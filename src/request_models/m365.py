from typing import Optional, List
from pydantic import BaseModel, Field


class CreateSubscriptionRequest(BaseModel):
    """Request model for creating an M365 subscription"""
    user_id: str = Field(..., description="User ID to create subscription for")
    resource: str = Field(
        default="me/mailFolders('Inbox')/messages",
        description="Resource to monitor"
    )


class DeleteSubscriptionRequest(BaseModel):
    """Request model for deleting an M365 subscription"""
    subscription_id: str = Field(..., description="Subscription ID to delete")


class RefreshTokenRequest(BaseModel):
    """Request model for refreshing access token"""
    user_id: str = Field(..., description="User ID to refresh token for")


class GetEmailsRequest(BaseModel):
    """Request model for getting emails"""
    user_id: str = Field(..., description="User ID")
    folder: str = Field(default="inbox", description="Folder name")
    limit: int = Field(default=10, description="Number of emails to retrieve")


class AuthenticateRequest(BaseModel):
    """Request model for initiating OAuth2 authentication"""
    redirect_uri: Optional[str] = Field(
        default=None,
        description="Optional redirect URI to use for this auth flow; overrides configured default"
    )
