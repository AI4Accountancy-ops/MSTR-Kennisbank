"""
Microsoft Outlook Connector using Microsoft Graph API

A focused tool for connecting to Microsoft Outlook via Microsoft Graph API.
Supports reading emails and creating drafts.
"""

import os
import logging
import html
import json
from typing import Dict, List, Any
import requests
import msal

from definitions.credentials import Credentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OutlookConnector:
    """
    Microsoft Outlook connector using Microsoft Graph API.
    
    Supports:
    - Reading emails from folders
    - Searching emails
    - Creating email drafts
    - Authentication via OAuth2/MSAL
    """
    
    def __init__(self, 
                 client_id: str = None,
                 client_secret: str = None, 
                 tenant_id: str = None,
                 redirect_uri: str = "http://localhost:8000/api/m365/auth/callback"):
        """
        Initialize the Outlook connector.
        
        Args:
            client_id: Azure AD application client ID
            client_secret: Azure AD application client secret
            tenant_id: Azure AD tenant ID
            redirect_uri: OAuth2 redirect URI (must match app registration)
        """
        self.client_id = client_id or Credentials.get_connector_microsoft_client_id()
        self.client_secret = client_secret or Credentials.get_connector_microsoft_client_secret()
        self.tenant_id = tenant_id or Credentials.get_connector_microsoft_tenant_id()
        self.redirect_uri = redirect_uri or Credentials.get_connector_redirect_uri()
        
        # Microsoft Graph API endpoints
        self.graph_url = "https://graph.microsoft.com/v1.0"
        self.authority = f"https://login.microsoftonline.com/common" # supports organization and personal accounts
        
        # Required scopes for email operations
        self.scopes = [
            "https://graph.microsoft.com/Mail.ReadWrite",
            "https://graph.microsoft.com/User.Read"
        ]
        
        self.access_token = None
        self.app = None
        self._initialize_msal_app()
    
    def _initialize_msal_app(self):
        """Initialize MSAL application for authentication."""
        try:
            # Confidential Client Application for web apps/APIs
            self.app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=self.authority
            )
            logger.info("MSAL application initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MSAL app: {e}")
            raise
    
    def initiate_auth_code_flow(self) -> Dict[str, Any]:
        """
        Initiate the authorization flow.
        
        Returns:
            Dict[str, Any]: 
        """
        try:
            # Auth code flow for interactive login
            flow = self.app.initiate_auth_code_flow(
                scopes=self.scopes,
                redirect_uri=self.redirect_uri,
                state=None
            )
            logger.info("Authorization flow initiated")
            return flow
        except Exception as e:
            logger.error(f"Failed to initiate authorization flow: {e}")
            raise
    
    def authenticate_with_code(self, flow: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Authenticate using authorization code from OAuth2 flow.
        
        Args:
            flow: Authorization flow from redirect
            params: Parameters from redirect
        Returns:
            dict: Authentication result containing access token
        """
        try:
            # Acquire access token for authorization code flow
            result = self.app.acquire_token_by_auth_code_flow(
                auth_code_flow=flow,
                auth_response=params
            )
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                logger.info("Successfully authenticated with authorization code")
                return result
            else:
                logger.error(f"Authentication failed: {result.get('error_description', 'Unknown error')}")
                raise Exception(f"Authentication failed: {result.get('error_description')}")
                
        except Exception as e:
            logger.error(f"Failed to authenticate with code: {e}")
            raise
    
    def authenticate_with_client_credentials(self) -> Dict[str, Any]:
        """
        Authenticate using client credentials flow (app-only access).
        
        Returns:
            dict: Authentication result containing access token
        """
        try:
            # Acquire access token for client credentials flow
            result = self.app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                logger.info("Successfully authenticated with client credentials")
                return result
            else:
                logger.error(f"Authentication failed: {result.get('error_description', 'Unknown error')}")
                raise Exception(f"Authentication failed: {result.get('error_description')}")
                
        except Exception as e:
            logger.error(f"Failed to authenticate with client credentials: {e}")
            raise
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: The refresh token to use
            
        Returns:
            dict: New authentication result containing access token
        """
        try:
            # Acquire new access token using refresh token
            result = self.app.acquire_token_by_refresh_token(
                refresh_token=refresh_token,
                scopes=self.scopes
            )
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                logger.info("Successfully refreshed access token")
                return result
            else:
                logger.error(f"Token refresh failed: {result.get('error_description', 'Unknown error')}")
                raise Exception(f"Token refresh failed: {result.get('error_description')}")
                
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authorization token."""
        if not self.access_token:
            raise Exception("Not authenticated. Please authenticate first.")
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """
        Make authenticated request to Microsoft Graph API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: Query parameters
            
        Returns:
            dict: API response
        """
        url = f"{self.graph_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            )
            
            if response.status_code in [200, 201, 202, 204]:
                return response.json() if response.content else {}
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    # CHANGE NOTIFICATION SUBSCRIPTION

    def create_subscription(self,
                          change_type: List[str],
                          notification_url: str,
                          resource: str,
                          expiration_minutes: int = 4230,
                          client_state: str = None) -> Dict[str, Any]:
        """
        Create a subscription for change notifications.
        
        Args:
            change_type: List of change types to monitor (e.g., ["created", "updated", "deleted"])
            notification_url: HTTPS URL where notifications will be sent
            resource: Resource path to monitor (e.g., "me/mailFolders('Inbox')/messages")
            expiration_minutes: Subscription expiration time in minutes (max 4230 for emails)
            client_state: Optional secret value for validating notifications
            
        Returns:
            dict: Subscription details including subscription ID
        """
        try:
            from datetime import datetime, timedelta
            
            # Calculate expiration time
            expiration_time = datetime.utcnow() + timedelta(minutes=expiration_minutes)
            expiration_str = expiration_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            
            # Prepare subscription payload
            subscription_data = {
                "changeType": ",".join(change_type),
                "notificationUrl": notification_url,
                "resource": resource,
                "expirationDateTime": expiration_str
            }
            
            # Add client state if provided
            if client_state:
                subscription_data["clientState"] = client_state
            
            # Create subscription
            result = self._make_request("POST", "subscriptions", subscription_data)
            logger.info(f"Subscription created successfully with ID: {result.get('id')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            raise

    # EMAIL OPERATIONS
    
    def get_emails(self, 
                   folder: str = "inbox",
                   limit: int = 10,
                   filter_query: str = None,
                   select_fields: List[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve emails from a folder.
        
        Args:
            folder: Folder name (inbox, sent, drafts, etc.)
            limit: Maximum number of emails to retrieve
            filter_query: OData filter query
            select_fields: List of fields to select
            
        Returns:
            list: List of email messages
        """
        try:
            params = {"$top": limit}
            
            if filter_query:
                params["$filter"] = filter_query
            
            if select_fields:
                params["$select"] = ",".join(select_fields)
            
            result = self._make_request("GET", f"me/mailFolders/{folder}/messages", params=params)
            logger.info(f"Retrieved {len(result.get('value', []))} emails from {folder}")
            return result.get("value", [])
            
        except Exception as e:
            logger.error(f"Failed to get emails: {e}")
            raise
    
    def create_draft(self, 
                     to_recipients: List[str] = None,
                     subject: str = "",
                     body: str = "",
                     cc_recipients: List[str] = None,
                     bcc_recipients: List[str] = None,
                     attachments: List[Dict] = None,
                     is_html: bool = True) -> Dict[str, Any]:
        """
        Create an email draft.
        
        Args:
            to_recipients: List of recipient email addresses
            subject: Email subject
            body: Email body content
            cc_recipients: List of CC recipient email addresses
            bcc_recipients: List of BCC recipient email addresses
            attachments: List of attachment dictionaries
            is_html: Whether body content is HTML
            
        Returns:
            dict: Created draft details
        """
        try:
            # Prepare email message
            message = {
                "subject": subject,
                "body": {
                    "contentType": "HTML" if is_html else "Text",
                    "content": body
                }
            }
            
            # Add recipients if provided
            if to_recipients:
                message["toRecipients"] = [{"emailAddress": {"address": email}} for email in to_recipients]
            
            if cc_recipients:
                message["ccRecipients"] = [{"emailAddress": {"address": email}} for email in cc_recipients]
            
            if bcc_recipients:
                message["bccRecipients"] = [{"emailAddress": {"address": email}} for email in bcc_recipients]
            
            # Add attachments if provided
            if attachments:
                message["attachments"] = attachments
            
            # Create draft
            result = self._make_request("POST", "me/messages", message)
            logger.info(f"Email draft created successfully with ID: {result.get('id')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create email draft: {e}")
            raise

    def draft_reply(self, message_id: str, reply_body: str = None, is_html: bool = True) -> Dict[str, Any]:
        """
        Create a reply draft for an email message.
        
        Args:
            message_id: ID of the message to reply to
            reply_body: Optional reply body content (can be HTML or plain text)
            is_html: If True, reply_body is treated as HTML; if False, it will be escaped

        Returns:
            dict: Reply draft details
        """
        try:

            # create the draft first
            result = self._make_request("POST", f"me/messages/{message_id}/createReply")
            
            # update the draft with the reply content
            if reply_body and result.get('id'):
                draft_id = result['id']
            
                draft_data = self._make_request("GET", f"me/messages/{draft_id}")
                original_content = draft_data.get('body', {}).get('content', '')
                
                # Only escape HTML if content is plain text, not if it's already HTML
                if is_html:
                    reply_content = reply_body
                else:
                    reply_content = html.escape(reply_body)
                
                updated_content = f"<div style='margin-bottom: 20px;'>{reply_content}</div><br><br>{original_content}"
                updated_body = {
                    "body": {
                        "contentType": "HTML",
                        "content": updated_content
                    }
                }
                
                updated_result = self._make_request("PATCH", f"me/messages/{draft_id}", updated_body)
                logger.info(f"Email reply draft created and updated successfully with ID: {draft_id}")
                return updated_result
            else:
                logger.info(f"Email reply draft created successfully with ID: {result.get('id')}")
                return result
            
        except Exception as e:
            logger.error(f"Failed to create reply draft: {e}")
            raise

    # UTILITY
    
    def get_user_profile(self) -> Dict[str, Any]:
        """
        Get current user's profile information.
        
        Returns:
            dict: User profile data
        """
        try:
            result = self._make_request("GET", "me")
            logger.info("Retrieved user profile successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            raise
