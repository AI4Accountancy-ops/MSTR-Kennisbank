from datetime import datetime

from services.repositories.whitelist_repo import WhitelistRepository
from logger.logger import Logger

logger = Logger.get_logger(__name__)

# Container name for the whitelist
WHITELIST_CONTAINER = "whitelist"

def main():
    # Initialize the Postgres whitelist repository
    repo = WhitelistRepository()
    
    # Emails to add to the whitelist
    emails_to_add = [
        # Add emails here as separated list of strings
    ]
    
    # Create whitelist item
    whitelist_item = {
        "id": "983393e5-5619-4268-b3c5-238352d26bfb",
        "partitionKey": "email_whitelist",
        "emails": emails_to_add,
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
        "description": "Whitelisted emails for system access"
    }
    
    # Upsert the item to the whitelist container
    success = repo.upsert_whitelist(whitelist_item)
    
    if success:
        logger.info(f"Successfully added emails to whitelist: {', '.join(emails_to_add)}")
    else:
        logger.error("Failed to add emails to whitelist")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error in add_whitelist script: {str(e)}")