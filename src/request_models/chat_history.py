from typing import List, Optional
from pydantic import BaseModel

from request_models.feedback import ChatMessage


class SaveChatHistoryRequest(BaseModel):
    user_id: str
    chat_title: Optional[str] = None
    chat_history: List[ChatMessage]
    chat_id: Optional[str] = None


class GetChatHistoryRequest(BaseModel):
    user_id: str


class GetChatByIdRequest(BaseModel):
    chat_id: str
    user_id: str


class UpdateChatTitleRequest(BaseModel):
    chat_id: str
    user_id: str
    new_title: str
