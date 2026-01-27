from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Request
import stripe

from definitions.credentials import Credentials
from logger.logger import Logger
from services.organization_service import OrganizationService


logger = Logger.get_logger(__name__)
router = APIRouter(prefix="/stripe", tags=["stripe"])


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")) -> Dict[str, Any]:
    payload = await request.body()
    webhook_secret = Credentials.get_stripe_webhook_secret()
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=webhook_secret,
        )
    except Exception as e:
        logger.warning(f"Invalid Stripe webhook signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        # We can be surgical, but for now trigger a refresh on relevant events
        event_type = event.get("type")
        data_object = event.get("data", {}).get("object", {})
        # Reuse a module-level singleton to avoid exhausting DB connections
        global _ORG_SVC_SINGLETON
        try:
            _ORG_SVC_SINGLETON
        except NameError:
            _ORG_SVC_SINGLETON = OrganizationService()
        org_service = _ORG_SVC_SINGLETON

        logger.info(f"Stripe webhook event: {event_type}")

        # Map subscription/customer IDs to orgs
        related_org_ids = []
        subscription_id = data_object.get("id") if data_object.get("object") == "subscription" else data_object.get("subscription")
        customer_id = data_object.get("customer")

        # Find organizations by subscription_id or customer_id
        try:
            with org_service.get_connection() as conn:
                with conn.cursor() as cur:
                    if subscription_id:
                        cur.execute(
                            "SELECT organization_id FROM organization_subscriptions WHERE stripe_subscription_id = %s",
                            (subscription_id,),
                        )
                        related_org_ids += [r[0] for r in cur.fetchall()]
                    if customer_id:
                        cur.execute(
                            "SELECT organization_id FROM organization_subscriptions WHERE stripe_customer_id = %s",
                            (customer_id,),
                        )
                        related_org_ids += [r[0] for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"Error mapping webhook to organizations: {e}")

        # Handle checkout.session.completed to immediately persist org_subscriptions
        if event_type == "checkout.session.completed":
            logger.info(f"Handling checkout.session.completed for organizations: {event_type}")
            try:
                import stripe as _stripe
                _stripe.api_key = Credentials.get_stripe_api_key()
                session_id = data_object.get("id")
                # expand to get customer/subscription ids
                session = _stripe.checkout.Session.retrieve(session_id, expand=["subscription", "customer"]) if session_id else None
                logger.info(f"Session: {session.metadata}")
                if session:
                    org_id_meta = None
                    try:
                        org_id_meta = session.metadata.get("organization_id") if hasattr(session, "metadata") else None
                    except Exception:
                        logger.warning(f"No organization_id found in session metadata")
                        org_id_meta = None
                    # Derive ids
                    try:
                        subscription_id = session.subscription.id if getattr(session, "subscription", None) else None
                    except Exception:
                        logger.warning(f"No subscription_id found in session")
                        subscription_id = None
                    try:
                        customer_id = session.customer.id if getattr(session, "customer", None) else session.customer
                    except Exception:
                        logger.warning(f"No customer_id found in session")
                        customer_id = None

                    if org_id_meta:
                        logger.info(f"Persisting checkout completion for org {org_id_meta}")
                        with org_service.get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute(
                                    """
                                    INSERT INTO organization_subscriptions (
                                        organization_id, stripe_customer_id, stripe_subscription_id, created_at, updated_at
                                    ) VALUES (%s, %s, %s, NOW(), NOW())
                                    ON CONFLICT (organization_id) DO UPDATE SET
                                        stripe_customer_id = COALESCE(EXCLUDED.stripe_customer_id, organization_subscriptions.stripe_customer_id),
                                        stripe_subscription_id = COALESCE(EXCLUDED.stripe_subscription_id, organization_subscriptions.stripe_subscription_id),
                                        updated_at = NOW()
                                    """,
                                    (org_id_meta, customer_id, subscription_id),
                                )
                        # If subscription object is available, apply details directly
                        try:
                            if subscription_id:
                                sub = _stripe.Subscription.retrieve(subscription_id)
                                org_service._upsert_org_subscription(org_id_meta, sub)
                        except Exception:
                            logger.warning(f"Failed to apply subscription payload to org {org_id_meta}")
                            pass
            except Exception as e:
                logger.warning(f"Failed to handle checkout.session.completed: {e}")

        # If the event contains a complete subscription object, apply it directly
        if event_type and event_type.startswith("customer.subscription") and data_object.get("object") == "subscription":
            # logger.info(f"Applying subscription payload to organizations: {related_org_ids}")
            for org_id in set(related_org_ids):
                try:
                    org_service.apply_subscription_payload(org_id, data_object)
                except Exception as e:
                    logger.warning(f"Failed to apply payload to org {org_id}: {e}")
            # Capture overage subscription_item id if present
            try:
                items = data_object.get("items", {}).get("data", [])
                for it in items:
                    price = it.get("price") or it.get("plan")
                    if price and price.get("recurring", {}).get("usage_type") == "metered":
                        overage_item_id = it.get("id")
                        for org_id in set(related_org_ids):
                            with org_service.get_connection() as conn:
                                with conn.cursor() as cur:
                                    cur.execute(
                                        """
                                        UPDATE organization_subscriptions
                                        SET overage_item_id = %s, updated_at = NOW()
                                        WHERE organization_id = %s
                                        """,
                                        (overage_item_id, org_id),
                                    )
            except Exception as e:
                logger.warning(f"Failed to store overage item id: {e}")
        else:
            # Generic fallback: refresh organizations via Stripe API
            for org_id in set(related_org_ids):
                try:
                    org_service.refresh_subscription_from_stripe(org_id)
                except Exception as e:
                    logger.warning(f"Failed to refresh org {org_id} from webhook: {e}")

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Stripe webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")


