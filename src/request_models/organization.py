from pydantic import BaseModel, EmailStr
from typing import Optional, List


class CreateOrganizationRequest(BaseModel):
    owner_user_id: str
    name: str
    description: Optional[str] = None


class UpdateOrganizationRequest(BaseModel):
    organization_id: str
    name: Optional[str] = None


class OrganizationIdRequest(BaseModel):
    organization_id: str


class UsageRequest(BaseModel):
    organization_id: Optional[str] = None
    user_id: Optional[str] = None


class ListMyOrganizationsRequest(BaseModel):
    user_id: str


class AddMemberRequest(BaseModel):
    organization_id: str
    user_id: str
    role: str  # 'admin' | 'user'
    acting_user_id: str


class UpdateMemberRoleRequest(BaseModel):
    organization_id: str
    user_id: str
    role: str  # 'admin' | 'user'
    acting_user_id: str


class RemoveMemberRequest(BaseModel):
    organization_id: str
    user_id: str
    acting_user_id: str


# Invitation flow removed; admins add users directly via members endpoints.


class GetSubscriptionRequest(BaseModel):
    organization_id: str


class RefreshSubscriptionRequest(BaseModel):
    organization_id: str
    acting_user_id: str


class RefreshAllSubscriptionsRequest(BaseModel):
    token: str


class OrganizationMember(BaseModel):
    user_id: str
    role: str


class Organization(BaseModel):
    id: str
    name: str
    owner_user_id: str
    description: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_price_id: Optional[str] = None
    stripe_product_id: Optional[str] = None
    subscription_status: Optional[str] = None
    current_period_end: Optional[str] = None
    members: Optional[List[OrganizationMember]] = None

