# request_models/feedback.py
from pydantic import BaseModel
from typing import List, Optional

#
# 1) Models describing the *incoming* request
#

class ChunkModel(BaseModel):
    id: Optional[str] = None
    year: Optional[int] = None
    source: Optional[List[str]] = None
    data_category: Optional[List[str]] = None
    fiscal_topic: Optional[List[str]] = None
    source_url: Optional[str] = None
    target_group: Optional[List[str]] = None
    information_type: Optional[List[str]] = None
    content: Optional[str] = None
    keyword_score: Optional[float] = None
    semantic_score: Optional[float] = None
    rerank_score: Optional[float] = None
    final_score: Optional[float] = None
    title: Optional[str] = None

class ChatMessage(BaseModel):
    role: str                  # "user" or "assistant"
    message: str               # The text content of the message
    is_initial: bool = False   # Filter out if you don't want these
    chunks: Optional[List[ChunkModel]] = None

class FeedbackRequest(BaseModel):
    """
    Represents the JSON body the frontend sends for feedback, e.g.:

    {
      "category": "Question",
      "feedback_text": "Details about my feedback",
      "chat_history": [...list of ChatMessage...]
    }
    """
    category: str
    feedback_text: str
    chat_history: List[ChatMessage]

#
# 2) (Optional) Models describing the *Cosmos DB document structure*
#

class MetadataModel(BaseModel):
    category: str
    timestamp: str

class ChatInteraction(BaseModel):
    user: str
    assistant: str
    chunks: Optional[List[ChunkModel]] = None

class FeedbackItem(BaseModel):
    """
    Represents the final document you might store in Cosmos.
    """
    id: str
    partitionKey: str
    metadata: MetadataModel
    feedback_text: str
    chat_interactions: List[ChatInteraction]

class MessageFeedbackRequest(BaseModel):
    """
    Represents the JSON body for message_feedback, e.g.:
    {
      "user_id": "The user's UUID from Azure MSAL",
      "chat_message": {
        "role": "assistant",
        "message": "VAT is...",
        "chunks": [...]
      },
      "feedback_type": "good"
    }
    """
    user_id: str
    chat_message: ChatMessage
    feedback_type: str