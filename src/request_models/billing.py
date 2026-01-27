from typing import Optional
from pydantic import BaseModel, AnyHttpUrl


class CreateCheckoutSessionRequest(BaseModel):
    user_id: str
    organization_id: str
    price_id: str
    success_url: AnyHttpUrl
    cancel_url: AnyHttpUrl
    trial_days: Optional[int] = None
    overage_price_id: Optional[str] = None


class CompleteCheckoutRequest(BaseModel):
    user_id: str
    session_id: str


class CustomerPortalRequest(BaseModel):
    acting_user_id: str
    organization_id: str
    return_url: AnyHttpUrl

