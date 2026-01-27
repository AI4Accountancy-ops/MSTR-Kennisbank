"""
JSON file implementation of M365 storage interface.

This is a simple file-based storage implementation for development/testing.
For production, consider using PostgreSQL, CosmosDB, or Redis implementations.
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

from services.m365_storage import M365StorageInterface
from logger.logger import Logger


logger = Logger.get_logger(__name__)


class M365JsonStorage(M365StorageInterface):
    """JSON file-based storage for M365 data"""
    
    def __init__(self, file_path: Optional[Path] = None):
        """
        Initialize JSON storage
        
        Args:
            file_path: Path to JSON file for storage
        """
        self.file_path = file_path or (Path(__file__).parent.parent / 'api' / 'data.json')
        self._data: Dict[str, Any] = {
            'user_tokens': {},
            'subscriptions': {},
            'auth_flows': {},  # Temporary storage for OAuth flows
            'last_updated': None
        }
        self._load()
    
    def _load(self):
        """Load data from JSON file"""
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r') as f:
                    loaded_data = json.load(f)
                    # Preserve structure, merge in loaded data
                    self._data['user_tokens'] = loaded_data.get('user_tokens', {})
                    self._data['subscriptions'] = loaded_data.get('active_subscriptions', {})  # Old key name
                    if not self._data['subscriptions']:
                        self._data['subscriptions'] = loaded_data.get('subscriptions', {})
                    self._data['auth_flows'] = loaded_data.get('auth_flows', {})
                    
                logger.info(f"Loaded {len(self._data['user_tokens'])} user tokens from {self.file_path}")
                logger.info(f"Loaded {len(self._data['subscriptions'])} subscriptions from {self.file_path}")
            else:
                logger.warning(f"No existing data file found at {self.file_path}")
        except Exception as e:
            logger.error(f"Error loading data from {self.file_path}: {e}")
            self._data = {
                'user_tokens': {},
                'subscriptions': {},
                'auth_flows': {},
                'last_updated': None
            }
    
    def _save(self):
        """Save data to JSON file"""
        try:
            self._data['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            # Create directory if it doesn't exist
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.file_path, 'w') as f:
                json.dump(self._data, f, indent=2)
            
            logger.debug(f"Saved data to {self.file_path}")
            
        except Exception as e:
            logger.error(f"Error saving data to {self.file_path}: {e}")
    
    # ============================================================================
    # USER TOKEN OPERATIONS
    # ============================================================================
    
    def save_user_token(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        expires_at: float,
        token_type: str,
        scope: str,
        user_profile: Dict[str, Any]
    ) -> bool:
        """Save or update user token data"""
        try:
            self._data['user_tokens'][user_id] = {
                'user_id': user_id,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': expires_in,
                'expires_at': expires_at,
                'token_type': token_type,
                'scope': scope,
                'user_profile': user_profile
            }
            self._save()
            return True
        except Exception as e:
            logger.error(f"Failed to save user token for {user_id}: {e}")
            return False
    
    def get_user_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user token data"""
        return self._data['user_tokens'].get(user_id)
    
    def list_user_tokens(self) -> Dict[str, Dict[str, Any]]:
        """List all stored user tokens"""
        return self._data['user_tokens'].copy()
    
    def delete_user_token(self, user_id: str) -> bool:
        """Delete user token data"""
        try:
            if user_id in self._data['user_tokens']:
                del self._data['user_tokens'][user_id]
                self._save()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete user token for {user_id}: {e}")
            return False
    
    def clear_all_user_tokens(self) -> int:
        """Clear all user tokens"""
        try:
            count = len(self._data['user_tokens'])
            self._data['user_tokens'] = {}
            self._save()
            return count
        except Exception as e:
            logger.error(f"Failed to clear user tokens: {e}")
            return 0
    
    # ============================================================================
    # SUBSCRIPTION OPERATIONS
    # ============================================================================
    
    def save_subscription(
        self,
        subscription_id: str,
        user_id: str,
        resource: str,
        notification_url: str,
        expires_at: str,
        created_at: Optional[str] = None
    ) -> bool:
        """Save or update subscription data"""
        try:
            if created_at is None:
                created_at = datetime.now(timezone.utc).isoformat()
            
            self._data['subscriptions'][subscription_id] = {
                'id': subscription_id,
                'user_id': user_id,
                'resource': resource,
                'notification_url': notification_url,
                'expires_at': expires_at,
                'created_at': created_at
            }
            self._save()
            return True
        except Exception as e:
            logger.error(f"Failed to save subscription {subscription_id}: {e}")
            return False
    
    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve subscription data"""
        return self._data['subscriptions'].get(subscription_id)
    
    def list_subscriptions(self) -> Dict[str, Dict[str, Any]]:
        """List all active subscriptions"""
        return self._data['subscriptions'].copy()
    
    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete subscription data"""
        try:
            if subscription_id in self._data['subscriptions']:
                del self._data['subscriptions'][subscription_id]
                self._save()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete subscription {subscription_id}: {e}")
            return False
    
    # ============================================================================
    # AUTH FLOW OPERATIONS (temporary storage during OAuth flow)
    # ============================================================================
    
    def save_auth_flow(self, state: str, flow_data: Dict[str, Any]) -> bool:
        """Save temporary auth flow data"""
        try:
            # Don't persist auth flows to disk (they're temporary)
            # Keep them in memory only
            self._data['auth_flows'][state] = flow_data
            return True
        except Exception as e:
            logger.error(f"Failed to save auth flow for state {state}: {e}")
            return False
    
    def get_auth_flow(self, state: str) -> Optional[Dict[str, Any]]:
        """Retrieve temporary auth flow data"""
        return self._data['auth_flows'].get(state)
    
    def delete_auth_flow(self, state: str) -> bool:
        """Delete temporary auth flow data"""
        try:
            if state in self._data['auth_flows']:
                del self._data['auth_flows'][state]
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete auth flow for state {state}: {e}")
            return False

