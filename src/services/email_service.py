# FOR LOCAL TESTING ONLY
if __name__ == "__main__":
    # Add src directory to path
    import sys
    from pathlib import Path

    src_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(src_dir))
    print(sys.path)

import logging

import definitions.names as n
from services.llm_factory import LLMFactory
from services.query_handler import QueryHandler
from utils.format_helper import FormatHelper

from prompts.system_prompt_templates import email_classifier_system_prompt, email_reply_system_prompt
from prompts.user_prompt_templates import email_classifier_user_prompt

from response_models.email_response_models import EmailClassifierResponse, EmailReplyRequest, EmailReplyResponse
from response_models.chat_response_models import QuestionFiscalTopicYear

logger = logging.getLogger(__name__)

class EmailPromptFormatter:
    @staticmethod
    def format_sender_info(email_request: EmailReplyRequest) -> str:
        """Format sender information"""
        if email_request.sender_name:
            sender_info = email_request.sender_name
            if email_request.sender_email:
                sender_info += f" ({email_request.sender_email})"
        elif email_request.sender_email:
            sender_info = email_request.sender_email
        else:
            sender_info = "Unknown sender"
        return sender_info
    
    @staticmethod
    def format_recipient_info(email_request: EmailReplyRequest) -> str:
        """Format recipient information block"""
        if email_request.recipient_name:
            return f"""
<antwoorder>
Jouw naam (voor ondertekening): {email_request.recipient_name}
</antwoorder>
"""
        return ""

class EmailClassifier:
    def __init__(self):
        self.llm = LLMFactory(n.AZURE_OPENAI)
        self.prompt_formatter = EmailPromptFormatter()
        logger.info("EmailClassifier initialized")
    
    def classify_email(self, email_request: EmailReplyRequest) -> EmailClassifierResponse:
        """Classify an email to decide if a response is needed."""
        try:
            user_message = self._format_email_prompt(email_request)
            system_prompt = email_classifier_system_prompt
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            response = self.llm.normal_completion(
                response_model=EmailClassifierResponse,
                messages=messages
            )
            return response
        except Exception as e:
            logger.error(f"Error classifying email: {e}")
            return EmailClassifierResponse(
                should_respond=False,
                reasoning="Error classifying email",
                fiscal_topic=[],
                confidence="laag"
            )
    
    def _format_email_prompt(self, email_request: EmailReplyRequest) -> str:
        """Format email information as user prompt"""
        sender_info = self.prompt_formatter.format_sender_info(email_request)
        recipient_info = self.prompt_formatter.format_recipient_info(email_request)
        return email_classifier_user_prompt.format(
            sender_info=sender_info,
            subject=email_request.subject,
            body=email_request.body,
            recipient_info=recipient_info
        ).strip()

class EmailReplyGenerator:
    """Service for generating personalized email replies using LLM"""
    
    def __init__(self):
        self.llm = LLMFactory(n.AZURE_OPENAI)
        self._query_handler = None
        self._format_helper = None
        self.prompt_formatter = EmailPromptFormatter()
        logger.info("EmailReplyGenerator initialized")

    @property
    def query_handler(self):
        if self._query_handler is None:
            self._query_handler = QueryHandler()
        return self._query_handler
    
    @property
    def format_helper(self):
        if self._format_helper is None:
            self._format_helper = FormatHelper()
        return self._format_helper
    
    def generate_reply(self, email_request: EmailReplyRequest, metadata: QuestionFiscalTopicYear) -> EmailReplyResponse:
        """
        Generate a personalized reply to an email
        
        Args:
            email_request: EmailReplyRequest containing email details
            metadata: QuestionFiscalTopicYear containing metadata
        Returns:
            EmailReplyResponse: Generated reply with metadata
        """
        try:
            # Prepare the user message with email context
            user_message = self._format_email_prompt(email_request)

            tax_response_gen = self.query_handler.answer_tax_query(
                user_message,
                metadata.vector_query,
                "professioneel en vriendelijk",
                metadata.year,
                [topic.value for topic in metadata.fiscal_topic],
                None,
            )

            # collect the streamed items
            streamed_items = []
            for item in tax_response_gen:
                if isinstance(item, dict):
                    if item.get("flag") == "docs_retrieved":
                        streamed_items.append(n.DOCS_RETRIEVED_FLAG)
                    elif item.get("flag") == "error":
                        streamed_items.append(item.get("message", "Er is een fout opgetreden."))
                        return EmailReplyResponse(
                            answer="Er is een fout opgetreden bij het genereren van het antwoord.",
                            tone="neutral",
                            reasoning="Error generating email reply"
                        )
                else:
                    sanitized_chunk = self.format_helper.sanitize_markdown(item)
                    if sanitized_chunk:
                        streamed_items.append(sanitized_chunk)
            
            tax_response_answer = "".join(streamed_items)

            # Convert the tax response answer to an email reply answer
            system_prompt = email_reply_system_prompt
            
            # Create messages for LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"<user_message>{user_message}</user_message>"},
                {"role": "user", "content": f"<tax_response_answer>{tax_response_answer}</tax_response_answer>"}
            ]
            
            # Generate reply using LLM
            response = self.llm.normal_completion(
                response_model=EmailReplyResponse,
                messages=messages
            )
            
            logger.info(f"Generated reply for email: {email_request.subject[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"Error generating email reply: {e}")
            # Return a fallback response
            return EmailReplyResponse(
                answer="Bedankt voor je e-mail. Ik heb je bericht ontvangen en zal binnenkort reageren.\n\nMet vriendelijke groet",
                tone="neutral",
                reasoning="Fallback reply due to generation error"
            )
    
    def _format_email_prompt(self, email_request: EmailReplyRequest) -> str:
        """Format email for reply generation"""
        sender_info = self.prompt_formatter.format_sender_info(email_request)
        recipient_info = self.prompt_formatter.format_recipient_info(email_request)
        
        return f"""
<tone_of_voice>
Professioneel en vriendelijk
</tone_of_voice>

<email_context>
<afzender>{sender_info}</afzender>
<onderwerp>{email_request.subject}</onderwerp>
<inhoud>
{email_request.body}
</inhoud>
</email_context>
{recipient_info}
<taak>
Genereer een gepersonaliseerd, professioneel antwoord op deze e-mail. 
Houd rekening met de context, toon en eventuele verzoeken in het oorspronkelijke bericht.
Zorg voor een duidelijke structuur en passende opmaak in markdown.
Gebruik de naam van de antwoorder voor de ondertekening (indien beschikbaar).
</taak>
""".strip()
        
# Example usage for testing
if __name__ == "__main__":
    generator = EmailReplyGenerator()
    
    # Test email
    '''test_request = EmailReplyRequest(
        subject="Vraag over BTW-aangifte",
        body="Hallo, ik heb een vraag over mijn BTW-aangifte voor het laatste kwartaal. Kunt u mij helpen?",
        sender_name="Jan Janssen",
        sender_email="jan@example.com"
    )
    
    reply = generator.generate_reply(test_request)'''

    # Print email reply generation
    '''print("Generated Reply:")
    print(reply.answer)
    print(f"\nTone: {reply.tone}")
    print(f"Reasoning: {reply.reasoning}")'''

    # Test email classification
    test_request_should_respond = EmailReplyRequest(
        subject="Gemengde btw & inkomstenbelasting – renovatie monumentale boerderij (woning/B&B/atelier)",
        body=f"""Beste team,

We renoveren een monumentale boerderij (1775) met een gemengd gebruik en ik wil dit correct verwerken voor btw en IB.

Gebruik & cijfers (fictief):
Woning (privé): 40%
B&B (belaste prestaties): 30%
Atelier (deels verkoop kunstwerken, belaste activiteiten): 30%
Renovatiekosten 2024-2025 (excl. btw): € 180.000
WOZ-waarde 2024: € 950.000

Vragen:
Hoe bepalen we in deze gemengde situatie het juiste btw-tarief en de aftrek van voorbelasting (toerekening per gebruiksdeel, eventueel pro-rata/werkelijk gebruik)?
Zijn er specifieke regels voor monumenten die hier een ander tarief of beperking geven?
Hoe verwerken we dit in de inkomstenbelasting: welk deel valt in Box 1 (onderneming/B&B/atelier) en welk deel in Box 3 (woning), incl. afschrijvings- en kostentoerekening?
Aandachtspunten bij mix van privé en zakelijk (bijtelling, correcties, btw-herzieningstermijnen, gebruikspercentages in de tijd)?
Als checklist ontvang ik graag een lijst documenten (facturen renovatie gesplitst, plattegronden m², omzetprognoses B&B/atelier, etc.).

Met vriendelijke groet,
Jan Janssen
MSTR""",
        sender_name="Jan Janssen",
        sender_email="jan@example.com"
    )
    classifier = EmailClassifier()
    classification = classifier.classify_email(test_request_should_respond)

    # Print classification
    print("Sample classification (should respond)")
    print(f"Should respond: {classification.should_respond}")
    print(f"Fiscal topic: {classification.fiscal_topic}")
    print(f"Confidence: {classification.confidence}")
    print(f"Reasoning: {classification.reasoning}")

    generate_reply = generator.generate_reply(test_request_should_respond, classification)

    # Print generate reply
    print("Generated Reply:")
    print(generate_reply.answer)
    print(f"\nTone: {generate_reply.tone}")
    print(f"Reasoning: {generate_reply.reasoning}")

    
    '''test_request_should_not_respond = EmailReplyRequest(
        subject="🤖 Ontdek je nieuwe AI-assistent — Werk slimmer, niet harder",
        body="""## Maak kennis met AI1: De AI die jouw productiviteit een boost geeft

Hallo,

Ben je het beu om eindeloze taken en vergaderingen te combineren? Laat **[Product Name]**, jouw nieuwe **AI-gestuurde assistent**, het drukke werk overnemen — zodat jij je kunt concentreren op wat écht telt.

Met AI1 kun je:  
✅ Repetitieve taken in seconden automatiseren  
✅ E-mails, rapporten en ideeën direct genereren  
✅ Inzichten in real time krijgen om prestaties te verbeteren  
✅ Naadloos samenwerken met je team  

Of je nu een zelfstandige ondernemer bent of deel uitmaakt van een groeiend team — [Product Name] past zich aan aan jouw manier van werken, niet andersom.

💡 **Probeer het 14 dagen gratis** en ervaar vandaag nog de toekomst van werken.

👉 [**Start je gratis proefperiode**](#)

Groeten,  
**Het team van AI1**  
[www.ai1.nl](#)

---

**P.S.** Vroege gebruikers krijgen **exclusieve toegang tot nieuwe AI-tools** die volgende maand worden gelanceerd — mis het niet!

**Afmelden** | **Voorkeuren beheren**""",
        sender_name="Jan Janssen",
        sender_email="jan@example.com"
    )
    classification = classifier.classify_email(test_request_should_not_respond)

    # Print classification
    print("\n--------------------------------\n")
    print("Sample classification (should not respond)")
    print(f"Should respond: {classification.should_respond}")
    print(f"Fiscal topic: {classification.fiscal_topic}")
    print(f"Confidence: {classification.confidence}")
    print(f"Reasoning: {classification.reasoning}")'''