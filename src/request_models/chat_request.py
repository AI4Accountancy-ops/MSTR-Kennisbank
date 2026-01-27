from typing import List, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    user_message: str
    tone_of_voice: str
    chat_history: List
    user_id: str
    web_search: Optional[bool] = False