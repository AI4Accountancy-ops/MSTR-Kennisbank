from typing import Optional
from pydantic import BaseModel

class LoginRequest(BaseModel):
    user_id: str
    email: str
    name: str
    auth_provider: str
    is_subscribed: bool
    selected_price_id: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None