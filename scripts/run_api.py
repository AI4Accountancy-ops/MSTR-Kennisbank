import sys
import os
import uvicorn

# Add src directory to Python path to make it the root for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')
sys.path.insert(0, src_path)

from logger.logger import Logger

logger = Logger.get_logger(__name__)

logger.info("Starting Uvicorn server...")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")
