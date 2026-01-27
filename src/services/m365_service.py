"""
M365 Service for managing Microsoft Graph webhooks and email draft generation.

This service handles:
1. OAuth2 authentication state management
2. Token refresh
3. Subscription lifecycle management
4. Email draft generation with LLM

The service is storage-agnostic and accepts a storage backend via dependency injection.
"""

import os
import time
import html
import webbrowser
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from services.m365_storage import M365StorageInterface
from services.tool_integration.outlook_connector import OutlookConnector
from services.email_service import EmailReplyGenerator, EmailClassifier
from response_models.email_response_models import EmailReplyRequest, EmailClassifierResponse
from response_models.chat_response_models import QuestionFiscalTopicYear
from logger.logger import Logger

from definitions.credentials import Credentials

logger = Logger.get_logger(__name__)

# FOR LOCAL TESTING ONLY
#from dotenv import load_dotenv
#load_dotenv()

# TODO: Refactor into smaller services
class M365Service:
    """Service for M365 integration and email automation"""
    
    def __init__(self, storage: M365StorageInterface):
        """
        Initialize M365 service
        
        Args:
            storage: Storage backend implementing M365StorageInterface
        """
        # Configuration
        self.client_id = Credentials.get_connector_microsoft_client_id() # os.getenv('CONNECTOR_MICROSOFT_CLIENT_ID', Credentials.get_connector_microsoft_client_id())
        self.client_secret = Credentials.get_connector_microsoft_client_secret() # os.getenv('CONNECTOR_MICROSOFT_CLIENT_SECRET', Credentials.get_connector_microsoft_client_secret())
        self.tenant_id = Credentials.get_connector_microsoft_tenant_id() # os.getenv('CONNECTOR_MICROSOFT_TENANT_ID', Credentials.get_connector_microsoft_tenant_id())
        self.redirect_uri = Credentials.get_connector_redirect_uri() # os.getenv('CONNECTOR_MICROSOFT_REDIRECT_URI', Credentials.get_connector_redirect_uri())
        self.webhook_url = Credentials.get_connector_webhook_url() # os.getenv('CONNECTOR_MICROSOFT_WEBHOOK_URL', Credentials.get_connector_webhook_url())
        self.client_state_secret = Credentials.get_connector_client_state_secret() # os.getenv('CONNECTOR_MICROSOFT_CLIENT_STATE_SECRET', Credentials.get_connector_client_state_secret())
        #logger.info(f"M365Service initialized with client_id: {self.client_id}, client_secret: {self.client_secret}, tenant_id: {self.tenant_id}, redirect_uri: {self.redirect_uri}, webhook_url: {self.webhook_url}, client_state_secret: {self.client_state_secret}")
        # Storage backend
        self.storage = storage
        
        # In-memory connector cache (not persisted)
        # Maps user_id -> OutlookConnector instance
        self._connector_cache: Dict[str, OutlookConnector] = {}
        
        # Lazy-loaded email reply generator
        self._reply_generator: Optional[EmailReplyGenerator] = None

        # Lazy-loaded email classifier
        self._email_classifier: Optional[EmailClassifier] = None
        
        # Initialize connectors from storage
        self._initialize_connectors()
    
    def _initialize_connectors(self):
        """Initialize connectors from stored tokens"""
        user_tokens = self.storage.list_user_tokens()
        for user_id, token_data in user_tokens.items():
            if token_data.get('access_token'):
                connector = self._create_connector()
                connector.access_token = token_data['access_token']
                self._connector_cache[user_id] = connector
    
    def get_reply_generator(self) -> EmailReplyGenerator:
        """Lazy load reply generator to speed up service initialization"""
        if self._reply_generator is None:
            logger.info("Initializing LLM reply generator...")
            self._reply_generator = EmailReplyGenerator()
        return self._reply_generator

    def get_email_classifier(self) -> EmailClassifier:
        """Lazy load email classifier to speed up service initialization"""
        if self._email_classifier is None:
            logger.info("Initializing email classifier...")
            self._email_classifier = EmailClassifier()
        return self._email_classifier
    
    def _create_connector(self) -> OutlookConnector:
        """Create a new OutlookConnector instance"""
        return OutlookConnector(
            client_id=self.client_id,
            client_secret=self.client_secret,
            tenant_id=self.tenant_id,
            redirect_uri=self.redirect_uri
        )
    
    def _get_connector(self, user_id: str) -> OutlookConnector:
        """Get or create connector for user"""
        if user_id not in self._connector_cache:
            connector = self._create_connector()
            # Load token from storage
            token_data = self.storage.get_user_token(user_id)
            if token_data and token_data.get('access_token'):
                connector.access_token = token_data['access_token']
            self._connector_cache[user_id] = connector
        return self._connector_cache[user_id]
    
    def initiate_auth_flow(self, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Initiate OAuth2 authentication flow
        
        Args:
            redirect_uri: Optional redirect URI to override the configured default
        """
        connector = self._create_connector()
        # Override connector redirect if provided
        if redirect_uri:
            connector.redirect_uri = redirect_uri
        flow = connector.initiate_auth_code_flow()
        
        state = flow.get('state')
        if state:
            # Store flow data temporarily (with connector serialized separately)
            flow_to_store = flow.copy()
            self.storage.save_auth_flow(state, {
                'flow': flow_to_store,
                # Note: connector is not serializable, will be recreated
            })
            # Keep connector in memory cache for this auth flow
            self._connector_cache[f"auth_{state}"] = connector
        
        # Open browser automatically
        # webbrowser.open_new(flow['auth_uri'])
        
        return {
            'auth_url': flow['auth_uri'],
            'state': state
        }
    
    def complete_auth(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete OAuth2 authentication
        
        Args:
            params: Query parameters from OAuth callback
            
        Returns:
            User data dictionary
        """
        state = params.get('state')
        
        # Get flow data from storage
        flow_data = self.storage.get_auth_flow(state)
        if not flow_data:
            raise ValueError(f"Invalid or expired state: {state}")
        
        flow = flow_data['flow']
        
        # Get or recreate connector
        connector_key = f"auth_{state}"
        if connector_key in self._connector_cache:
            connector = self._connector_cache[connector_key]
        else:
            connector = self._create_connector()
        
        # Authenticate
        auth_result = connector.authenticate_with_code(flow, params)
        
        # Get user profile
        user_profile = connector.get_user_profile()
        user_id = user_profile.get('id', state)
        
        # Store user tokens in storage backend
        self.storage.save_user_token(
            user_id=user_id,
            access_token=auth_result.get('access_token'),
            refresh_token=auth_result.get('refresh_token'),
            expires_in=auth_result.get('expires_in', 3600),
            expires_at=time.time() + auth_result.get('expires_in', 3600),
            token_type=auth_result.get('token_type', 'Bearer'),
            scope=auth_result.get('scope', ''),
            user_profile=user_profile
        )
        
        # Cache connector
        self._connector_cache[user_id] = connector
        
        # Clean up auth flow
        self.storage.delete_auth_flow(state)
        if connector_key in self._connector_cache:
            del self._connector_cache[connector_key]
        
        logger.info(f"User authenticated: {user_profile.get('displayName')} ({user_id})")
        
        return {
            'user_id': user_id,
            'name': user_profile.get('displayName'),
            'email': user_profile.get('mail') or user_profile.get('userPrincipalName')
        }
    
    def is_token_expired(self, user_id: str) -> bool:
        """Check if the access token is expired"""
        token_data = self.storage.get_user_token(user_id)
        if not token_data:
            return True
        
        if 'expires_at' not in token_data:
            return True
        
        expires_at = datetime.fromtimestamp(token_data['expires_at'])
        # Add 5 minute buffer
        return datetime.now() >= (expires_at - timedelta(minutes=5))
    
    def refresh_token(self, user_id: str) -> bool:
        """
        Refresh token if it's expired
        
        Args:
            user_id: User ID to refresh token for
            
        Returns:
            True if token is valid or successfully refreshed
        """
        token_data = self.storage.get_user_token(user_id)
        if not token_data:
            logger.error(f"User {user_id} not found in storage")
            return False
        
        if not self.is_token_expired(user_id):
            # Token is still valid, ensure connector has it
            connector = self._get_connector(user_id)
            if token_data.get('access_token'):
                connector.access_token = token_data['access_token']
            return True
        
        logger.info(f"Token expired for user {user_id}, refreshing...")
        
        try:
            connector = self._get_connector(user_id)
            refresh_result = connector.refresh_access_token(token_data['refresh_token'])
            
            # Update storage with new token info
            new_expires_at = time.time() + refresh_result.get('expires_in', 3600)
            
            self.storage.save_user_token(
                user_id=user_id,
                access_token=refresh_result['access_token'],
                refresh_token=refresh_result.get('refresh_token', token_data['refresh_token']),
                expires_in=refresh_result.get('expires_in', 3600),
                expires_at=new_expires_at,
                token_type=token_data.get('token_type', 'Bearer'),
                scope=token_data.get('scope', ''),
                user_profile=token_data.get('user_profile', {})
            )
            
            # Update connector's access token
            connector.access_token = refresh_result['access_token']
            
            logger.info(f"Token refreshed successfully for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh token for user {user_id}: {e}")
            return False
    
    def create_subscription(self, user_id: str, resource: str) -> Dict[str, Any]:
        """
        Create a subscription for email notifications
        
        Args:
            user_id: User ID to create subscription for
            resource: Resource to monitor
            
        Returns:
            Subscription data
        """
        token_data = self.storage.get_user_token(user_id)
        if not token_data:
            raise ValueError(f"User {user_id} not found. Please authenticate first.")
        
        # Refresh token if needed
        self.refresh_token(user_id)
        
        connector = self._get_connector(user_id)
        
        # Ensure connector has current token
        token_data = self.storage.get_user_token(user_id)
        connector.access_token = token_data['access_token']
        
        logger.info(f"Creating subscription for user {user_id}")
        logger.info(f"Webhook URL: {self.webhook_url}")
        logger.info(f"Resource: {resource}")
        
        # Create subscription
        subscription = connector.create_subscription(
            change_type=["created"],
            notification_url=self.webhook_url,
            resource=resource,
            expiration_minutes=4230,  # Max for emails (~3 days)
            client_state=self.client_state_secret
        )
        
        subscription_id = subscription.get('id')
        
        # Store subscription in storage backend
        self.storage.save_subscription(
            subscription_id=subscription_id,
            user_id=user_id,
            resource=resource,
            notification_url=self.webhook_url,
            expires_at=subscription.get('expirationDateTime')
        )
        
        logger.info(f"Subscription created for user {user_id}: {subscription_id}")
        
        return {
            'id': subscription_id,
            'user_id': user_id,
            'resource': resource,
            'expires_at': subscription.get('expirationDateTime'),
            'notification_url': self.webhook_url
        }
    
    def list_subscriptions(self) -> Dict[str, Dict[str, Any]]:
        """List all active subscriptions"""
        return self.storage.list_subscriptions()
    
    def delete_subscription(self, subscription_id: str) -> bool:
        """
        Delete a subscription
        
        Args:
            subscription_id: Subscription ID to delete
            
        Returns:
            True if successfully deleted
        """
        subscription_data = self.storage.get_subscription(subscription_id)
        if not subscription_data:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        user_id = subscription_data['user_id']
        
        token_data = self.storage.get_user_token(user_id)
        if not token_data:
            raise ValueError(f"User {user_id} not found")
        
        # Refresh token if needed
        self.refresh_token(user_id)
        
        connector = self._get_connector(user_id)
        
        # Delete subscription via API
        connector._make_request("DELETE", f"subscriptions/{subscription_id}")
        
        # Remove from storage
        self.storage.delete_subscription(subscription_id)
        
        logger.info(f"Subscription deleted: {subscription_id}")
        return True
    
    def get_emails(self, user_id: str, folder: str = "inbox", limit: int = 10) -> list:
        """
        Get emails for a user
        
        Args:
            user_id: User ID
            folder: Folder name
            limit: Number of emails to retrieve
            
        Returns:
            List of emails
        """
        token_data = self.storage.get_user_token(user_id)
        if not token_data:
            raise ValueError(f"User {user_id} not found")
        
        self.refresh_token(user_id)
        
        connector = self._get_connector(user_id)
        emails = connector.get_emails(folder=folder, limit=limit)
        
        formatted_emails = []
        for email in emails:
            formatted_emails.append({
                'id': email.get('id'),
                'subject': email.get('subject'),
                'from': email.get('from', {}).get('emailAddress', {}).get('address'),
                'from_name': email.get('from', {}).get('emailAddress', {}).get('name'),
                'received_datetime': email.get('receivedDateTime'),
                'is_read': email.get('isRead'),
                'body_preview': email.get('bodyPreview')
            })
        
        return formatted_emails
    
    def list_users(self) -> Dict[str, Dict[str, Any]]:
        """List all authenticated users"""
        return self.storage.list_user_tokens()
    
    def clear_all_users(self) -> int:
        """Clear all user tokens"""
        count = self.storage.clear_all_user_tokens()
        # Clear connector cache
        self._connector_cache.clear()
        return count
    
    def handle_webhook_notification(self, notification: Dict[str, Any]) -> Optional[str]:
        """
        Handle a webhook notification and create draft reply
        
        Args:
            notification: Webhook notification data
            
        Returns:
            Message ID if successfully processed
        """
        # Validate client state if present
        client_state = notification.get('clientState')
        if client_state and client_state != self.client_state_secret:
            logger.warning(f"Invalid client state in notification")
            return None
        
        # Extract notification details
        subscription_id = notification.get('subscriptionId')
        resource = notification.get('resource')
        change_type = notification.get('changeType')
        
        logger.info(f"New email notification - Change type: {change_type}")
        logger.info(f"Subscription: {subscription_id}")
        logger.info(f"Resource: {resource}")
        
        # Get subscription data from storage
        subscription_data = self.storage.get_subscription(subscription_id)
        if not subscription_data:
            logger.warning(f"Unknown subscription: {subscription_id}")
            return None
        
        # Extract message ID from resource
        # Resource format: "Users/{user_id}/Messages/{message_id}"
        message_id = resource.split('/')[-1]
        
        logger.info(f"Processing new email: {message_id}")
        
        return message_id

    async def process_email(self, email_data: Dict[str, Any], user_id: str):
        """Check if email should be replied to"""
        try:
            
            email_request, email_data = self._extract_email_request(email_data, user_id)
            if not email_request:
                logger.error(f"Email request not found")
                return None
            
            classification = self.get_email_classifier().classify_email(email_request)
            
            if classification.should_respond:
                logger.info(f"Email should be replied to")
                return self._generate_and_create_draft_reply(email_request, email_data, classification, user_id)
            else:
                logger.info(f"Email should not be replied to")
                return None

        except Exception as e:
            logger.error(f"Error processing email: {e}", exc_info=True)
            return None

    def _extract_email_request(self, email_data: Dict[str, Any], user_id: str) -> tuple[Optional[EmailReplyRequest], Optional[Dict]]:
        """Extract EmailReplyRequest from email data (shared by process_email and generate_and_create_draft_reply)"""
        token_data = self.storage.get_user_token(user_id)
        if not token_data:
            logger.error(f"User data not found for {user_id}")
            return None, None
        
        connector = self._get_connector(user_id)
        self.refresh_token(user_id)
        
        # Fetch full email details if we only have the ID
        if 'subject' not in email_data:
            message_id = email_data['id']
            logger.info(f"Fetching full email details for: {message_id}")
            email_data = connector._make_request("GET", f"me/messages/{message_id}")
        
        # Extract email information
        subject = email_data.get('subject', 'No Subject')
        body_html = email_data.get('body', {})
        body_text = self._extract_email_text(body_html)
        
        # Get sender information
        sender_info = email_data.get('sender', {}).get('emailAddress', {})
        sender_name = sender_info.get('name', '')
        sender_email = sender_info.get('address', '')
        
        # Get recipient (user) information
        recipient_name = token_data.get('user_profile', {}).get('givenName', '')
        
        logger.info(f"Processing email from: {sender_name or sender_email}")
        logger.info(f"Subject: {subject}")
        
        # Create request
        email_request = EmailReplyRequest(
            subject=subject,
            body=body_text,
            sender_name=sender_name,
            sender_email=sender_email,
            recipient_name=recipient_name
        )
        
        return email_request, email_data

    def _generate_and_create_draft_reply(self, email_request: EmailReplyRequest, email_data: Dict[str, Any], classification: EmailClassifierResponse, user_id: str):
        """Generate personalized reply and create draft"""
        try:            
            metadata = QuestionFiscalTopicYear(
                fiscal_topic=classification.fiscal_topic,
                year=classification.year,
                vector_query=classification.vector_query
            )
            
            # Generate reply using LLM (lazy load)
            reply_response = self.get_reply_generator().generate_reply(email_request, metadata)
            
            logger.info(f"Generated reply - Tone: {reply_response.tone}")
            
            # Convert markdown to HTML
            html_reply = self._convert_markdown_to_html(reply_response.answer)
            
            # Create draft reply
            connector = self._get_connector(user_id)
            draft = connector.draft_reply(
                message_id=email_data['id'],
                reply_body=html_reply,
                is_html=True
            )
            
            logger.info(f"Draft reply created successfully for email: {email_data['subject']}")
            return draft
            
        except Exception as e:
            logger.error(f"Error creating draft reply: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _extract_email_text(email_body: Dict[str, Any]) -> str:
        """Extract plain text from email body HTML"""
        if not email_body:
            return ""
        
        import re
        # Remove HTML tags
        clean_text = re.sub('<[^<]+?>', '', email_body.get('content', ''))
        # Decode HTML entities
        clean_text = html.unescape(clean_text)
        # Clean up whitespace
        clean_text = ' '.join(clean_text.split())
        
        return clean_text
    
    @staticmethod
    def _convert_markdown_to_html(text: str) -> str:
        """Convert markdown/plain text to HTML for email display"""
        import re
        
        # Escape any existing HTML
        text = html.escape(text)
        
        # URLs placeholders
        url_placeholder_map = {}
        url_counter = 0
        
        def store_url(match):
            nonlocal url_counter
            placeholder = f"\x00URLPLACEHOLDER{url_counter}\x00"
            url_placeholder_map[placeholder] = match.group(0)
            url_counter += 1
            return placeholder
        
        # Store markdown links [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', store_url, text)
        
        # Apply bold/italic formatting to non-URL text
        # Convert markdown bold (**text** or __text__) to HTML
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
        
        # Convert markdown italic (*text* or _text_) to HTML
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
        text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<em>\1</em>', text)
        
        # Restore URLs and convert to HTML links
        for placeholder, original_link in url_placeholder_map.items():
            # Parse the original [text](url) format
            match = re.match(r'\[([^\]]+)\]\(([^\)]+)\)', original_link)
            if match:
                link_text, url = match.groups()
                html_link = f'<a href="{url}" style="color: #0563C1; text-decoration: underline;">{link_text}</a>'
                text = text.replace(placeholder, html_link)
        
        # Convert bullet points (- item) to HTML list
        lines = text.split('\n')
        html_lines = []
        in_list = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('- '):
                if not in_list:
                    html_lines.append('<ul style="margin-top: 8px; margin-bottom: 8px;">')
                    in_list = True
                html_lines.append(f'<li style="margin-bottom: 4px;">{line[2:].strip()}</li>')
            else:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append(f'<p style="margin-top: 0; margin-bottom: 8px;">{line}</p>')
        
        if in_list:
            html_lines.append('</ul>')
        
        # Convert horizontal rules (---)
        html_text = '\n'.join(html_lines)
        html_text = re.sub(r'<p[^>]*>-{3,}</p>', '<hr style="margin: 12px 0; border: none; border-top: 1px solid #ccc;">', html_text)
        
        # Wrap in a div with proper styling
        html_output = f'''<div style="font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #000000; line-height: 1.4;">
{html_text}
</div>'''
        
        return html_output
