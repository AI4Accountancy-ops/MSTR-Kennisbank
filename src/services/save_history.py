from typing import Dict, List, Optional
import uuid
from datetime import datetime
import json

from services.repositories.chat_history_repo import ChatHistoryRepository
from logger.logger import Logger
from request_models.feedback import ChatMessage

logger = Logger.get_logger(__name__)


class SaveHistory:
    def __init__(self):
        self.repo = ChatHistoryRepository()
    
    def save_chat_history(
        self, 
        user_id: str, 
        chat_title: str, 
        chat_history: List[ChatMessage], 
        chat_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Save or update a chat history in Cosmos DB.
        """
        try:
            # Log the incoming data structure
            logger.info(f"Saving chat history for user: {user_id}, title: {chat_title}, chat_id: {chat_id}")
            logger.info(f"Chat history contains {len(chat_history)} messages")
            
            # Check for messages with chunks
            chunk_messages = 0
            for msg in chat_history:
                if hasattr(msg, 'chunks') and msg.chunks:
                    chunk_messages += 1
                    logger.info(f"Message with role {msg.role} has {len(msg.chunks)} chunks")
                    # Log sample chunk structure for debugging
                    if len(msg.chunks) > 0:
                        sample_chunk = msg.chunks[0]
                        logger.info(f"Sample chunk keys: {list(sample_chunk.__dict__.keys()) if hasattr(sample_chunk, '__dict__') else type(sample_chunk)}")
            
            logger.info(f"Found {chunk_messages} messages with chunks")
            
            # If chat_id was passed in, see if that document already exists
            existing_doc = None
            if chat_id:
                existing_doc = self.get_chat_by_id(chat_id, user_id)

            # Filter out initial messages
            filtered_history = [msg for msg in chat_history if not getattr(msg, 'is_initial', False)]
            logger.info(f"Processing {len(filtered_history)} messages for chat history after filtering")
            
            # Create message pairs - this assigns IDs in the backend
            chat_pairs = self.pair_user_assistant_messages(filtered_history)
            
            # If the document doesn't exist (or no chat_id was given), create a new chat
            if not existing_doc:
                # Create new chat document
                new_chat_id = chat_id or str(uuid.uuid4())
                
                new_doc = {
                    "id": new_chat_id,
                    "partitionKey": user_id,
                    "userId": user_id,
                    "title": chat_title or "Nieuwe Chat",
                    "createdAt": datetime.now().isoformat(),
                    "updatedAt": datetime.now().isoformat(),
                    "messages": chat_pairs
                }
                
                logger.info(f"Creating new chat document with {len(chat_pairs)} message pairs")
                
                # Save to database
                upserted_id = self.repo.upsert_chat(
                    chat_id=new_chat_id,
                    user_id=user_id,
                    title=new_doc["title"],
                    messages=new_doc["messages"],
                    created_at=new_doc["createdAt"],
                )
                if upserted_id:
                    logger.info(f"Successfully saved new chat with ID: {upserted_id}")
                    return upserted_id
                logger.error("Failed to save new chat document")
                return None
                
            else:
                # The document exists, so we'll update it
                logger.info(f"Updating existing chat document with ID: {chat_id}")
                
                # REPLACE the messages array
                existing_doc["messages"] = chat_pairs
                
                # Update timestamps and title
                existing_doc["updatedAt"] = datetime.now().isoformat()
                
                # Only update the title if:
                # 1. A new title is provided AND
                # 2. Either the existing title is a default value OR the new title is significantly different
                if chat_title and chat_title.strip():
                    existing_title = existing_doc.get("title", "")
                    default_titles = ["Nieuwe Chat", "New Chat", ""]
                    
                    # Only update if existing title is default or new title is significantly different
                    if (existing_title in default_titles or 
                        existing_title != chat_title.strip()):
                        existing_doc["title"] = chat_title.strip()
                        logger.info(f"Updated chat title from '{existing_title}' to '{chat_title.strip()}'")
                    else:
                        logger.info(f"Preserving existing title '{existing_title}' (no significant change)")

                # Save to database
                upserted_id = self.repo.upsert_chat(
                    chat_id=existing_doc["id"],
                    user_id=user_id,
                    title=existing_doc["title"],
                    messages=existing_doc["messages"],
                    created_at=existing_doc.get("createdAt"),
                )
                if upserted_id:
                    logger.info(f"Successfully updated chat with ID: {upserted_id}")
                    return upserted_id
                logger.error(f"Failed to update chat document with ID: {chat_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving/updating chat history: {e}", exc_info=True)
            return None
    
    def get_user_chat_history(self, user_id: str) -> List[Dict]:
        """Get all chat history for a specific user."""
        try:
            return self.repo.get_user_chat_history(user_id)
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}", exc_info=True)
            return []
    
    def get_chat_by_id(self, chat_id: str, user_id: str) -> Optional[Dict]:
        """Get a specific chat by its ID and user ID."""
        try:
            # Using query instead of direct get_item to ensure user can only access their own chats
            return self.repo.get_chat_by_id(chat_id, user_id)
        except Exception as e:
            logger.error(f"Error retrieving chat: {e}", exc_info=True)
            return None
    
    def delete_chat(self, chat_id: str, user_id: str) -> bool:
        """Delete a specific chat by its ID and user ID."""
        try:
            # Verify this chat belongs to the user
            chat = self.get_chat_by_id(chat_id, user_id)
            if not chat:
                return False
                
            deleted = self.repo.delete_chat(chat_id, user_id)
            if not deleted:
                logger.error(f"Failed to delete chat document with ID: {chat_id}")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting chat: {e}", exc_info=True)
            return False
    
    def pair_user_assistant_messages(self, messages: List[ChatMessage]) -> List[Dict]:
        """
        Pair user and assistant messages into coherent pairs.
        Each pair gets a unique ID.
        """
        # Log the incoming messages
        logger.info(f"Pairing {len(messages)} messages")
        
        # Process messages sequentially to ensure proper pairs
        pairs = []
        i = 0
        
        while i < len(messages):
            # Look for a user message
            if i < len(messages) and messages[i].role == "user":
                # Create a new pair with a unique ID
                pair_id = str(uuid.uuid4())
                
                user_msg = messages[i].message
                assistant_msg = None
                chunks = []
                
                # Look for the corresponding assistant message
                if i + 1 < len(messages) and messages[i + 1].role == "assistant":
                    assistant_msg = messages[i + 1].message
                    
                    # Process chunks if they exist
                    # Try multiple ways to access chunks depending on if it's a Pydantic model or dict
                    try:
                        assistant_message = messages[i + 1]
                        
                        # Check if chunks exist using different access methods
                        if hasattr(assistant_message, 'chunks'):
                            chunks_data = assistant_message.chunks
                        elif isinstance(assistant_message, dict) and 'chunks' in assistant_message:
                            chunks_data = assistant_message['chunks']
                        else:
                            chunks_data = []
                            
                        # Only process non-empty chunks
                        if chunks_data:
                            logger.info(f"Found {len(chunks_data)} chunks in assistant message")
                            chunks = self._serialize_chunks(chunks_data)
                    except Exception as e:
                        logger.error(f"Error processing chunks: {e}")
                        chunks = []
                    
                    # Move past both messages
                    i += 2
                else:
                    # No matching assistant message, just move to next
                    i += 1
                
                # Create a complete pair with both messages
                pair = {
                    "id": pair_id,
                    "user": user_msg,
                    "assistant": assistant_msg,
                    "chunks": chunks
                }
                pairs.append(pair)
            else:
                # Skip any assistant messages without a preceding user message
                i += 1
        
        # Log what we created
        logger.info(f"Created {len(pairs)} message pairs")
        
        return pairs

    def _serialize_chunks(self, chunks):
        """Helper method to serialize chunks to a JSON-compatible format"""
        serialized_chunks = []
        
        if not chunks:
            return serialized_chunks
        
        for chunk in chunks:
            try:
                # First try to use Pydantic's .model_dump() or .dict() method if available
                if hasattr(chunk, 'model_dump'):
                    chunk_dict = chunk.model_dump()
                elif hasattr(chunk, 'dict'):
                    chunk_dict = chunk.dict()
                # Handle dictionary objects
                elif isinstance(chunk, dict):
                    # Create a shallow copy to avoid modifying the original
                    chunk_dict = chunk.copy()
                    
                    # Make sure certain fields are properly serialized
                    if 'year' in chunk_dict and isinstance(chunk_dict['year'], list):
                        # Keep year as a list, just make sure all elements are integers
                        chunk_dict['year'] = [int(y) for y in chunk_dict['year'] if str(y).isdigit()]
                    
                    # Ensure fiscal_topic is properly serialized if present
                    if 'fiscal_topic' in chunk_dict and chunk_dict['fiscal_topic'] is not None:
                        if not isinstance(chunk_dict['fiscal_topic'], list):
                            chunk_dict['fiscal_topic'] = [str(chunk_dict['fiscal_topic'])]
                else:
                    # For objects with __dict__, extract attributes
                    if hasattr(chunk, '__dict__'):
                        chunk_dict = {
                            k: v for k, v in chunk.__dict__.items() 
                            if not k.startswith('_') and v is not None
                        }
                    else:
                        # Last resort: create a generic dict
                        chunk_dict = {
                            "chunk_type": getattr(chunk, "chunk_type", "unknown"),
                            "chunk_value": getattr(chunk, "chunk_value", str(chunk))
                        }
                
                # Make sure all values are JSON serializable
                for key, value in list(chunk_dict.items()):
                    # Handle non-serializable types
                    if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        chunk_dict[key] = str(value)
                    # Ensure lists contain only simple types
                    elif isinstance(value, list):
                        chunk_dict[key] = [
                            item if isinstance(item, (str, int, float, bool, type(None)))
                            else str(item) for item in value
                        ]
                
                serialized_chunks.append(chunk_dict)
                
            except Exception as e:
                logger.error(f"Error serializing chunk: {e}")
                # Include a basic representation as fallback
                serialized_chunks.append({
                    "error": "Failed to serialize chunk",
                    "chunk_value": str(chunk)
                })
            
        return serialized_chunks

    def _fix_serialization(self, doc):
        """Helper to fix JSON serialization issues in a document"""
        if "messages" in doc:
            for pair in doc["messages"]:
                # Fix chunks array
                if "chunks" in pair:
                    if not isinstance(pair["chunks"], list):
                        pair["chunks"] = []
                    else:
                        # Ensure each chunk is serializable
                        serializable_chunks = []
                        for chunk in pair["chunks"]:
                            if isinstance(chunk, dict):
                                # Keep only serializable fields
                                safe_chunk = {}
                                for k, v in chunk.items():
                                    if isinstance(v, (str, int, float, bool, type(None))):
                                        safe_chunk[k] = v
                                    else:
                                        safe_chunk[k] = str(v)
                                serializable_chunks.append(safe_chunk)
                            else:
                                # Convert to string
                                serializable_chunks.append({
                                    "chunk_type": "text", 
                                    "chunk_value": str(chunk)
                                })
                        pair["chunks"] = serializable_chunks

    def search_chat_history(self, user_id: str, query: str) -> list:
        """
        Search through a user's chat history for messages matching the query.
        Only searches in:
        - Chat title
        - User messages
        - Assistant messages
        Returns a list of chat history items that contain matching messages.
        """
        try:
            # Get all chat history for the user
            all_chats = self.get_user_chat_history(user_id)
            
            # Filter chats that contain messages matching the query
            matching_chats = []
            query = query.lower()
            
            for chat in all_chats:
                # 1. Check if query matches chat title
                if query in chat.get("title", "").lower():
                    matching_chats.append(chat)
                    continue
                
                # 2. Check if query matches any message content
                for message in chat.get("messages", []):
                    # Only check user and assistant message fields
                    if (query in message.get("user", "").lower() or 
                        query in message.get("assistant", "").lower()):
                        matching_chats.append(chat)
                        break
            
            return matching_chats
            
        except Exception as e:
            logger.error(f"Error searching chat history: {str(e)}")
            return []
    
    def update_chat_title(self, chat_id: str, new_title: str, user_id: str) -> bool:
        """
        Update the title of a specific chat by ID for a user.
        """
        try:
            # Get the chat document
            chat = self.get_chat_by_id(chat_id, user_id)
            if not chat:
                return False
            
            # Update the title
            chat["title"] = new_title

            # Save the updated chat
            return self.repo.update_chat_title(chat_id, new_title, user_id)
        except Exception as e:
            logger.error(f"Error updating chat title: {str(e)}")
            return False
