from typing import BinaryIO, Optional, Generator
import json

import definitions.names as n
from config.settings import get_settings
from definitions.enums import ReasoningEffort
from services.llm_factory import LLMFactory
from services.query_handler import QueryHandler
from utils.format_helper import FormatHelper
from logger.logger import Logger

logger = Logger.get_logger(__name__)


class ChatBot:
    def __init__(self):
        self.settings = get_settings()
        self.llm = LLMFactory(n.AZURE_OPENAI)
        self.query_handler = QueryHandler()
        self.format_helper = FormatHelper()

    def get_chatbot_response(
            self,
            user_message: str,
            tone_of_voice: str,
            reasoning_effort: ReasoningEffort = ReasoningEffort.MEDIUM.value,
            uploaded_file: Optional[BinaryIO] = None,
            chat_history: Optional[list] = None,
            user_id: Optional[str] = None,
            web_search: bool = False,
    ) -> Generator[str, None, None]:
        try:
            # 1. Validate user subscription if required
            if user_id:
                from services.auth_service import UserService
                user_service = UserService()
                
                # Fast DB-only access check (no Stripe calls)
                if not user_service.has_access_fast(user_id):
                    not_subscribed_message = """
Om je vraag te kunnen beantwoorden, is een actief account nodig.

---

Je kunt je aanmelden via onze website: [ai4accountancy.nl/accountancy-software](https://ai4accountancy.nl/accountancy-software). Na aanmelding krijg je direct toegang tot de Belasting AI Agents voor BTW, VPB en IB.

---

Heb je vragen over de aanmelding of het gebruik? Stuur dan gerust een mail naar: [pascale@ai4accountancy.nl](mailto:pascale@ai4accountancy.nl)
"""
                    logger.warning(f"User {user_id} is not subscribed or doesn't exist")
                    yield not_subscribed_message
                    return
                # Quota check: consume 1 question if available for the user's active org
                try:
                    from services.organization_service import OrganizationService
                    # Reuse a module-level singleton to avoid exhausting DB connections
                    global _ORG_SVC_SINGLETON
                    try:
                        _ORG_SVC_SINGLETON
                    except NameError:
                        _ORG_SVC_SINGLETON = OrganizationService()
                    org_service = _ORG_SVC_SINGLETON
                    active_org_id = org_service.get_first_active_org_for_user(user_id)
                    if active_org_id:
                        result = org_service.consume_quota_if_available(active_org_id)
                        # Never block post-trial; only block during trial when allowed=False
                        if not result.get("allowed", True):
                            quota_message = f"\nJe dagquotum is bereikt (trial). Probeer het morgen opnieuw."
                            yield quota_message
                            return
                        # Emit Stripe meter event strictly for usage beyond monthly plan quota
                        if result.get("over_quota"):
                            org_service.report_overage_usage(active_org_id, quantity=1)
                except Exception:
                    pass
            else:
                logger.warning("No user_id provided, proceeding without subscription check")
            
            # Handle file-based queries
            if uploaded_file:
                for response in self.query_handler.answer_query_with_file(user_message, uploaded_file):
                    sanitized_response = self.format_helper.sanitize_markdown(response)
                    yield sanitized_response
                return

            # Signal: start vraag analyseren spinner
            yield n.ANALYSIS_STARTED_FLAG

            # Process the user's question to get fiscal topics/years/vector_query
            question_metadata = self.query_handler.process_question(user_message, chat_history)

            # Extract fiscal topics as string values from FiscalTopic enum objects
            fiscal_topic = [topic.value for topic in question_metadata.fiscal_topic]
            year = question_metadata.year
            vector_query = question_metadata.vector_query
            cleaned_vector_query = self.query_handler.clean_vector_query(vector_query)
            
            logger.info(f"Processed question metadata - fiscal topics: {fiscal_topic}, years: {year}")

            # Signal: finish vraag analyseren spinner
            yield n.ANALYSIS_FINISHED_FLAG

            # Always start retrieval spinner
            yield n.RETRIEVAL_STARTED_FLAG

            # Use the generator from answer_tax_query
            tax_response_gen = self.query_handler.answer_tax_query(
                user_message,
                cleaned_vector_query,
                tone_of_voice,
                year,
                fiscal_topic,
                chat_history,
            )
            
            # Stream items directly to the user interface
            for item in tax_response_gen:
                if isinstance(item, dict):
                    if item.get("flag") == "docs_retrieved":
                        yield n.DOCS_RETRIEVED_FLAG
                    elif item.get("flag") == "error":
                        yield item.get("message", "Er is een fout opgetreden.")
                        return
                else:
                    sanitized_chunk = self.format_helper.sanitize_markdown(item)
                    if sanitized_chunk:
                        yield sanitized_chunk

        except Exception as e:
            logger.error(f"Error in get_chatbot_response: {e}")
            yield "Er is een fout opgetreden bij het verwerken van je vraag. Probeer het later opnieuw."
