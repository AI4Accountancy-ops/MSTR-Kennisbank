"""
Storage abstraction layer for M365 service.

This module provides an abstract interface for storing M365 authentication tokens,
user data, and subscription information. This allows the M365 service to be 
database/storage agnostic.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class M365StorageInterface(ABC):
    """Abstract interface for M365 storage operations"""
    
    # ============================================================================
    # USER TOKEN OPERATIONS
    # ============================================================================
    
    @abstractmethod
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
        """
        Save or update user token data
        
        Args:
            user_id: Unique user identifier
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_in: Token expiration duration in seconds
            expires_at: Timestamp when token expires
            token_type: Token type (usually "Bearer")
            scope: OAuth scopes granted
            user_profile: User profile information from Microsoft Graph
            
        Returns:
            True if successfully saved
        """
        pass
    
    @abstractmethod
    def get_user_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user token data
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Dictionary with token data or None if not found
        """
        pass
    
    @abstractmethod
    def list_user_tokens(self) -> Dict[str, Dict[str, Any]]:
        """
        List all stored user tokens
        
        Returns:
            Dictionary mapping user_id to token data
        """
        pass
    
    @abstractmethod
    def delete_user_token(self, user_id: str) -> bool:
        """
        Delete user token data
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            True if successfully deleted
        """
        pass
    
    @abstractmethod
    def clear_all_user_tokens(self) -> int:
        """
        Clear all user tokens
        
        Returns:
            Number of tokens cleared
        """
        pass
    
    # ============================================================================
    # SUBSCRIPTION OPERATIONS
    # ============================================================================
    
    @abstractmethod
    def save_subscription(
        self,
        subscription_id: str,
        user_id: str,
        resource: str,
        notification_url: str,
        expires_at: str,
        created_at: Optional[str] = None
    ) -> bool:
        """
        Save or update subscription data
        
        Args:
            subscription_id: Microsoft Graph subscription ID
            user_id: User who owns this subscription
            resource: Resource being monitored
            notification_url: Webhook URL for notifications
            expires_at: Subscription expiration datetime (ISO format)
            created_at: Creation datetime (ISO format)
            
        Returns:
            True if successfully saved
        """
        pass
    
    @abstractmethod
    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve subscription data
        
        Args:
            subscription_id: Microsoft Graph subscription ID
            
        Returns:
            Dictionary with subscription data or None if not found
        """
        pass
    
    @abstractmethod
    def list_subscriptions(self) -> Dict[str, Dict[str, Any]]:
        """
        List all active subscriptions
        
        Returns:
            Dictionary mapping subscription_id to subscription data
        """
        pass
    
    @abstractmethod
    def delete_subscription(self, subscription_id: str) -> bool:
        """
        Delete subscription data
        
        Args:
            subscription_id: Microsoft Graph subscription ID
            
        Returns:
            True if successfully deleted
        """
        pass
    
    # ============================================================================
    # AUTH FLOW OPERATIONS (temporary storage during OAuth flow)
    # ============================================================================
    
    @abstractmethod
    def save_auth_flow(self, state: str, flow_data: Dict[str, Any]) -> bool:
        """
        Save temporary auth flow data (only needed during OAuth flow)
        
        Args:
            state: OAuth state parameter
            flow_data: Flow data to store temporarily
            
        Returns:
            True if successfully saved
        """
        pass
    
    @abstractmethod
    def get_auth_flow(self, state: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve temporary auth flow data
        
        Args:
            state: OAuth state parameter
            
        Returns:
            Flow data or None if not found
        """
        pass
    
    @abstractmethod
    def delete_auth_flow(self, state: str) -> bool:
        """
        Delete temporary auth flow data
        
        Args:
            state: OAuth state parameter
            
        Returns:
            True if successfully deleted
        """
        pass

