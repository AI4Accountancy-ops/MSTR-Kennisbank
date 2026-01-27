import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from request_models.organization import (
    CreateOrganizationRequest,
    UpdateOrganizationRequest,
    OrganizationIdRequest,
    ListMyOrganizationsRequest,
    AddMemberRequest,
    UpdateMemberRoleRequest,
    RemoveMemberRequest,
    GetSubscriptionRequest,
    RefreshSubscriptionRequest,
    RefreshAllSubscriptionsRequest,
    UsageRequest,
)
from services.organization_service import OrganizationService
from logger.logger import Logger
from definitions.credentials import Credentials


logger = Logger.get_logger(__name__)
router = APIRouter(prefix="/organizations", tags=["organizations"])
service = OrganizationService()


@router.post("")
def create_organization(req: CreateOrganizationRequest) -> Dict[str, Any]:
    org_id = service.create_organization(req.owner_user_id, req.name, req.description)
    if not org_id:
        raise HTTPException(status_code=500, detail="Failed to create organization")
    return {"status": "success", "organization_id": org_id}


@router.get("/{organization_id}")
def get_organization(organization_id: str) -> Dict[str, Any]:
    org = service.get_organization(organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"status": "success", "organization": org}


@router.post("/mine")
def list_my_organizations(req: ListMyOrganizationsRequest) -> Dict[str, Any]:
    orgs = service.list_organizations_for_user(req.user_id)
    return {"status": "success", "organizations": orgs}


@router.post("/members")
def add_member(req: AddMemberRequest) -> Dict[str, Any]:
    if not service.is_user_admin(req.organization_id, req.acting_user_id):
        raise HTTPException(status_code=403, detail="Admin role required")
    ok = service.add_member(req.organization_id, req.user_id, req.role)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to add member")
    return {"status": "success"}


@router.patch("/members/role")
def update_member_role(req: UpdateMemberRoleRequest) -> Dict[str, Any]:
    if not service.is_user_admin(req.organization_id, req.acting_user_id):
        raise HTTPException(status_code=403, detail="Admin role required")
    ok = service.update_member_role(req.organization_id, req.user_id, req.role)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to update member role")
    return {"status": "success"}


@router.delete("/members")
def remove_member(req: RemoveMemberRequest) -> Dict[str, Any]:
    if not service.is_user_admin(req.organization_id, req.acting_user_id):
        raise HTTPException(status_code=403, detail="Admin role required")
    ok = service.remove_member(req.organization_id, req.user_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to remove member")
    return {"status": "success"}


# Invitation endpoints removed: admins add members directly via members endpoints.


@router.post("/subscription")
def get_subscription(req: GetSubscriptionRequest) -> Dict[str, Any]:
    active = service.has_active_subscription(req.organization_id)
    return {"status": "success", "active": active}


@router.post("/subscription/refresh")
def refresh_subscription(req: RefreshSubscriptionRequest) -> Dict[str, Any]:
    if not service.is_user_admin(req.organization_id, req.acting_user_id):
        raise HTTPException(status_code=403, detail="Admin role required")
    ok = service.refresh_subscription_from_stripe(req.organization_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to refresh subscription from Stripe")
    return {"status": "success"}


@router.post("/subscription/refresh_all")
def refresh_all_subscriptions(req: RefreshAllSubscriptionsRequest) -> Dict[str, Any]:
    expected = Credentials.get_subscription_sync_token()
    if not expected or req.token != expected:
        raise HTTPException(status_code=403, detail="Invalid token")
    count = service.refresh_all_subscriptions_from_stripe()
    return {"status": "success", "refreshed": count}


@router.post("/usage")
def get_usage(req: UsageRequest) -> Dict[str, Any]:
    """Return usage summary for the organization (or for user's active org)."""
    summary = service.get_usage_summary(organization_id=req.organization_id, user_id=req.user_id)
    if "error" in summary:
        if summary["error"] == "organization_not_found":
            raise HTTPException(status_code=404, detail="Organization not found")
        elif summary["error"] == "subscription_not_found":
            raise HTTPException(status_code=404, detail="Subscription not found")
        else:
            raise HTTPException(status_code=500, detail="Failed to retrieve usage summary")
    return {"status": "success", "usage": summary}


