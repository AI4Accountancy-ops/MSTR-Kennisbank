import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from definitions.credentials import Credentials
from request_models.chat_request import ChatRequest
from request_models.auth import LoginRequest
from request_models.feedback import FeedbackRequest, MessageFeedbackRequest
from services.save_feedback import SaveFeedback
from services.chat_bot import ChatBot
from request_models.chat_history import (
    SaveChatHistoryRequest, 
    GetChatHistoryRequest, 
    GetChatByIdRequest,
    UpdateChatTitleRequest,
)
from services.save_history import SaveHistory
from services.auth_service import UserService
from services.organization_service import OrganizationService
from logger.logger import Logger
from typing import List, Optional
from pydantic import BaseModel
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import stripe

logger = Logger.get_logger(__name__)

router = APIRouter()
chat_bot_instance = ChatBot()
save_feedback = SaveFeedback()
save_history = SaveHistory()
user_service = UserService()


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint to handle text-based chat requests.
    Accepts a JSON body with a user_message (and optional chat_history).
    Streams back the chatbot's response as plain text with chunks data.
    
    If the user is not subscribed, it will return a message asking them to update their subscription.
    """
    request_id = str(uuid.uuid4())[:8]  # Generate a short unique ID for this request
    logger.info(f"[{request_id}] Chat request started for user_id: {request.user_id}")
    
    try:
        def response_generator():
            for chunk in chat_bot_instance.get_chatbot_response(
                user_message=request.user_message,
                tone_of_voice=request.tone_of_voice,
                chat_history=request.chat_history,
                user_id=request.user_id,
                web_search=getattr(request, "web_search", False)
            ):
                # Pass through chunks without modification
                yield chunk
        
        logger.info(f"[{request_id}] Chat response streaming started for user_id: {request.user_id}")
        return StreamingResponse(response_generator(), media_type="text/plain")
    except Exception as e:
        logger.error(f"[{request_id}] Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class FaviconsRequest(BaseModel):
    urls: List[str]


@router.post("/favicons")
def get_favicons(request: FaviconsRequest) -> Dict[str, Any]:
    """
    Given a list of page URLs, attempt to extract a representative favicon for each.
    We parse the HTML using BeautifulSoup and look for <link rel="icon"|"shortcut icon"|"apple-touch-icon">.
    If none are found, we fall back to "/favicon.ico" at the site root.

    Returns: { "favicons": { original_url: favicon_url_or_null } }
    """
    results: Dict[str, Optional[str]] = {}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
    }

    for url in request.urls:
        favicon_url: Optional[str] = None
        try:
            resp = requests.get(url, headers=headers, timeout=6)
            # Use final URL after redirects as base
            parsed = urlparse(resp.url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            soup = BeautifulSoup(resp.text, "html.parser")
            rel_candidates = {"icon", "shortcut icon", "apple-touch-icon", "apple-touch-icon-precomposed"}

            for link in soup.find_all("link"):
                rel = link.get("rel")
                if not rel:
                    continue
                # Normalize rel as string
                rel_str = " ".join(rel).lower() if isinstance(rel, list) else str(rel).lower()
                if any(candidate in rel_str for candidate in rel_candidates):
                    href = link.get("href")
                    if href:
                        favicon_url = urljoin(base_url, href)
                        break

            # Fallback to /favicon.ico
            if not favicon_url:
                favicon_url = urljoin(base_url, "/favicon.ico")

            results[url] = favicon_url
        except Exception as ex:
            logger.warning(f"Failed to extract favicon for {url}: {ex}")
            results[url] = None

    return {"favicons": results}

@router.post("/save_feedback")
def create_feedback(request: FeedbackRequest) -> Dict[str, Any]:
    """
    Receives feedback data from the React frontend, transforms it,
    and saves it in Cosmos DB.
    """
    try:
        # Filter out is_initial messages if you don't want them:
        filtered_history = [msg for msg in request.chat_history if not msg.is_initial]
        
        # Clean up chunks data in each message
        for msg in filtered_history:
            if msg.chunks is not None:
                # Ensure chunks are properly formatted
                sanitized_chunks = []
                for chunk in msg.chunks:
                    # Skip empty chunks
                    if not chunk or (isinstance(chunk, dict) and not chunk.get('content') and not chunk.get('id') and not chunk.get('source_url')):
                        continue
                    
                    # Transform chunk data if needed
                    if isinstance(chunk, dict):
                        # Normalize source field (string[] or null expected)
                        if 'source' in chunk:
                            if chunk['source'] is None:
                                chunk['source'] = []
                            elif isinstance(chunk['source'], str):
                                chunk['source'] = [chunk['source']]
                            elif not isinstance(chunk['source'], list):
                                chunk['source'] = []
                        
                        # Normalize year field (number or null expected)
                        if 'year' in chunk:
                            if chunk['year'] is None:
                                pass  # Keep as null
                            elif isinstance(chunk['year'], list) and chunk['year']:
                                chunk['year'] = chunk['year'][0]  # Take first element
                            elif isinstance(chunk['year'], list) and not chunk['year']:
                                chunk['year'] = None
                            elif not isinstance(chunk['year'], (int, float)):
                                try:
                                    chunk['year'] = int(chunk['year'])
                                except (ValueError, TypeError):
                                    chunk['year'] = None
                    
                    # If it's already a ChunkModel, keep it
                    if hasattr(chunk, 'model_dump'):
                        sanitized_chunks.append(chunk)
                    # If it's a dict, convert to ChunkModel if possible
                    elif isinstance(chunk, dict):
                        try:
                            from request_models.feedback import ChunkModel
                            sanitized_chunks.append(ChunkModel(**chunk))
                        except Exception as e:
                            logger.warning(f"Failed to convert chunk to ChunkModel: {e}")
                            # Skip invalid chunks
                            continue
                    else:
                        # Skip any chunks that don't fit our expected formats
                        logger.warning(f"Skipping chunk with unexpected format: {type(chunk)}")
                        continue
                        
                msg.chunks = sanitized_chunks

        # Pair user+assistant messages, which returns a list of dicts
        pairs = save_feedback.pair_user_assistant_messages(filtered_history)

        # Build the actual feedback item
        feedback_id = str(uuid.uuid4())
        feedback_item = {
            "id": feedback_id,
            "partitionKey": feedback_id,
            "metadata": {
                "category": request.category,
                "timestamp": datetime.now().isoformat(),
            },
            "feedback_text": request.feedback_text,
            "chat_interactions": pairs
        }

        # Persist the feedback to Cosmos
        saved = save_feedback.save_feedback(feedback_item)
        if not saved:
            # If something went wrong while saving
            raise HTTPException(status_code=500, detail="Failed to save feedback")

        return {"status": "success", "feedback_id": feedback_id}
    except Exception as e:
        logger.error(f"Error in save_feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process feedback: {str(e)}")


@router.post("/message_feedback")
def message_feedback(request: MessageFeedbackRequest) -> Dict[str, Any]:
    """
    Receives message feedback for a specific chat message pair.
    The feedback is saved in Cosmos DB with metadata indicating it's a message_feedback type.
    """
    try:
        # Convert the request model to a dictionary
        message_dict = request.chat_message.model_dump() if hasattr(request.chat_message, "model_dump") else request.chat_message.dict()
        
        # Sanitize chunks if present
        if "chunks" in message_dict and message_dict["chunks"]:
            sanitized_chunks = []
            for chunk in message_dict["chunks"]:
                # Skip empty chunks
                if not chunk:
                    logger.warning("Skipping empty chunk")
                    continue
                
                # Transform data types if needed
                if isinstance(chunk, dict):
                    # Normalize source field (string[] or null expected)
                    if 'source' in chunk:
                        if chunk['source'] is None:
                            chunk['source'] = []
                        elif isinstance(chunk['source'], str):
                            chunk['source'] = [chunk['source']]
                        elif not isinstance(chunk['source'], list):
                            chunk['source'] = []
                    
                    # Normalize year field (number or null expected)
                    if 'year' in chunk:
                        if chunk['year'] is None:
                            pass  # Keep as null
                        elif isinstance(chunk['year'], list) and chunk['year']:
                            chunk['year'] = chunk['year'][0]  # Take first element
                        elif isinstance(chunk['year'], list) and not chunk['year']:
                            chunk['year'] = None
                        elif not isinstance(chunk['year'], (int, float)):
                            try:
                                chunk['year'] = int(chunk['year'])
                            except (ValueError, TypeError):
                                chunk['year'] = None
                
                try:
                    # If chunk is a Pydantic model, convert to dict
                    if hasattr(chunk, "model_dump"):
                        sanitized_chunks.append(chunk.model_dump())
                    elif hasattr(chunk, "dict"):
                        sanitized_chunks.append(chunk.dict())
                    elif isinstance(chunk, dict):
                        # Only keep if it has at least one required field
                        if not ("id" in chunk or "content" in chunk or "source_url" in chunk):
                            logger.warning(f"Skipping chunk with missing required fields: {chunk}")
                            continue
                        sanitized_chunks.append(chunk)
                    else:
                        logger.warning(f"Skipping chunk with unexpected type: {type(chunk)}")
                        continue
                except Exception as e:
                    logger.warning(f"Error processing chunk: {e}")
                    continue
                    
            message_dict["chunks"] = sanitized_chunks
        
        # Create a transformed structure that matches what the service expects
        feedback_data = {
            "user_id": request.user_id,
            "chat_message": message_dict,
            "feedback_type": request.feedback_type,
        }

        saved = save_feedback.message_feedback(feedback_data)
        if not saved:
            raise HTTPException(status_code=500, detail="Failed to save like/dislike feedback")

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error in message_feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process message feedback: {str(e)}")


@router.post("/save_chat_history")
def save_chat_history(request: SaveChatHistoryRequest) -> Dict[str, Any]:
    """
    Saves (or updates) a chat history session in Cosmos DB.
    If request.chat_id is provided and the document exists,
    we update that document by appending messages.
    Otherwise, we create a new document.
    """
    # Access check using fast DB-only method
    if request.user_id:
        if not user_service.has_access_fast(request.user_id):
            logger.warning(f"User {request.user_id} is not subscribed or doesn't exist, not saving chat history")
            return {"status": "error", "message": "User not subscribed"}
    
    # Generate title if not provided
    title = request.chat_title
    if not title and request.chat_history:
        for msg in request.chat_history:
            if msg.role == "user":
                title = msg.message[:30]
                break
        if not title:
            title = "Nieuwe Chat"

    # The difference here is we now pass `request.chat_id` if given
    result_chat_id = save_history.save_chat_history(
        user_id=request.user_id,
        chat_title=title,
        chat_history=request.chat_history,
        chat_id=request.chat_id
    )

    if not result_chat_id:
        raise HTTPException(status_code=500, detail="Failed to save or update chat history")

    return {"status": "success", "chat_id": result_chat_id}


@router.post("/get_chat_history")
def get_chat_history(request: GetChatHistoryRequest) -> Dict[str, Any]:
    """
    Retrieves all chat history for a specific user.
    """
    chat_history = save_history.get_user_chat_history(request.user_id)
    
    # Process for frontend display - group by date categories
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)
    
    categorized_history = {
        "today": [],
        "yesterday": [],
        "previous_7_days": [],
        "older": []
    }
    
    for chat in chat_history:
        created_at = datetime.fromisoformat(chat["createdAt"])
        created_date = datetime(created_at.year, created_at.month, created_at.day)
        
        days_diff = (today - created_date).days
        
        if days_diff == 0:
            categorized_history["today"].append(chat)
        elif days_diff == 1:
            categorized_history["yesterday"].append(chat)
        elif 1 < days_diff <= 7:
            categorized_history["previous_7_days"].append(chat)
        else:
            categorized_history["older"].append(chat)
    
    return {"status": "success", "history": categorized_history}


@router.post("/get_chat_by_id")
def get_chat_by_id(request: GetChatByIdRequest) -> Dict[str, Any]:
    """
    Retrieves a specific chat by ID for a user.
    """
    chat = save_history.get_chat_by_id(request.chat_id, request.user_id)
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")
    
    return {"status": "success", "chat": chat}


@router.delete("/delete_chat")
def delete_chat(chat_id: str, user_id: str) -> Dict[str, Any]:
    """
    Deletes a specific chat by ID for a user.
    Uses query parameters instead of a request body.
    """
    success = save_history.delete_chat(chat_id, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")
    
    return {"status": "success"}

@router.get("/search_chat_history")
def search_chat_history(user_id: str, query: str) -> Dict[str, Any]:
    """
    Searches chat history for a specific user based on a query.
    Uses query parameters: user_id and query.
    Returns chat history items that contain messages matching the query.
    """
    matching_chats = save_history.search_chat_history(
        user_id=user_id,
        query=query
    )
    
    return {
        "status": "success",
        "results": matching_chats
    }

@router.put("/update_chat_title")
def update_chat_title(request: UpdateChatTitleRequest) -> Dict[str, Any]:
    """
    Updates the title of a specific chat by ID for a user.
    """
    success = save_history.update_chat_title(request.chat_id, request.new_title, request.user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")
    
    return {"status": "success"}


class AccessCheckRequest(BaseModel):
    user_id: str


@router.post("/access/check")
def access_check(req: AccessCheckRequest) -> Dict[str, Any]:
    """
    Access check with priority:
      1) Grant if user's email is in the whitelist
      2) Else, grant if the user belongs to any organization with an active/trialing subscription
    """
    try:
        if not req.user_id:
            raise HTTPException(status_code=400, detail="Missing user_id")

        # 1) Whitelist check by email
        user = user_service.get_user(req.user_id)
        if not user:
            return {"status": "success", "has_access": False}
        email = user.get("email")
        if email and user_service.is_email_whitelisted(email):
            return {"status": "success", "has_access": True}

        # 2) Organization subscription check (admin or any member should be allowed)
        try:
            # Reuse singleton OrganizationService to avoid pool exhaustion
            global _ORG_SVC_SINGLETON
            try:
                _ORG_SVC_SINGLETON
            except NameError:
                _ORG_SVC_SINGLETON = OrganizationService()
            org_service = _ORG_SVC_SINGLETON
            has_org_access = org_service.user_has_active_org_subscription(req.user_id)
            return {"status": "success", "has_access": bool(has_org_access)}
        except Exception as e:
            logger.warning(f"Org subscription check failed for user {req.user_id}: {e}")
            return {"status": "success", "has_access": False}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in access_check: {e}")
        raise HTTPException(status_code=500, detail="Failed to check access")

@router.post("/login")
def login(request: LoginRequest) -> Dict[str, Any]:
    """
    Handles user login and stores user information in the database.
    
    Args:
        request: LoginRequest containing user information
        
    Returns:
        Dictionary with status, message, and user data
    """
    request_id = str(uuid.uuid4())[:8]  # Generate a short unique ID for this request
    logger.info(f"[{request_id}] Login request started for user_id: {request.user_id}")
    
    try:
        # Validate request data
        if not request.user_id:
            logger.error(f"[{request_id}] Missing user_id in login request")
            raise HTTPException(status_code=400, detail="Missing user_id field")
            
        if not request.email:
            logger.error(f"[{request_id}] Missing email in login request")
            raise HTTPException(status_code=400, detail="Missing email field")
            
        if not request.auth_provider:
            logger.error(f"[{request_id}] Missing auth_provider in login request")
            raise HTTPException(status_code=400, detail="Missing auth_provider field")
        
        # Create/update a user document
        user_data = {
            "user_id": request.user_id,
            "email": request.email,
            "name": request.name or "",
            "auth_provider": request.auth_provider,
            "is_subscribed": request.is_subscribed,
        }
        
        logger.info(f"[{request_id}] Saving user data to database for user_id: {request.user_id}")
        
        # Save the user data using the user service
        result = user_service.save_user(user_data)
        
        if not result["success"]:
            error_code = 500
            # Map certain error types to appropriate HTTP status codes
            if result["error"] == "missing_field":
                error_code = 400
            elif result["error"] == "db_connection_error":
                error_code = 503  # Service Unavailable
            # Handle duplicate key violations with a 409 Conflict status
            elif result["error"] == "db_insert_error" and "duplicate key" in result["message"]:
                error_code = 409  # Conflict - resource already exists
                result["message"] = f"User already exists: {request.user_id}"
                logger.warning(f"[{request_id}] Duplicate user creation attempt: {request.user_id}")
                # Return a friendly response for duplicate inserts during concurrent requests
                response = {
                    "status": "success", 
                    "user_id": request.user_id,
                    "action": "exists",
                    "message": "User already exists",
                    "request_id": request_id
                }
                logger.info(f"[{request_id}] Login request completed with duplicate user: {request.user_id}")
                return response
                
            logger.error(f"[{request_id}] Failed to save user data: {result['message']}")
            raise HTTPException(status_code=error_code, detail=result["message"])
        
        # Decide post-login flow
        # Reuse a module-level singleton to avoid exhausting DB connections
        global _ORG_SVC_SINGLETON
        try:
            _ORG_SVC_SINGLETON
        except NameError:
            _ORG_SVC_SINGLETON = OrganizationService()
        org_service = _ORG_SVC_SINGLETON
        has_access = False
        try:
            has_access = user_service.has_access_fast(request.user_id)
        except Exception:
            has_access = False

        # If the user pre-selected a plan and is NOT already subscribed, create checkout and return redirect URL
        if (not has_access) and request.selected_price_id:
            try:
                stripe.api_key = Credentials.get_stripe_api_key()
                # Try to associate checkout with an existing organization for this user
                org_id_for_metadata = None
                try:
                    orgs = org_service.list_organizations_for_user(request.user_id)
                    if isinstance(orgs, list) and len(orgs) > 0 and isinstance(orgs[0], dict):
                        org_id_for_metadata = orgs[0].get("id")
                except Exception:
                    org_id_for_metadata = None
                session_params = dict(
                    mode="subscription",
                    line_items=[{"price": request.selected_price_id, "quantity": 1}],
                    success_url=(request.success_url or "https://app.example/success") + "?session_id={CHECKOUT_SESSION_ID}",
                    cancel_url=request.cancel_url or "https://app.example/cancel",
                    metadata={"user_id": request.user_id, **({"organization_id": org_id_for_metadata} if org_id_for_metadata else {})},
                    # We don't have organization_id in this flow; ensure metadata propagates to Subscription
                    subscription_data={
                        "metadata": {"user_id": request.user_id, **({"organization_id": org_id_for_metadata} if org_id_for_metadata else {})}
                    },
                    client_reference_id=org_id_for_metadata or request.user_id,
                )
                # Prefill email for Stripe receipts/invoices when available
                if request.email:
                    session_params["customer_email"] = request.email
                session = stripe.checkout.Session.create(**session_params)
                logger.info(f"[{request_id}] Created checkout session for user {request.user_id}")
                return {
                    "status": "success",
                    "next": "checkout",
                    "checkout_url": session.url,
                    "request_id": request_id,
                }
            except Exception as e:
                logger.error(f"[{request_id}] Failed to create checkout session: {e}")
                # Fall back to ask frontend to show plan selection
                return {
                    "status": "success",
                    "next": "choose_plan",
                    "request_id": request_id,
                }

        # If already subscribed/has access, go to app
        if has_access:
            return {
                "status": "success",
                "next": "app",
                "user_id": request.user_id,
                "request_id": request_id,
            }

        # Otherwise, ask frontend to present plan selection page
        return {
            "status": "success",
            "next": "choose_plan",
            "user_id": request.user_id,
            "request_id": request_id,
        }
    except HTTPException as http_ex:
        # Log exception details with request ID
        logger.error(f"[{request_id}] HTTP exception in login endpoint: {http_ex.status_code} - {http_ex.detail}")
        # Re-raise HTTP exceptions to preserve status code
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error in login endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

