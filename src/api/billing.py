from typing import Any, Dict

from fastapi import APIRouter, HTTPException
import stripe

from request_models.billing import (
    CreateCheckoutSessionRequest,
    CompleteCheckoutRequest,
    CustomerPortalRequest,
)
from definitions.credentials import Credentials
from logger.logger import Logger


logger = Logger.get_logger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/create_checkout_session")
def create_checkout_session(req: CreateCheckoutSessionRequest) -> Dict[str, Any]:
    try:
        stripe.api_key = Credentials.get_stripe_api_key()
        # Validate organization and permissions
        try:
            from services.organization_service import OrganizationService
            org_service = OrganizationService()
            # Ensure organization exists and user is admin of it
            org = org_service.get_organization(req.organization_id)
            if not org:
                raise HTTPException(status_code=400, detail="Ongeldige organisatie")
            if not org_service.is_user_admin(req.organization_id, req.user_id):
                raise HTTPException(status_code=403, detail="Gebruiker is geen admin van de organisatie")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=500, detail="Kan organisatie of rechten niet valideren")
        # Try to prefill the customer's email so Stripe sends receipts/invoices
        customer_email = None
        try:
            from services.auth_service import UserService
            user_service = UserService()
            user = user_service.get_user(req.user_id)
            if user and user.get("email"):
                customer_email = user.get("email")
        except Exception:
            customer_email = None
        # Preflight validate prices to fail fast with 400 if misconfigured
        try:
            _ = stripe.Price.retrieve(req.price_id)
            if req.overage_price_id:
                _ = stripe.Price.retrieve(req.overage_price_id)
        except Exception as e:
            logger.error(f"Invalid Stripe price id: {e}")
            raise HTTPException(status_code=400, detail="Invalid Stripe price_id or overage_price_id")

        subscription_data = {}
        if req.trial_days and req.trial_days > 0:
            subscription_data["trial_period_days"] = req.trial_days
        # Ensure metadata is also present on the resulting Subscription
        subscription_data["metadata"] = {
            "user_id": req.user_id,
            "organization_id": req.organization_id,
        }
        line_items = [{"price": req.price_id, "quantity": 1}]
        if req.overage_price_id:
            line_items.append({"price": req.overage_price_id, "quantity": 1})
        session_params = dict(
            mode="subscription",
            line_items=line_items,
            success_url=str(req.success_url) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=str(req.cancel_url),
            metadata={"user_id": req.user_id, "organization_id": req.organization_id},
            client_reference_id=req.organization_id,
            subscription_data=subscription_data or None,
        )
        if customer_email:
            session_params["customer_email"] = customer_email
        session = stripe.checkout.Session.create(**session_params)
        return {"status": "success", "url": session.url}
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/complete_checkout")
def complete_checkout(req: CompleteCheckoutRequest) -> Dict[str, Any]:
    try:
        stripe.api_key = Credentials.get_stripe_api_key()
        session = stripe.checkout.Session.retrieve(req.session_id, expand=["subscription", "customer"])
        if session.payment_status not in ("paid", "no_payment_required"):
            raise HTTPException(status_code=400, detail="Checkout not paid")

        subscription_id = None
        customer_id = None
        try:
            subscription_id = session.subscription.id if getattr(session, "subscription", None) else None
        except Exception:
            pass
        try:
            customer_id = session.customer.id if getattr(session, "customer", None) else session.customer
        except Exception:
            pass

        if not customer_id:
            raise HTTPException(status_code=500, detail="Missing customer_id from session")

        # Validate that the session's user_id matches the request
        session_user_id = session.metadata.get("user_id") if hasattr(session, "metadata") else None
        if not session_user_id or session_user_id != req.user_id:
            raise HTTPException(status_code=403, detail="Session user_id mismatch")

        # Provision organization using existing endpoint logic
        from services.organization_service import OrganizationService

        # Reuse a module-level singleton to avoid exhausting DB connections
        global _ORG_SVC_SINGLETON
        try:
            _ORG_SVC_SINGLETON
        except NameError:
            _ORG_SVC_SINGLETON = OrganizationService()
        org_service = _ORG_SVC_SINGLETON

        # Check if this session has already been processed (idempotency)
        # Look up by Stripe IDs in organization_subscriptions first
        with org_service.get_connection() as conn:
            with conn.cursor() as cur:
                if subscription_id or customer_id:
                    cur.execute(
                        """
                        SELECT organization_id 
                        FROM organization_subscriptions 
                        WHERE (stripe_subscription_id = %s AND %s IS NOT NULL)
                           OR (stripe_customer_id = %s AND %s IS NOT NULL)
                        LIMIT 1
                        """,
                        (subscription_id, subscription_id, customer_id, customer_id),
                    )
                    existing = cur.fetchone()
                    if existing:
                        existing_org_id = existing[0]
                        logger.info(f"Subscription already linked to org {existing_org_id} for session {req.session_id}")
                        return {
                            "status": "success",
                            "organization_id": existing_org_id,
                            "customer_id": customer_id,
                            "subscription_id": subscription_id,
                            "message": "Already processed"
                        }

        # Prefer organization_id from session metadata if present; do NOT create org here
        org_id = None
        try:
            org_id = session.metadata.get("organization_id") if hasattr(session, "metadata") else None
        except Exception:
            org_id = None
        if not org_id:
            # Fallback: try to find any existing organization for this user
            try:
                with org_service.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT id FROM organizations WHERE owner_user_id = %s ORDER BY created_at ASC LIMIT 1",
                            (req.user_id,),
                        )
                        row = cur.fetchone()
                        org_id = row[0] if row else None
            except Exception:
                org_id = None
        if not org_id:
            raise HTTPException(status_code=400, detail="Organisatie ontbreekt voor deze checkout sessie")

        with org_service.get_connection() as conn:
            with conn.cursor() as cur:
                # Ensure user is admin in users table (optional convenience)
                try:
                    cur.execute(
                        "UPDATE users SET role = 'admin' WHERE id = %s",
                        (req.user_id,),
                    )
                except Exception:
                    pass
                # Do not store Stripe IDs on organizations; canonical table is organization_subscriptions via webhook

        # Do not upsert into organization_subscriptions here; webhook will handle persistence

        return {"status": "success", "organization_id": org_id, "customer_id": customer_id, "subscription_id": subscription_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete checkout")

@router.post("/customer_portal")
def create_customer_portal(req: CustomerPortalRequest) -> Dict[str, Any]:
    try:
        # Validate admin
        from services.organization_service import OrganizationService
        org_service = OrganizationService()
        if not org_service.is_user_admin(req.organization_id, req.acting_user_id):
            raise HTTPException(status_code=403, detail="Admin role required")

        # Lookup customer_id
        stripe.api_key = Credentials.get_stripe_api_key()
        customer_id = None
        with org_service.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT stripe_customer_id FROM organization_subscriptions WHERE organization_id = %s",
                    (req.organization_id,),
                )
                row = cur.fetchone()
                customer_id = row[0] if row and row[0] else None
        if not customer_id:
            raise HTTPException(status_code=404, detail="Stripe klant niet gevonden voor organisatie")

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=str(req.return_url),
        )
        return {"status": "success", "url": session.url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create customer portal session: {e}")
        raise HTTPException(status_code=500, detail="Kon klantportaal niet openen")

