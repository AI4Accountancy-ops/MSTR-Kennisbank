from datetime import datetime
from typing import Dict, Any, Optional
import contextlib

import psycopg2
import stripe

from config.settings import get_settings
from definitions.credentials import Credentials
from logger.logger import Logger
from services.repositories.whitelist_repo import WhitelistRepository
from services.db import get_connection

logger = Logger.get_logger(__name__)


class UserService:
    """Service for managing users in PostgreSQL database."""

    def __init__(self):
        """Initialize database connection pool."""
        self.settings = get_settings()
        self.database_url = self.settings.database_url
        self.stripe_api_key = Credentials.get_stripe_api_key()
        self.stripe_product_id = Credentials.get_stripe_product_id()
        # Initialize Postgres repository for whitelist checking
        self.whitelist_repo = WhitelistRepository()
        
        # Use shared DB pool via services.db
        
        # Ensure the users table exists on initialization
        self._ensure_users_table_exists()

    def __del__(self):
        # Shared pool is managed globally
        return

    @contextlib.contextmanager
    def get_connection(self):
        """Yield a connection from the shared pool."""
        with get_connection() as conn:
            yield conn

    def _ensure_users_table_exists(self):
        """Create the users table if it doesn't already exist."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Create the 'users' table if needed
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS users (
                            id VARCHAR(255) PRIMARY KEY,
                            email VARCHAR(255) NOT NULL,
                            name VARCHAR(255),
                            auth_provider VARCHAR(50) NOT NULL,
                            is_subscribed BOOLEAN NOT NULL,
                            last_login TIMESTAMP NOT NULL,
                            created_at TIMESTAMP NOT NULL,
                            updated_at TIMESTAMP
                        );
                        """
                    )
                    # Create index on email for faster lookups
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS users_email_idx ON users (email);
                        """
                    )
                    logger.info("Table 'users' is ready")
                    conn.commit()
        except Exception as e:
            logger.error(f"Error ensuring users table exists: {str(e)}")
            raise

    def is_email_whitelisted(self, email: str) -> bool:
        """
        Check if an email is in the whitelist (Postgres-backed).
        """
        try:
            result = self.whitelist_repo.is_email_whitelisted(email)
            logger.info(
                f"Email {email} is {'in' if result else 'not in'} the whitelist (Postgres)"
            )
            return result
        except Exception as e:
            logger.error(f"Error checking whitelist for email {email}: {str(e)}")
            return False

    def save_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save or update user data in the PostgreSQL database.
        
        Args:
            user_data: Dictionary containing user information
                - id: User ID from auth provider
                - email: User email
                - name: User display name
                - auth_provider: Authentication provider (microsoft, google)
                - is_subscribed: Whether the user is subscribed to the service

        Returns:
            Dict: Contains success status, message, and additional data if successful
        """
        try:
            # Extract fields from user_data
            user_id = user_data.get('user_id') or user_data.get('id')
            email = user_data.get('email')
            name = user_data.get('name', '')
            auth_provider = user_data.get('auth_provider')
            
            # Check if is_subscribed was explicitly provided
            is_subscribed = user_data.get('is_subscribed')
            
            # If not explicitly provided as True, check whitelist and then Stripe
            if email and (is_subscribed is None or is_subscribed is False):
                # First check if the email is whitelisted
                is_whitelisted = self.is_email_whitelisted(email)
                
                if is_whitelisted:
                    logger.info(f"Setting is_subscribed=True for email {email} based on whitelist")
                    is_subscribed = True
                    user_data['is_subscribed'] = True
                else:
                    # If not whitelisted, check Stripe
                    is_stripe_subscribed = self.check_stripe_subscription(email)
                    if is_stripe_subscribed:
                        logger.info(f"Setting is_subscribed=True for email {email} based on Stripe subscription")
                        is_subscribed = True
                        user_data['is_subscribed'] = True
                    elif is_subscribed is None:
                        # Default to False if not specified and not found in whitelist or Stripe
                        is_subscribed = False
            
            # Validate required fields
            if not user_id:
                logger.error("Missing required user data field: user_id")
                return {"success": False, "error": "missing_field", "message": "User ID is required"}
            
            if not email:
                logger.error("Missing required user data field: email")
                return {"success": False, "error": "missing_field", "message": "Email is required"}
            
            if not auth_provider:
                logger.error("Missing required user data field: auth_provider")
                return {"success": False, "error": "missing_field", "message": "Authentication provider is required"}
            
            current_time = datetime.now().isoformat()
            
            # Use a connection from the pool with transaction management
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if table exists
                    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')")
                    table_exists = cur.fetchone()[0]
                    
                    if not table_exists:
                        logger.warning("Users table does not exist, creating it")
                        self._ensure_users_table_exists()
                    
                    # Use FOR UPDATE SKIP LOCKED to acquire row lock or skip if already locked
                    # If row doesn't exist, no lock is obtained and we proceed to insert
                    cur.execute(
                        "SELECT id FROM users WHERE id = %s FOR UPDATE SKIP LOCKED", 
                        (user_id,)
                    )
                    user_exists = cur.fetchone() is not None
                    
                    if user_exists:
                        logger.info(f"User {user_id} exists, updating")
                        # Update existing user
                        cur.execute(
                            """
                            UPDATE users 
                            SET email = %s, 
                                name = %s, 
                                auth_provider = %s,
                                is_subscribed = %s,
                                last_login = %s,
                                updated_at = %s
                            WHERE id = %s
                            """,
                            (email, name, auth_provider, is_subscribed, current_time, current_time, user_id)
                        )
                        action = "updated"
                    else:
                        # Double-check without locking to detect race conditions
                        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                        already_exists = cur.fetchone() is not None
                        
                        if already_exists:
                            # Another transaction has inserted the user between our check and lock
                            logger.warning(f"Detected race condition for user {user_id}, another transaction inserted the user")
                            
                            # Try to acquire lock for update
                            try:
                                cur.execute(
                                    "SELECT id FROM users WHERE id = %s FOR UPDATE NOWAIT", 
                                    (user_id,)
                                )
                                # We got the lock, update the user
                                cur.execute(
                                    """
                                    UPDATE users 
                                    SET email = %s, 
                                        name = %s, 
                                        auth_provider = %s,
                                        is_subscribed = %s,
                                        last_login = %s,
                                        updated_at = %s
                                    WHERE id = %s
                                    """,
                                    (email, name, auth_provider, is_subscribed, current_time, current_time, user_id)
                                )
                                action = "updated (concurrent)"
                            except psycopg2.Error as lock_err:
                                # Couldn't get the lock, another transaction is updating
                                logger.warning(f"Could not acquire lock for {user_id}: {str(lock_err)}")
                                action = "skipped (locked)"
                                # We'll just commit the transaction without changes
                        else:
                            # The user doesn't exist, so insert a new row
                            logger.info(f"User {user_id} doesn't exist, inserting")
                            cur.execute(
                                """
                                INSERT INTO users 
                                (id, email, name, auth_provider, is_subscribed, last_login, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """,
                                (user_id, email, name, auth_provider, is_subscribed, current_time, current_time)
                            )
                            action = "created"
                
                # The transaction will be committed by the context manager
                logger.info(f"User {user_id} {action} successfully, transaction ready to commit")
                return {
                    "success": True, 
                    "action": action, 
                    "user_id": user_id,
                    "message": f"User {action} successfully"
                }
                
        except psycopg2.OperationalError as op_err:
            logger.error(f"Database connection error: {str(op_err)}")
            return {"success": False, "error": "db_connection_error", "message": "Database connection error"}
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Error saving user data ({error_type}): {str(e)}")
            return {"success": False, "error": "unknown_error", "message": f"Unexpected error: {str(e)}"}

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user data by ID.
        
        Args:
            user_id: User ID to retrieve
            
        Returns:
            Dict containing user data or None if not found
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, email, name, auth_provider, is_subscribed, last_login, created_at
                        FROM users WHERE id = %s
                        """,
                        (user_id,)
                    )
                    user_data = cur.fetchone()
                    
                    if not user_data:
                        logger.info(f"User {user_id} not found in database")
                        return None
                    
                    logger.info(f"User {user_id} found in database, is_subscribed: {user_data[4]}")
                    return {
                        "id": user_data[0],
                        "email": user_data[1],
                        "name": user_data[2],
                        "auth_provider": user_data[3],
                        "is_subscribed": user_data[4],
                        "last_login": user_data[5].isoformat() if user_data[5] else None,
                        "created_at": user_data[6].isoformat() if user_data[6] else None
                    }
                    
        except Exception as e:
            logger.error(f"Error retrieving user data: {str(e)}")
            return None 

    def check_user_subscription(self, user_id: str) -> bool:
        """
        Check if a user has access using DB-only checks.
        Prefer organization subscription; fallback to user's is_subscribed or whitelist.
        
        Args:
            user_id: The ID of the user to check
            
        Returns:
            bool: True if the user exists and is subscribed, False otherwise
        """
        return self.has_access_fast(user_id)

    def has_access_fast(self, user_id: str) -> bool:
        """DB-only access check. No Stripe calls.
        1) Any active organization subscription the user belongs to
        2) Fallback: user's is_subscribed flag
        3) Fallback: whitelist email
        """
        logger.info(f"Fast access check for user {user_id}")
        user_data = self.get_user(user_id)
        if not user_data:
            logger.warning(f"User {user_id} not found in database during access check")
            return False

        try:
            from services.organization_service import OrganizationService
            # Reuse a module-level singleton to avoid exhausting DB connections
            global _ORG_SVC_SINGLETON
            try:
                _ORG_SVC_SINGLETON
            except NameError:
                _ORG_SVC_SINGLETON = OrganizationService()
            org_service = _ORG_SVC_SINGLETON
            if org_service.user_has_active_org_subscription(user_id):
                return True
        except Exception as e:
            logger.warning(f"Organization subscription check failed for user {user_id}: {e}")

        if user_data.get('is_subscribed', False):
            return True

        email = user_data.get('email')
        if email and self.is_email_whitelisted(email):
            return True

        return False
        
    def check_stripe_subscription(self, email: str) -> bool:
        """
        Check if a user has an active subscription in Stripe for the specified product.
        
        Args:
            email: The email address of the user to check
            
        Returns:
            bool: True if the user has an active subscription, False otherwise
        """
        try:            
            # Set Stripe API key
            stripe.api_key = self.stripe_api_key
            
            # The product ID to check for
            target_product_id = self.stripe_product_id
            
            # Get customers with the provided email
            customers = stripe.Customer.list(email=email, limit=3)
            
            if not customers.data:
                logger.info(f"No customer found with email {email}")
                return False
            
            # Check if any customer has an active subscription with the target product
            for customer in customers.data:
                # Get active subscriptions for this customer without using too deep expand
                subscriptions = stripe.Subscription.list(
                    customer=customer.id, 
                    status="active", 
                    limit=10
                )
                
                if not subscriptions.data:
                    continue
                
                # Check each subscription
                for subscription in subscriptions.data:
                    # Access the items using the appropriate method
                    items = stripe.SubscriptionItem.list(subscription=subscription.id)
                    
                    # Check each item in the subscription
                    for item in items.data:
                        if not hasattr(item, 'price') or not item.price or not item.price.id:
                            continue
                            
                        # Get price details separately with single level expand
                        price = stripe.Price.retrieve(
                            item.price.id,
                            expand=["product"]
                        )
                        
                        if price and hasattr(price, 'product') and price.product and price.product.id == target_product_id:
                            logger.info(f"Found active subscription for product {target_product_id} for email {email}")
                            return True
            
            # No active subscription found
            logger.info(f"No active subscription found for product {target_product_id} for email {email}")
            return False
        
        except ImportError as e:
            logger.error(f"Error importing stripe module: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error checking Stripe subscription: {str(e)}")
            return False 

    def promote_if_whitelisted(self, user_id: str) -> Dict[str, Any]:
        """
        If the user's email is in the whitelist, set users.is_subscribed = TRUE.
        Returns { is_whitelisted: bool, updated: bool }.
        """
        try:
            user = self.get_user(user_id)
            if not user:
                return {"is_whitelisted": False, "updated": False, "message": "User not found"}
            email = user.get("email")
            if not email:
                return {"is_whitelisted": False, "updated": False, "message": "Email missing"}

            if not self.is_email_whitelisted(email):
                return {"is_whitelisted": False, "updated": False}

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET is_subscribed = TRUE, updated_at = %s
                        WHERE id = %s
                        """,
                        (datetime.now().isoformat(), user_id),
                    )
            return {"is_whitelisted": True, "updated": True}
        except Exception as e:
            logger.error(f"promote_if_whitelisted failed for {user_id}: {e}")
            return {"is_whitelisted": False, "updated": False, "error": "internal_error"}