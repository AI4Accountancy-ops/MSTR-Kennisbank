"""
M365 Connector API endpoints for Microsoft Graph webhooks and email automation.

This module provides:
1. OAuth2 authentication with Microsoft Graph
2. Webhook subscription management
3. Automated email draft generation using LLM
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse, Response, RedirectResponse

from request_models.m365 import (
    CreateSubscriptionRequest,
    DeleteSubscriptionRequest,
    RefreshTokenRequest,
    GetEmailsRequest,
    AuthenticateRequest
)
from services.m365_service import M365Service
from services.m365_storage_json import M365JsonStorage
from logger.logger import Logger


logger = Logger.get_logger(__name__)
router = APIRouter(prefix="/m365", tags=["m365"])

storage = M365JsonStorage() # <- TODO: replace with Postgres storage
m365_service = M365Service(storage=storage)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "m365-connector",
        "active_users": len(m365_service.list_users()),
        "active_subscriptions": len(m365_service.list_subscriptions())
    }

# M365 Authentication Endpoints

@router.post("/auth/authenticate")
async def get_auth_url(request: AuthenticateRequest) -> Dict[str, Any]:
    """Initiate OAuth2 authentication flow"""
    try:
        result = m365_service.initiate_auth_flow(redirect_uri=request.redirect_uri)

        # Return JSON with the authorization URL so frontend can navigate
        return {
            'status': 'success',
            'auth_url': result.get('auth_url'),
            'message': 'Please complete authentication in the opened browser tab',
            'state': result.get('state', '')
        }

    except Exception as e:
        logger.error(f"Failed to initiate auth flow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate auth flow: {str(e)}")


@router.get("/auth/callback")
async def callback(request: Request) -> Dict[str, Any]:
    """Handle OAuth2 callback from /auth/authenticate

    TODO: Must match redirect URI configured in Azure Portal.
    """
    try:
        # Get callback parameters
        params = dict(request.query_params)
        auth_code = params.get('code')
        state = params.get('state')
        error = params.get('error')
        error_description = params.get('error_description')
        
        # Error handling
        if error:
            raise HTTPException(
                status_code=400,
                detail=f"Authentication error: {error} - {error_description}"
            )
        
        if not auth_code or not state:
            raise HTTPException(
                status_code=400,
                detail="Missing authorization code or state parameter"
            )
        
        # Complete authentication
        user_data = m365_service.complete_auth(params)
        
        logger.info(f"User authenticated: {user_data['name']} ({user_data['user_id']})")
        
        return {
            'status': 'success',
            'message': 'Authentication successful!',
            'user': user_data,
            'next_steps': 'Create a subscription using POST /api/m365/mail/subscriptions'
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Authentication failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/auth/refresh-token")
async def refresh_token(request: RefreshTokenRequest) -> Dict[str, Any]:
    """Refresh access token for a user"""
    try:
        success = m365_service.refresh_token(request.user_id)
        
        if success:
            user_data = m365_service.storage.get_user_token(request.user_id) or {}
            return {
                'status': 'success',
                'message': 'Token refreshed successfully',
                'user_id': request.user_id,
                'expires_in': user_data.get('expires_in')
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to refresh token")
            
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing token: {str(e)}")


@router.post("/mail/subscriptions")
def create_subscription(request: CreateSubscriptionRequest) -> Dict[str, Any]:
    """Create a subscription for email notifications"""
    try:
        subscription = m365_service.create_subscription(
            user_id=request.user_id,
            resource=request.resource
        )
        
        return {
            'status': 'success',
            'message': 'Subscription created successfully',
            'subscription': subscription
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Subscription creation failed: {e}", exc_info=True)
        
        # Show detailed error information for debugging
        error_detail = str(e)
        if hasattr(e, 'response'):
            try:
                response = e.response
                logger.error(f"Request URL: {response.request.url}")
                logger.error(f"Request Method: {response.request.method}")
                logger.error(f"Response Status: {response.status_code} {response.reason}")
                
                try:
                    error_json = response.json()
                    error_code = error_json.get('error', {}).get('code')
                    error_msg = error_json.get('error', {}).get('message')
                    error_detail = f"{error_code}: {error_msg}"
                    logger.error(f"Error Code: {error_code}")
                    logger.error(f"Error Message: {error_msg}")
                except Exception:
                    error_detail = response.text
                    logger.error(f"Response Text: {response.text}")
                
            except Exception as parse_error:
                logger.error(f"Could not extract response details: {parse_error}")
        
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {error_detail}")


@router.get("/mail/subscriptions")
async def list_subscriptions() -> Dict[str, Any]:
    """List all active subscriptions"""
    subscriptions = m365_service.list_subscriptions()
    return {
        'status': 'success',
        'count': len(subscriptions),
        'subscriptions': list(subscriptions.values())
    }


@router.delete("/mail/subscriptions/{subscription_id}")
async def delete_subscription(subscription_id: str) -> Dict[str, Any]:
    """Delete a subscription"""
    try:
        m365_service.delete_subscription(subscription_id)
        
        return {
            'status': 'success',
            'message': f'Subscription {subscription_id} deleted successfully'
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete subscription: {str(e)}")


@router.api_route("/mail/webhook", methods=["GET", "POST"])
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    validationToken: Optional[str] = Query(None)
) -> Response:
    """
    Webhook endpoint for Microsoft Graph notifications.
    
    This endpoint:
    1. Handles validation requests from Microsoft Graph (GET or POST with validationToken)
    2. Receives notifications about new emails (POST)
    3. Triggers draft reply generation in background
    """
    
    # Log timing information
    import time
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    # CRITICAL: Respond to validation immediately (must be < 10 seconds)
    if validationToken is not None:
        response_time = (time.time() - start_time) * 1000
        host = request.headers.get("host")
        user_agent = request.headers.get("user-agent", "")
        
        logger.info(f"VALIDATION REQUEST RECEIVED")
        logger.info(f"Time to process: {response_time:.2f}ms")
        logger.info(f"From host: {host}")
        logger.info(f"User-Agent: {user_agent}")
        logger.info(f"Client IP: {client_ip}")
        logger.info(f"Token (first 50): {validationToken[:50]}...")
        logger.info(f"Echoing token immediately...")
        
        return Response(content=validationToken, media_type="text/plain", status_code=200)
    
    # Handle notification
    try:
        body = await request.json()
        
        logger.info(f"Webhook notification received")
        
        # Extract notifications
        notifications = body.get('value', [])
        
        for notification in notifications:
            message_id = m365_service.handle_webhook_notification(notification)
            
            if message_id:
                subscription_id = notification.get('subscriptionId')
                subscription_data = m365_service.storage.get_subscription(subscription_id)
                
                if subscription_data:
                    user_id = subscription_data['user_id']
            
                    # Process in background to return 202 quickly
                    background_tasks.add_task(
                        m365_service.process_email,
                {'id': message_id},  # Only pass ID, fetch details in background
                user_id
            )
        
        # Return 202 Accepted immediately (< 3 seconds recommended)
        return JSONResponse(
            status_code=202,
            content={'status': 'accepted', 'message': 'Notification received and processing'}
        )
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        # Return 200 to prevent Microsoft from disabling the subscription
        return JSONResponse(
            status_code=200,
            content={'status': 'error', 'message': str(e)}
        )


@router.get("/auth/users")
async def list_users() -> Dict[str, Any]:
    """List all authenticated users"""
    from datetime import datetime
    
    users_info = []
    all_users = m365_service.list_users()
    for user_id, token_data in all_users.items():
        users_info.append({
            'user_id': user_id,
            'name': token_data.get('user_profile', {}).get('displayName'),
            'email': token_data.get('user_profile', {}).get('mail'),
            'has_token': bool(token_data.get('access_token')),
            'token_expires_at': datetime.fromtimestamp(token_data.get('expires_at', 0)).isoformat() if token_data.get('expires_at') else None
        })
    
    return {
        'status': 'success',
        'count': len(users_info),
        'users': users_info
    }


@router.post("/auth/users/clear")
async def clear_users() -> Dict[str, Any]:
    """Clear all user tokens (for testing)"""
    count = m365_service.clear_all_users()
    
    return {
        'status': 'success',
        'message': f'Cleared {count} user tokens'
    }


@router.post("/mail/emails")
async def get_emails(request: GetEmailsRequest) -> Dict[str, Any]:
    """Get emails for a user (for testing)"""
    try:
        emails = m365_service.get_emails(
            user_id=request.user_id,
            folder=request.folder,
            limit=request.limit
        )
        
        return {
            'status': 'success',
            'count': len(emails),
            'emails': emails
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get emails: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get emails: {str(e)}")
