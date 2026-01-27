from contextlib import asynccontextmanager
import asyncio
import contextlib

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from api.api import router as chat_router
from api.organizations import router as organizations_router
from api.billing import router as billing_router
from api.stripe_webhook import router as stripe_router
from api.m365_connector import router as m365_router
from services.organization_service import OrganizationService
from logger.logger import Logger

logger = Logger.get_logger(__name__)

# Define a lifespan handler using an async context manager.
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI application startup complete.")

    async def subscription_refresh_loop():
        service = OrganizationService()
        while True:
            try:
                # Run blocking sync work in a thread to avoid blocking the event loop
                refreshed = await asyncio.to_thread(service.refresh_all_subscriptions_from_stripe)
                logger.info(f"Periodic subscription refresh complete. Refreshed: {refreshed}")
            except Exception as e:
                logger.error(f"Periodic subscription refresh failed: {e}")
            # Sleep 10 minutes
            await asyncio.sleep(600)

    # Start background task
    app.state.subscription_task = asyncio.create_task(subscription_refresh_loop())

    try:
        yield {}
    finally:
        # Gracefully stop background task
        task = getattr(app.state, "subscription_task", None)
        if task:
            task.cancel()
            with contextlib.suppress(Exception):
                await task

# Create the FastAPI app, passing in the lifespan handler.
app = FastAPI(lifespan=lifespan)

# Add CORS middleware to handle cross-origin requests from frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the chat router under the "/api" prefix.
# Endpoints defined in chat_router will be available at routes starting with "/api".
app.include_router(chat_router, prefix="/api")
app.include_router(organizations_router, prefix="/api")
app.include_router(billing_router, prefix="/api")
app.include_router(stripe_router, prefix="/api")
app.include_router(m365_router, prefix="/api")

@app.get("/health")
async def health_check():
    """Health check endpoint for Azure App Service"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    
    # Use the correct module path - this should be "main:app"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
