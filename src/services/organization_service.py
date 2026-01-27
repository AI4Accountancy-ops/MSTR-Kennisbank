from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import time
import uuid
import contextlib

import psycopg2
import stripe

from config.settings import get_settings
from definitions.credentials import Credentials
from logger.logger import Logger
from services.db import get_connection


logger = Logger.get_logger(__name__)


class OrganizationService:
    """Service for managing organizations, memberships, invitations and subscriptions."""

    def __init__(self):
        self.settings = get_settings()
        self.database_url = self.settings.database_url
        self.stripe_api_key = Credentials.get_stripe_api_key()
        # Stripe Meters: event name configured in Dashboard (e.g., "ai_requests")
        self.METER_EVENT_NAME: str = "ai_requests"
        # Product → monthly question quota mapping
        # New products:
        #  - Instap €49: 250
        #  - Groei  €149: 1000
        #  - Pro    €349: 2500
        self.PRODUCT_QUOTAS: Dict[str, int] = {
            # Map Stripe product IDs to quotas
            # Update these IDs if they change in Stripe
            "prod_T9EMiXbHFZajKD": 250,   # Instap
            "prod_T9EMjATRUTd01T": 1000,  # Groei
            "prod_T9ENg8YAVns3Cf": 2500,  # Pro
            "prod_TBdhFYzLySpZXs": 7500,  # Enterprise
        }

        # Uses shared pool via services.db

    def __del__(self):
        # Shared pool is managed globally; nothing to close here
        return

    @contextlib.contextmanager
    def get_connection(self):
        with get_connection() as conn:
            yield conn

    # --------------------------
    # Organization CRUD
    # --------------------------
    def create_organization(self, owner_user_id: str, name: str, description: Optional[str] = None) -> Optional[str]:
        org_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Enforce single organization per owner (admin)
                    cur.execute(
                        "SELECT id FROM organizations WHERE owner_user_id = %s LIMIT 1",
                        (owner_user_id,),
                    )
                    existing = cur.fetchone()
                    if existing and existing[0]:
                        existing_org_id = existing[0]
                        # Ensure owner is recorded as admin member
                        cur.execute(
                            """
                            INSERT INTO organization_members (organization_id, user_id, role, created_at)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (organization_id, user_id)
                            DO UPDATE SET role = EXCLUDED.role, updated_at = %s
                            """,
                            (existing_org_id, owner_user_id, "admin", now, now),
                        )
                        return existing_org_id

                    cur.execute(
                        """
                        INSERT INTO organizations (id, name, owner_user_id, description, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (org_id, name, owner_user_id, description, now),
                    )
                    # Owner is admin member by default
                    cur.execute(
                        """
                        INSERT INTO organization_members (organization_id, user_id, role, created_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (organization_id, user_id)
                        DO UPDATE SET role = EXCLUDED.role, updated_at = %s
                        """,
                        (org_id, owner_user_id, "admin", now, now),
                    )
            return org_id
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            return None

    def get_organization(self, organization_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, name, owner_user_id, created_at, updated_at
                        FROM organizations
                        WHERE id = %s
                        """,
                        (organization_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None

                    org = {
                        "id": row[0],
                        "name": row[1],
                        "owner_user_id": row[2],
                        "created_at": row[3].isoformat() if row[3] else None,
                        "updated_at": row[4].isoformat() if row[4] else None,
                    }

                    # Members
                    cur.execute(
                        """
                        SELECT user_id, role
                        FROM organization_members
                        WHERE organization_id = %s
                        """,
                        (organization_id,),
                    )
                    org["members"] = [{"user_id": r[0], "role": r[1]} for r in cur.fetchall()]
                    return org
        except Exception as e:
            logger.error(f"Error fetching organization: {e}")
            return None

    def list_organizations_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT o.id, o.name, om.role, s.status AS subscription_status, s.current_period_end, s.stripe_price_id
                        FROM organization_members om
                        JOIN organizations o ON o.id = om.organization_id
                        LEFT JOIN organization_subscriptions s ON s.organization_id = o.id
                        WHERE om.user_id = %s
                        ORDER BY o.created_at DESC
                        """,
                        (user_id,),
                    )
                    rows = cur.fetchall()
                    return [
                        {
                            "id": r[0],
                            "name": r[1],
                            "role": r[2],
                            "subscription_status": r[3],
                            "current_period_end": r[4].isoformat() if r[4] else None,
                            "stripe_price_id": r[5],
                        }
                        for r in rows
                    ]
        except Exception as e:
            logger.error(f"Error listing organizations for user: {e}")
            return []

    def get_first_active_org_for_user(self, user_id: str) -> Optional[str]:
        """Return the first organization_id with an active subscription for the user, or None."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT o.id
                        FROM organization_members om
                        JOIN organizations o ON o.id = om.organization_id
                        WHERE om.user_id = %s
                        ORDER BY o.created_at ASC
                        """,
                        (user_id,),
                    )
                    org_ids = [r[0] for r in cur.fetchall()]
            for org_id in org_ids:
                if self.has_active_subscription(org_id):
                    return org_id
            return None
        except Exception as e:
            logger.error(f"Error finding active org for user: {e}")
            return None

    # --------------------------
    # Memberships
    # --------------------------
    def is_user_admin(self, organization_id: str, user_id: str) -> bool:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT 1 FROM organization_members
                        WHERE organization_id = %s AND user_id = %s AND role = 'admin'
                        LIMIT 1
                        """,
                        (organization_id, user_id),
                    )
                    return cur.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking admin role: {e}")
            return False

    def add_member(self, organization_id: str, user_id: str, role: str = "user") -> bool:
        if role not in ("admin", "user"):
            return False
        now = datetime.now().isoformat()
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO organization_members (organization_id, user_id, role, created_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (organization_id, user_id)
                        DO UPDATE SET role = EXCLUDED.role, updated_at = %s
                        """,
                        (organization_id, user_id, role, now, now),
                    )
            return True
        except Exception as e:
            logger.error(f"Error adding member: {e}")
            return False

    def update_member_role(self, organization_id: str, user_id: str, role: str) -> bool:
        if role not in ("admin", "user"):
            return False
        now = datetime.now().isoformat()
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE organization_members
                        SET role = %s, updated_at = %s
                        WHERE organization_id = %s AND user_id = %s
                        """,
                        (role, now, organization_id, user_id),
                    )
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating member role: {e}")
            return False

    def remove_member(self, organization_id: str, user_id: str) -> bool:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM organization_members WHERE organization_id = %s AND user_id = %s",
                        (organization_id, user_id),
                    )
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing member: {e}")
            return False

    # Invitation flow removed in favor of direct admin add of members.

    # --------------------------
    # Subscriptions
    # --------------------------
    def has_active_subscription(self, organization_id: str) -> bool:
        """Return True if the organization has an active (or trialing) subscription.
        Reads exclusively from organization_subscriptions.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT status, current_period_end
                        FROM organization_subscriptions
                        WHERE organization_id = %s
                        """,
                        (organization_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return False
                    status, current_period_end = row
                    if status in ("active", "trialing"):
                        # Compare against aware UTC now to match stored UTC timestamps
                        # Coerce DB value to aware UTC if naive
                        now_utc = datetime.now(timezone.utc)
                        if current_period_end is None:
                            return True
                        try:
                            cpe_dt = current_period_end if current_period_end.tzinfo else current_period_end.replace(tzinfo=timezone.utc)
                        except AttributeError:
                            # If stored as string, parse isoformat
                            try:
                                parsed = datetime.fromisoformat(str(current_period_end))
                                cpe_dt = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
                            except Exception:
                                # Fallback: deny if unreadable
                                return False
                        if cpe_dt > now_utc:
                            return True
                    return False
        except Exception as e:
            logger.error(f"Error checking organization subscription: {e}")
            return False

    def user_has_active_org_subscription(self, user_id: str) -> bool:
        """Return True if the user belongs to any org with an active subscription."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT organization_id
                        FROM organization_members
                        WHERE user_id = %s
                        """,
                        (user_id,),
                    )
                    org_ids = [r[0] for r in cur.fetchall()]
            for org_id in org_ids:
                if self.has_active_subscription(org_id):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking user org subscription: {e}")
            return False

    def refresh_subscription_from_stripe(self, organization_id: str) -> bool:
        """Fetch latest subscription info from Stripe and persist it.

        This assumes the organization has either stripe_customer_id or stripe_subscription_id stored.
        """
        try:
            stripe.api_key = self.stripe_api_key
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT stripe_customer_id, stripe_subscription_id
                        FROM organization_subscriptions
                        WHERE organization_id = %s
                        """,
                        (organization_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return False
                    stripe_customer_id, stripe_subscription_id = row

            subscription_obj = None
            if stripe_subscription_id:
                subscription_obj = stripe.Subscription.retrieve(stripe_subscription_id)
            elif stripe_customer_id:
                # Take the most recent active/trialing subscription
                subs = stripe.Subscription.list(customer=stripe_customer_id, limit=3)
                for s in subs.data:
                    if s.status in ("active", "trialing"):
                        subscription_obj = s
                        break
                if not subscription_obj and subs.data:
                    subscription_obj = subs.data[0]
            else:
                return False

            if not subscription_obj:
                # Clear status
                self._upsert_org_subscription(organization_id, None)
                return False

            self._upsert_org_subscription(organization_id, subscription_obj)
            return True
        except Exception as e:
            logger.error(f"Error refreshing subscription from Stripe: {e}")
            return False

    # --------------------------
    # Subscription Changes
    # --------------------------
    def _get_current_subscription(self, organization_id: str) -> Optional[Any]:
        """
        Retrieve the Stripe Subscription object for the organization's current subscription
        using stored stripe_subscription_id or by listing active/trialing subscriptions by customer.
        """
        try:
            stripe.api_key = self.stripe_api_key
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT stripe_customer_id, stripe_subscription_id
                        FROM organization_subscriptions
                        WHERE organization_id = %s
                        """,
                        (organization_id,),
                    )
                    row = cur.fetchone()
            if not row:
                return None
            stripe_customer_id, stripe_subscription_id = row
            if stripe_subscription_id:
                return stripe.Subscription.retrieve(stripe_subscription_id, expand=["items.data.price"])
            if stripe_customer_id:
                subs = stripe.Subscription.list(customer=stripe_customer_id, status="all", limit=5)
                for s in subs.data:
                    if s.status in ("active", "trialing"):
                        return stripe.Subscription.retrieve(s.id, expand=["items.data.price"])
                if subs.data:
                    return stripe.Subscription.retrieve(subs.data[0].id, expand=["items.data.price"])
            return None
        except Exception as e:
            logger.error(f"_get_current_subscription failed: {e}")
            return None

    def refresh_all_subscriptions_from_stripe(self) -> int:
        """Refresh subscriptions for all organizations. Returns number refreshed."""
        refreshed = 0
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM organizations")
                    org_ids = [r[0] for r in cur.fetchall()]
            for org_id in org_ids:
                if self.refresh_subscription_from_stripe(org_id):
                    refreshed += 1
            return refreshed
        except Exception as e:
            logger.error(f"Error refreshing all subscriptions: {e}")
            return refreshed

    def _upsert_org_subscription(self, organization_id: str, subscription: Optional[Any]) -> None:
        """Persist subscription details to organization_subscriptions if exists, else to organizations."""
        now = datetime.now().isoformat()
        status = None
        current_period_end = None
        stripe_customer_id = None
        stripe_subscription_id = None
        stripe_price_id = None
        stripe_product_id = None
        current_period_start = None
        if subscription is not None:
            status = getattr(subscription, "status", None)
            cpe = getattr(subscription, "current_period_end", None)
            # Convert Stripe epoch seconds to UTC (aware) to avoid local timezone/DST shifts
            current_period_end = (
                datetime.fromtimestamp(cpe, tz=timezone.utc).isoformat() if cpe else None
            )
            cps = getattr(subscription, "current_period_start", None)
            current_period_start = (
                datetime.fromtimestamp(cps, tz=timezone.utc).isoformat() if cps else None
            )
            stripe_subscription_id = subscription.id
            if getattr(subscription, "customer", None):
                stripe_customer_id = subscription.customer
            # Extract first item price/product
            try:
                if subscription.items and subscription.items.data:
                    item = subscription.items.data[0]
                    if item.price:
                        stripe_price_id = item.price.id
                        if hasattr(item.price, "product"):
                            stripe_product_id = item.price.product if isinstance(item.price.product, str) else item.price.product.id
            except Exception:
                pass

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Try insert into organization_subscriptions
                    cur.execute(
                        """
                        INSERT INTO organization_subscriptions
                            (organization_id, stripe_customer_id, stripe_subscription_id, stripe_price_id, stripe_product_id,
                             status, current_period_start, current_period_end, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (organization_id)
                        DO UPDATE SET
                            stripe_customer_id = EXCLUDED.stripe_customer_id,
                            stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                            stripe_price_id = EXCLUDED.stripe_price_id,
                            stripe_product_id = EXCLUDED.stripe_product_id,
                            status = EXCLUDED.status,
                            current_period_start = EXCLUDED.current_period_start,
                            current_period_end = EXCLUDED.current_period_end,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            organization_id,
                            stripe_customer_id,
                            stripe_subscription_id,
                            stripe_price_id,
                            stripe_product_id,
                            status,
                            datetime.fromisoformat(current_period_start) if current_period_start else None,
                            datetime.fromisoformat(current_period_end) if current_period_end else None,
                            now,
                            now,
                        ),
                    )
        except Exception as e:
            logger.error(f"Error upserting organization subscription: {e}")

    def apply_subscription_payload(self, organization_id: str, payload: Dict[str, Any]) -> None:
        """Update org subscription rows directly from a Stripe subscription event payload.

        Expected keys in payload (as received in webhook):
          id, customer, status, current_period_start/current_period_end (or under items.data[0])
          items.data[0].price.id, items.data[0].price.product
        """
        now = datetime.now().isoformat()
        try:
            status = payload.get("status")
            stripe_subscription_id = payload.get("id")
            stripe_customer_id = payload.get("customer")

            # Prefer root-level period if present; otherwise fallback to first item
            cps = payload.get("current_period_start")
            cpe = payload.get("current_period_end")
            price_id = None
            product_id = None
            try:
                items = payload.get("items", {}).get("data", [])
                if items:
                    first = items[0]
                    # Some API versions provide period on item
                    if not cps:
                        cps = first.get("current_period_start")
                    if not cpe:
                        cpe = first.get("current_period_end")
                    price = first.get("price") or first.get("plan")
                    if price:
                        price_id = price.get("id")
                        product_id = price.get("product") if isinstance(price.get("product"), str) else price.get("product", {}).get("id")
            except Exception:
                pass

            current_period_start = (
                datetime.fromtimestamp(cps, tz=timezone.utc).isoformat() if cps else None
            )
            current_period_end = (
                datetime.fromtimestamp(cpe, tz=timezone.utc).isoformat() if cpe else None
            )

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO organization_subscriptions
                            (organization_id, stripe_customer_id, stripe_subscription_id, stripe_price_id, stripe_product_id,
                             status, current_period_start, current_period_end, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (organization_id)
                        DO UPDATE SET
                            stripe_customer_id = EXCLUDED.stripe_customer_id,
                            stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                            stripe_price_id = EXCLUDED.stripe_price_id,
                            stripe_product_id = EXCLUDED.stripe_product_id,
                            status = EXCLUDED.status,
                            current_period_start = EXCLUDED.current_period_start,
                            current_period_end = EXCLUDED.current_period_end,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            organization_id,
                            stripe_customer_id,
                            stripe_subscription_id,
                            price_id,
                            product_id,
                            status,
                            datetime.fromisoformat(current_period_start) if current_period_start else None,
                            datetime.fromisoformat(current_period_end) if current_period_end else None,
                            now,
                            now,
                        ),
                    )
        except Exception as e:
            logger.error(f"Error applying subscription payload: {e}")

    # --------------------------
    # Quotas
    # --------------------------
    def _get_quota_for_product(self, product_id: Optional[str]) -> int:
        if not product_id:
            return 0
        return self.PRODUCT_QUOTAS.get(str(product_id), 0)

    def _get_subscription_row_for_update(self, cur, organization_id: str) -> Optional[tuple]:
        try:
            cur.execute(
                """
                SELECT stripe_product_id, current_period_start, current_period_end, status,
                       COALESCE(questions_used, 0)
                FROM organization_subscriptions
                WHERE organization_id = %s
                FOR UPDATE
                """,
                (organization_id,),
            )
            return cur.fetchone()
        except Exception as e:
            logger.warning(f"Could not load subscriptions row for update (maybe missing table/cols): {e}")
            return None

    def consume_quota_if_available(self, organization_id: str) -> Dict[str, Any]:
        """Consume 1 question and report whether it exceeds the plan quota.

        Returns { allowed: bool, used: int, quota: int, over_quota: bool }.
        Trial: enforce daily 1000 cap (allowed=False when exceeded). Post‑trial: never block; over_quota indicates billing.
        """
        now_dt = datetime.now()
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # If in trial, enforce daily quota of 1000 using organization_daily_usage
                    try:
                        cur.execute(
                            "SELECT status FROM organization_subscriptions WHERE organization_id = %s",
                            (organization_id,),
                        )
                        row_status = cur.fetchone()
                        in_trial = bool(row_status and row_status[0] == "trialing")
                    except Exception:
                        in_trial = False

                    if in_trial:
                        usage_date = now_dt.date()
                        # Upsert daily usage row
                        try:
                            cur.execute(
                                """
                                INSERT INTO organization_daily_usage (organization_id, usage_date, questions_used)
                                VALUES (%s, %s, 1)
                                ON CONFLICT (organization_id, usage_date)
                                DO UPDATE SET questions_used = organization_daily_usage.questions_used + 1
                                RETURNING questions_used
                                """,
                                (organization_id, usage_date),
                            )
                            used_today = cur.fetchone()[0]
                        except Exception:
                            # Create table if missing or allow by default
                            used_today = 1
                        quota_today = 1000
                        if used_today > quota_today:
                            # Roll back last increment if we overshot
                            try:
                                cur.execute(
                                    "UPDATE organization_daily_usage SET questions_used = questions_used - 1 WHERE organization_id = %s AND usage_date = %s",
                                    (organization_id, usage_date),
                                )
                            except Exception:
                                pass
                            return {"allowed": False, "used": used_today - 1, "quota": quota_today, "over_quota": True}
                        return {"allowed": True, "used": used_today, "quota": quota_today, "over_quota": used_today > quota_today}

                    row = self._get_subscription_row_for_update(cur, organization_id)
                    if not row:
                        # Fallback: allow until schema is ready
                        return {"allowed": True, "used": 0, "quota": 0, "over_quota": False}
                    product_id, period_start, period_end, status, used = row
                    quota = self._get_quota_for_product(product_id)
                    # If no quota configured, allow
                    if quota <= 0:
                        return {"allowed": True, "used": used or 0, "quota": quota, "over_quota": False}
                    # Reset if period passed
                    if period_end and now_dt > period_end:
                        used = 0
                        try:
                            cur.execute(
                                "UPDATE organization_subscriptions SET questions_used = %s WHERE organization_id = %s",
                                (0, organization_id),
                            )
                        except Exception:
                            pass
                    # Post‑trial: always increment; do not block
                    new_used = (used or 0) + 1
                    try:
                        cur.execute(
                            "UPDATE organization_subscriptions SET questions_used = %s WHERE organization_id = %s",
                            (new_used, organization_id),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update questions_used (schema missing?): {e}")
                    return {"allowed": True, "used": new_used, "quota": quota, "over_quota": new_used > quota}
        except Exception as e:
            logger.error(f"Error consuming quota: {e}")
            return {"allowed": True, "used": 0, "quota": 0, "over_quota": False}

    # --------------------------
    # Usage Reporting (Overage)
    # --------------------------
    def get_subscription_status_and_overage_item(self, organization_id: str) -> Dict[str, Optional[str]]:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT status, COALESCE(overage_item_id, NULL)
                        FROM organization_subscriptions
                        WHERE organization_id = %s
                        """,
                        (organization_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return {"status": None, "overage_item_id": None}
                    return {"status": row[0], "overage_item_id": row[1]}
        except Exception:
            return {"status": None, "overage_item_id": None}

    def get_usage_summary(self, organization_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Return usage status for UI: daily (trial) and monthly counters with quotas."""
        try:
            org_id = organization_id
            if not org_id and user_id:
                org_id = self.get_first_active_org_for_user(user_id)
            if not org_id:
                return {"error": "organization_not_found"}

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT status, stripe_product_id, current_period_start, current_period_end,
                               COALESCE(questions_used,0)
                        FROM organization_subscriptions
                        WHERE organization_id = %s
                        """,
                        (org_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return {"error": "subscription_not_found"}
                    status, product_id, cps, cpe, monthly_used = row
                    monthly_quota = self._get_quota_for_product(product_id)
                    summary: Dict[str, Any] = {
                        "organization_id": org_id,
                        "status": status,
                        "in_trial": status == "trialing",
                        "monthly_used": int(monthly_used or 0),
                        "monthly_quota": int(monthly_quota or 0),
                        "current_period_start": cps.isoformat() if cps else None,
                        "current_period_end": cpe.isoformat() if cpe else None,
                        "over_quota": (monthly_used or 0) > (monthly_quota or 0),
                    }
                    if status == "trialing":
                        # get today's daily usage
                        today = datetime.now().date()
                        try:
                            cur.execute(
                                "SELECT COALESCE(questions_used,0) FROM organization_daily_usage WHERE organization_id = %s AND usage_date = %s",
                                (org_id, today),
                            )
                            daily_used = cur.fetchone()
                            summary["daily_used"] = int(daily_used[0]) if daily_used else 0
                        except Exception:
                            summary["daily_used"] = 0
                        summary["daily_quota"] = 1000
                        summary["over_quota"] = summary["daily_used"] > summary["daily_quota"]
                    return summary
        except Exception as e:
            logger.error(f"get_usage_summary failed: {e}")
            return {"error": "internal_error"}

    def report_overage_usage(self, organization_id: str, quantity: int = 1) -> bool:
        try:
            stripe.api_key = self.stripe_api_key
        except Exception:
            return False
        info = self.get_subscription_status_and_overage_item(organization_id)
        if info.get("status") == "trialing":
            return False
        item_id = info.get("overage_item_id")
        if not item_id:
            return False
        try:
            # Emit a Stripe Meter event (Raw aggregation with value key)
            stripe.MeterEvent.create(
                event_name=self.METER_EVENT_NAME,
                payload={
                    "subscription_item": item_id,
                    "value": quantity,
                },
                timestamp=int(time.time()),
            )
            return True
        except Exception:
            return False


