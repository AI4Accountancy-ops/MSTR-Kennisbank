from typing import Dict, List
import uuid
from datetime import datetime

from services.repositories.feedback_repo import FeedbackRepository
from logger.logger import Logger
from request_models.feedback import ChatMessage

logger = Logger.get_logger(__name__)

class SaveFeedback:
    def __init__(self):
        self.repo = FeedbackRepository()

    def save_feedback(self, feedback_item: Dict) -> bool:
        """Save feedback to Cosmos DB."""
        try:
            return self.repo.upsert_feedback(feedback_item)
        except Exception as e:
            logger.error(f"Error saving feedback: {e}", exc_info=True)
            return False

    def pair_user_assistant_messages(self, messages: List[ChatMessage]) -> List[Dict]:
        """
        Convert a flat list of ChatMessage objects into a list of Q&A pairs.
        Each pair includes 'user', 'assistant', and 'chunks'.
        """
        pairs = []
        current_user_msg = None  # will store a ChatMessage or None

        for msg in messages:
            if msg.role == "user":
                if current_user_msg is not None:
                    # A pending user message with no assistant answer
                    pairs.append({
                        "user": current_user_msg.message,
                        "assistant": "",
                        "chunks": []
                    })
                current_user_msg = msg

            elif msg.role == "assistant":
                # Process chunks safely
                chunk_dicts = []
                
                if msg.chunks:
                    for chunk in msg.chunks:
                        try:
                            if hasattr(chunk, "model_dump"):
                                chunk_dicts.append(chunk.model_dump())
                            elif hasattr(chunk, "dict"):
                                chunk_dicts.append(chunk.dict())
                            elif isinstance(chunk, dict):
                                chunk_dicts.append(chunk)
                            else:
                                # Skip any chunks that don't fit expected formats
                                logger.warning(f"Skipping chunk with unexpected type in pair_messages: {type(chunk)}")
                        except Exception as e:
                            logger.warning(f"Error processing chunk in pair_messages: {e}")
                            continue
                
                if current_user_msg is not None:
                    pairs.append({
                        "user": current_user_msg.message,
                        "assistant": msg.message,
                        "chunks": chunk_dicts
                    })
                    current_user_msg = None
                else:
                    # Assistant message with no preceding user
                    pairs.append({
                        "user": "",
                        "assistant": msg.message,
                        "chunks": chunk_dicts
                    })

        # If there is an unmatched user message left
        if current_user_msg is not None:
            pairs.append({
                "user": current_user_msg.message,
                "assistant": "",
                "chunks": []
            })

        return pairs

    def message_feedback(self, feedback_data: Dict) -> bool:
        """
        Save like/dislike feedback to Cosmos DB.
        The feedback_data should contain:
        - user_id: str
        - chat_message: Dict with user, assistant, and chunks
        - feedback_type: str ("good" or "bad")
        """
        try:
            feedback_id = str(uuid.uuid4())
            
            # Process chunks - convert ChunkModel instances to dictionaries
            chat_message = feedback_data["chat_message"]
            
            if "chunks" in chat_message and chat_message["chunks"]:
                processed_chunks = []
                
                for chunk in chat_message["chunks"]:
                    # Skip empty or invalid chunks
                    if not chunk:
                        logger.debug("Skipping empty chunk in message_feedback")
                        continue
                    
                    try:
                        # If chunk is a Pydantic model, convert to dict
                        if hasattr(chunk, "model_dump"):
                            processed_chunks.append(chunk.model_dump())
                        elif hasattr(chunk, "dict"):
                            processed_chunks.append(chunk.dict())
                        elif isinstance(chunk, dict):
                            # Make sure the dict has required fields
                            if "content" not in chunk and "id" not in chunk and "source_url" not in chunk:
                                logger.debug(f"Skipping chunk with no required fields in message_feedback: {chunk}")
                                continue
                            processed_chunks.append(chunk)
                        else:
                            # Skip any chunks that don't fit our expected formats
                            logger.debug(f"Skipping chunk with unexpected type in message_feedback: {type(chunk)}")
                            continue
                    except Exception as e:
                        logger.warning(f"Error processing chunk in message_feedback: {e}")
                        continue
                
                chat_message["chunks"] = processed_chunks
            
            feedback_item = {
                "id": feedback_id,
                "partitionKey": feedback_id,
                "metadata": {
                    "type": "message_feedback",
                    "feedback_type": feedback_data["feedback_type"],
                    "timestamp": datetime.now().isoformat(),
                },
                "user_id": feedback_data["user_id"],
                "chat_message": chat_message,
            }
            return self.repo.upsert_message_feedback(feedback_item)
        except Exception as e:
            logger.error(f"Error saving like/dislike feedback: {e}", exc_info=True)
            return False
