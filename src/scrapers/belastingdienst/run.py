import asyncio
import os
import sys
from datetime import datetime

from logger.logger import Logger
from scrapers.belastingdienst.scraper import BelastingdienstScraper
from scrapers.belastingdienst.brochure import BrochureScraper
from scrapers.belastingdienst.scrape_extra_links import ExtraLinksScraper

logger = Logger.get_logger(__name__)

async def run_belastingdienst_scraper():
    """Run the main Belastingdienst scraper with 5 workers."""
    logger.info("Starting Belastingdienst scraper (main)")
    scraper = BelastingdienstScraper()
    page_contents = await scraper.start_scraping()
    logger.info("Belastingdienst scraper (main) completed")
    return page_contents

async def run_brochure_scraper():
    """Run the brochure scraper with 5 workers."""
    logger.info("Starting Belastingdienst brochure scraper")
    brochure_scraper = BrochureScraper()
    await brochure_scraper.scrape_brochures_async()
    logger.info("Belastingdienst brochure scraper completed")

async def run_extra_links_scraper():
    """Run the extra links scraper with 5 workers."""
    logger.info("Starting Belastingdienst extra links scraper")
    # Create ExtraLinksScraper with 5 workers for independent parallel processing
    extra_links_scraper = ExtraLinksScraper(max_workers=5)
    page_contents = await extra_links_scraper.start_scraping()
    logger.info("Belastingdienst extra links scraper completed")
    return page_contents

async def main():
    """Run all Belastingdienst scrapers independently with their own worker configurations."""
    start_time = datetime.now()
    logger.info(f"Starting all Belastingdienst scrapers at {start_time.isoformat()}")
    
    # Create temp directory if it doesn't exist
    os.makedirs("temp", exist_ok=True)
    
    # Run scrapers independently - each with their own Playwright instances and worker pools
    logger.info("Running scrapers independently with their own worker configurations...")
    
    results = []
    
    try:
        # Step 1: Run main scraper with 5 workers
        logger.info("=== STEP 1: Running Main Scraper (5 workers) ===")
        main_result = await run_belastingdienst_scraper()
        results.append(main_result)
        logger.info("Main Scraper completed successfully")
        
        # Step 2: Run extra links scraper with 5 workers
        logger.info("=== STEP 2: Running Extra Links Scraper (5 workers) ===")
        extra_result = await run_extra_links_scraper()
        results.append(extra_result)
        logger.info("Extra Links Scraper completed successfully")
        
        # Step 3: Run brochure scraper with 5 workers
        logger.info("=== STEP 3: Running Brochure Scraper (5 workers) ===")
        await run_brochure_scraper()
        results.append(None)  # Brochure scraper doesn't return results
        logger.info("Brochure Scraper completed successfully")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
    
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"All Belastingdienst scrapers completed at {end_time.isoformat()}")
    logger.info(f"Total duration: {duration}")
    
    # Log results summary
    main_pages = len(results[0]) if results[0] else 0
    extra_pages = len(results[1]) if len(results) > 1 and results[1] else 0
    logger.info(f"Total pages scraped - Main: {main_pages}, Extra: {extra_pages}")

if __name__ == "__main__":
    asyncio.run(main()) 