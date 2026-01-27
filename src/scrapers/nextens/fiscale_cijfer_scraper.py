import re
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from bs4 import BeautifulSoup
from datetime import datetime
import html2text

from cloud.storage import AzureStorageClient
from definitions.enums import DataCategory, Source
from definitions.paths import Paths
from scrapers.nextens.nextens_login import NextensLogin
from logger.logger import Logger

logger = Logger.get_logger(__name__)


class FiscalCijferScraper:
    """Scraper for Nextens Fiscal Cijfers pages."""

    def __init__(self):
        # Folder structure
        self.paths = Paths()
        self.fiscal_cijfer_folder = Source.NEXTENS_FISCALE_CIJFER.value
        
        # Initialize storage client for uploading files
        self.storage_client = AzureStorageClient()

        # Initialize login
        self.login = NextensLogin()
        self.base_url = "https://naslag.nextens.nl"
        self.year_urls = {}
        # Initialize the browser context to None
        self.context = None
        
        # Track statistics
        self.total_docs_processed = 0
        self.total_docs_uploaded = 0

    def authenticate(self, browser: Browser) -> BrowserContext:
        """Authenticate and return the authenticated browser context."""
        context = browser.new_context()
        try:
            logger.info("Attempting to authenticate...")
            self.login.authenticate(context)
            logger.info("Authentication successful!")
            self.context = context  # Store the authenticated context
            return context
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            context.close()
            raise

    def extract_year_urls(self, page: Page):
        """
        Extract fiscal cijfers URLs for different years from the main page.
        Only extract URLs for the years 2023, 2024, and 2025 if available.
        """
        fiscal_cijfer_url = f"{self.base_url}/fiscale-cijfers"
        logger.info(f"Navigating to main Fiscal Cijfers page: {fiscal_cijfer_url}")
        page.goto(fiscal_cijfer_url, timeout=300000)
        
        # Wait longer for the page to fully load
        page.wait_for_load_state("networkidle", timeout=120000)
        
        try:
            # Wait for year link elements to appear
            page.wait_for_selector("a.c-link.small.ng-star-inserted", timeout=150000)
            
            # Get all year links
            year_elements = page.locator("a.c-link.small.ng-star-inserted")
            count = year_elements.count()
            logger.info(f"Found {count} year elements")
            
            for i in range(count):
                try:
                    # Extract the year text
                    year_text_element = year_elements.nth(i).locator("div.c-link__text.ng-star-inserted")
                    year_text = year_text_element.inner_text().strip()
                    
                    # Only process years 2023-2025
                    if year_text in ["2023", "2024", "2025"]:
                        # Get the URL
                        href = year_elements.nth(i).get_attribute("href")
                        if href:
                            full_url = f"{self.base_url}{href}" if not href.startswith("http") else href
                            self.year_urls[year_text] = full_url
                            logger.info(f"Added URL for year {year_text}: {full_url}")
                    else:
                        logger.info(f"Skipping year {year_text} (not in 2023-2025)")
                except Exception as e:
                    logger.error(f"Error processing year element {i+1}: {str(e)}")
            
            logger.info(f"Total year URLs extracted: {len(self.year_urls)}")
            
        except Exception as e:
            logger.error(f"Error extracting year URLs: {e}")
            logger.exception(e)
            raise

    def extract_chapter_urls(self, page: Page, year: str, year_url: str):
        """Extract chapter URLs from a specific year page."""
        chapter_urls = {}
        
        logger.info(f"Navigating to year page for {year}: {year_url}")
        page.goto(year_url, timeout=300000)
        page.wait_for_load_state("networkidle", timeout=120000)
        
        try:
            # Wait for chapter links to appear
            page.wait_for_selector("ul.c-list.book-toc-i", timeout=150000)
            chapter_links = page.locator("a.c-link.book-toc-i.ng-star-inserted")
            count = chapter_links.count()
            logger.info(f"Found {count} chapter links for year {year}")
            
            for i in range(count):
                try:
                    # Extract chapter title
                    chapter_text_element = chapter_links.nth(i).locator("div.c-link--text-toc-i.ng-star-inserted")
                    chapter_text = chapter_text_element.inner_text().strip()
                    
                    # Get chapter number
                    prefix_span = chapter_text_element.locator("span.c-link--text-prefix")
                    chapter_num = ""
                    if prefix_span.count() > 0:
                        chapter_num = prefix_span.inner_text().strip()
                    
                    # Get chapter title without number
                    chapter_title = chapter_text.replace(chapter_num, "").strip()
                    if not chapter_title:
                        chapter_title = chapter_text
                    
                    # Get chapter URL
                    href = chapter_links.nth(i).get_attribute("href")
                    if href:
                        full_url = f"{self.base_url}{href}" if not href.startswith("http") else href
                        chapter_urls[chapter_title] = {
                            "url": full_url,
                            "number": chapter_num
                        }
                        logger.info(f"Added chapter URL for {chapter_title} (number: {chapter_num})")
                except Exception as e:
                    logger.error(f"Error processing chapter link {i+1} for year {year}: {str(e)}")
            
            logger.info(f"Total chapter URLs extracted for year {year}: {len(chapter_urls)}")
            return chapter_urls
            
        except Exception as e:
            logger.error(f"Error extracting chapter URLs for year {year}: {e}")
            logger.exception(e)
            return {}

    def scrape_chapter_content(self, context, year, chapter_url, chapter_title, chapter_num):
        """
        Scrape content from a chapter overview page and all its sub-chapter pages.
        This handles both direct content pages and pages with sub-chapters.
        """
        if not chapter_url:
            logger.warning(f"No URL to scrape for {chapter_title}")
            return

        # Create new page for content
        chapter_page = context.new_page()
        try:
            # Initialize content collection
            content_str = ""
            
            # First, navigate to the chapter overview page
            logger.info(f"  Navigating to chapter overview: {chapter_url}")
            try:
                # Set a longer timeout for navigation
                chapter_page.goto(chapter_url, timeout=300000, wait_until="domcontentloaded")
                # Wait for networkidle to ensure page is fully loaded
                chapter_page.wait_for_load_state("networkidle", timeout=120000)
            except Exception as e:
                logger.warning(f"  Navigation issue for {chapter_url}: {e}")
                # Try to proceed anyway if the page loaded partially
            
            # Add the chapter title as a heading
            content_str += f"# {chapter_num} {chapter_title}\n\n"
            
            # Check if this is an overview page with sub-chapters
            subchapter_container = chapter_page.query_selector("app-shared-book-chapter-overview-chapters")
            if subchapter_container:
                logger.info(f"  Found subchapter container for {chapter_title}")
                subchapter_links = chapter_page.locator("a.c-link.book-toc-ii.ng-star-inserted")
                subchapter_count = subchapter_links.count()
                
                if subchapter_count > 0:
                    logger.info(f"  Found {subchapter_count} subchapters for {chapter_title}")
                    
                    # Get the summary content if available
                    try:
                        summary_element = chapter_page.query_selector("div#summary")
                        if summary_element:
                            summary_text = summary_element.inner_text().strip()
                            if summary_text:
                                content_str += f"{summary_text}\n\n"
                    except Exception as e:
                        logger.warning(f"  Error extracting summary: {e}")
                    
                    # Process each subchapter
                    for i in range(subchapter_count):
                        try:
                            # Get the subchapter link
                            sublink = subchapter_links.nth(i)
                            href = sublink.get_attribute("href")
                            if not href:
                                continue
                            
                            # Get the subchapter title
                            subchapter_text_element = sublink.locator("div.c-link--text-toc-ii")
                            
                            # Get prefix (number)
                            prefix_span = subchapter_text_element.locator("span.c-link--text-prefix")
                            subchapter_num = ""
                            if prefix_span.count() > 0:
                                subchapter_num = prefix_span.inner_text().strip()
                            
                            # Get title text
                            title_span = subchapter_text_element.locator("span.c-link--text-prefix-text")
                            subchapter_title = ""
                            if title_span.count() > 0:
                                subchapter_title = title_span.inner_text().strip()
                            
                            full_title = f"{subchapter_num} {subchapter_title}".strip()
                            full_url = f"{self.base_url}{href}" if not href.startswith("http") else href
                            
                            logger.info(f"  Processing subchapter {i+1}/{subchapter_count}: {full_title}")
                            
                            # Navigate to the subchapter
                            with context.new_page() as subchapter_page:
                                try:
                                    subchapter_page.goto(full_url, timeout=300000, wait_until="domcontentloaded")
                                    subchapter_page.wait_for_load_state("networkidle", timeout=60000)
                                    
                                    # Add the subchapter title
                                    content_str += f"## {full_title}\n\n"
                                    
                                    # Extract subchapter content
                                    content_str = self.extract_page_content(subchapter_page, content_str)
                                except Exception as e:
                                    logger.error(f"  Error processing subchapter {full_title}: {e}")
                                    # Continue with next subchapter
                        except Exception as e:
                            logger.error(f"  Error with subchapter {i+1}: {e}")
                            # Continue with next subchapter
                else:
                    # No subchapters found, but we might still have chapter content
                    logger.info(f"  No subchapters found for {chapter_title}, extracting direct content")
                    content_str = self.extract_page_content(chapter_page, content_str)
            else:
                # This is a direct content page
                logger.info(f"  This is a direct content page: {chapter_title}")
                content_str = self.extract_page_content(chapter_page, content_str)
            
            # Remove excessive newlines
            content_str = re.sub(r'\n{3,}', '\n\n', content_str)
            
            # If content extracted successfully
            if content_str.strip():
                # Update metrics
                self.total_docs_processed += 1
                
                # Create sanitized filename
                sanitized_filename = self.sanitize_filename(chapter_title)
                
                # Format the content with metadata headers
                formatted_content = ""
                formatted_content += f"Year: {year}\n"
                formatted_content += f"Title: {chapter_title}\n"
                formatted_content += f"Source: {Source.NEXTENS_FISCALE_CIJFER.value}\n"
                formatted_content += f"Data Category: {DataCategory.JURIDISCHE_BEGELEIDING.value}\n"
                formatted_content += f"URL: {chapter_url}\n"
                formatted_content += f"Scraped at: {datetime.now().isoformat()}\n"
                formatted_content += f"Content:\n{content_str}"
                
                doc_size = len(formatted_content)
                
                # Upload to Azure Storage
                if self.storage_client:
                    blob_name = f"{self.fiscal_cijfer_folder}/{sanitized_filename}_{year}.txt"
                    self.storage_client.upload_text_as_blob(blob_name, formatted_content)
                    self.total_docs_uploaded += 1
                    logger.info(f"  Uploaded document to Azure Storage: {blob_name} ({doc_size} bytes)")
                else:
                    logger.info(f"  Processed document: {sanitized_filename}_{year} ({doc_size} bytes)")
            else:
                logger.warning(f"  No content extracted for {chapter_title}")

        except Exception as e:
            logger.error(f"Error while scraping chapter content for {chapter_title}: {e}")
            logger.exception(e)  # Print full stack trace
        finally:
            chapter_page.close()
            
    def extract_page_content(self, page, content_str):
        """Extract the main content from a page."""
        try:
            # Initialize html2text with settings for good table formatting
            h = html2text.HTML2Text()
            h.body_width = 0  # Don't wrap text
            h.unicode_snob = True  # Use Unicode instead of ASCII
            h.ul_item_mark = "-"  # Use hyphen for unordered lists
            h.ignore_links = True  # Ignore links since we already have the URL in metadata
            h.ignore_images = True
            h.ignore_emphasis = False
            h.ignore_tables = False
            h.table_preference = 'pretty'  # Make tables look nicer
            
            # Try different content extraction methods and use the one that yields best results
            content_extracted = False
            
            # Method 1: Try to get content from app-shared-book-chapter-overview
            try:
                overview_locator = page.locator("app-shared-book-chapter-overview")
                if overview_locator.count() > 0:
                    overview_html = overview_locator.first.inner_html()
                    
                    # Use html2text to convert HTML to Markdown, preserving tables
                    overview_content = h.handle(overview_html).strip()
                    
                    if overview_content:
                        content_str += f"{overview_content}\n\n"
                        content_extracted = True
            except Exception as e:
                logger.warning(f"  Error with method 1 content extraction: {e}")
            
            # Method 2: Get content from app-shared-markup elements
            try:
                markup_locators = page.locator("app-shared-markup")
                markup_count = markup_locators.count()
                
                if markup_count > 0:
                    for i in range(markup_count):
                        markup_html = markup_locators.nth(i).inner_html()
                        if markup_html:
                            # Convert markup HTML to Markdown
                            markup_content = h.handle(markup_html).strip()
                            
                            if markup_content:
                                content_str += f"{markup_content}\n\n"
                                content_extracted = True
            except Exception as e:
                logger.warning(f"  Error with method 2 content extraction: {e}")
            
            # Method 3: Last resort - get complete page content
            if not content_extracted:
                try:
                    # Get the full HTML content of the main area
                    main_content = page.query_selector("main, article")
                    if main_content:
                        main_html = main_content.inner_html()
                        if main_html:
                            # Convert to Markdown with html2text
                            markdown_content = h.handle(main_html).strip()
                            
                            # Clean up the content by removing navigation, headers, etc.
                            lines = markdown_content.split('\n')
                            filtered_lines = []
                            for line in lines:
                                # Skip menu items, navigation, empty lines
                                if (line.strip() and 
                                    not line.startswith('Menu') and 
                                    not line.startswith('Home') and
                                    not 'Zoeken' in line and
                                    not '▾' in line):
                                    filtered_lines.append(line)
                            
                            if filtered_lines:
                                content_str += "\n".join(filtered_lines) + "\n\n"
                                content_extracted = True
                except Exception as e:
                    logger.warning(f"  Error processing page content with html2text: {e}")
                
                # If still no content, fall back to plain text
                if not content_extracted:
                    try:
                        body_text = page.evaluate("() => document.body.innerText")
                        if body_text:
                            lines = body_text.split('\n')
                            content_lines = []
                            for line in lines:
                                line = line.strip()
                                if len(line) > 10 and not line.startswith("Menu") and not line.startswith("Home"):
                                    content_lines.append(line)
                            
                            if content_lines:
                                content_str += "\n".join(content_lines) + "\n\n"
                                content_extracted = True
                    except Exception as e:
                        logger.warning(f"  Error extracting body text: {e}")
            
            # Clean up the content - remove duplicate newlines and fix spacing
            content_str = re.sub(r'\n{3,}', '\n\n', content_str)
            
            return content_str
        
        except Exception as e:
            logger.error(f"Error extracting page content: {e}")
            logger.exception(e)  # Print full stack trace
            return content_str

    def sanitize_filename(self, filename: str) -> str:
        """
        Clean a string to make it suitable for a filename.
        Removes or replaces characters that are problematic for filenames.
        """
        # Replace characters that are invalid for filenames with underscores
        invalid_chars = r'[<>:"/\\|?*]'
        clean_name = re.sub(invalid_chars, '_', filename)
        
        # Replace multiple spaces or underscores with single underscore
        clean_name = re.sub(r'[\s_]+', '_', clean_name)
        
        # Remove leading/trailing spaces and underscores
        clean_name = clean_name.strip('_ ')
        
        # Ensure filename isn't too long (max 255 chars is safe for most systems)
        if len(clean_name) > 200:
            clean_name = clean_name[:197] + '...'
            
        # Ensure non-empty filename
        if not clean_name:
            clean_name = "unnamed_file"
            
        return clean_name

    def scrape_fiscal_cijfer_docs(self):
        """Scrape the Fiscal Cijfers pages for all available years."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                # Authenticate and get the browser context
                context = self.authenticate(browser)

                # Open a new page in the authenticated context
                page = context.new_page()

                # Extract year URLs dynamically
                self.extract_year_urls(page)

                if not self.year_urls:
                    logger.error("No year URLs were found. Aborting.")
                    return
                
                logger.info(f"Beginning to process {len(self.year_urls)} years")
                
                # Process each year
                for year, year_url in self.year_urls.items():
                    logger.info(f"Processing year: {year}, URL: {year_url}")
                    
                    # Extract chapter URLs for this year
                    chapter_urls = self.extract_chapter_urls(page, year, year_url)
                    
                    if not chapter_urls:
                        logger.warning(f"No chapter URLs found for year {year}")
                        continue
                    
                    logger.info(f"Found {len(chapter_urls)} chapters for year {year}")
                    
                    # Process each chapter
                    for chapter_title, chapter_data in chapter_urls.items():
                        chapter_url = chapter_data["url"]
                        chapter_num = chapter_data["number"]
                        
                        # Skip "Voorwerk" chapters
                        if "voorwerk" in chapter_title.lower():
                            logger.info(f"  Skipping 'Voorwerk' chapter: {chapter_title}")
                            continue
                        
                        logger.info(f"  Processing chapter: {chapter_title}")
                        
                        # Scrape this chapter and its subchapters
                        self.scrape_chapter_content(context, year, chapter_url, chapter_title, chapter_num)
                
                page.close()
                
                logger.info(f"Scraping completed! Processed {self.total_docs_processed} documents and uploaded {self.total_docs_uploaded} to Azure Storage.")
                
            except Exception as e:
                logger.error(f"An error occurred during scraping: {e}")
                logger.exception(e)  # Print full stack trace
            finally:
                if self.context:
                    self.context.close()
                browser.close()


if __name__ == "__main__":
    """
    Main entry point for testing the FiscalCijferScraper directly.
    Run this file directly to start scraping fiscal cijfers.
    """
    try:
        # Initialize and run the scraper
        logger.info("Starting Nextens Fiscal Cijfer scraper...")
        scraper = FiscalCijferScraper()
        scraper.scrape_fiscal_cijfer_docs()
        logger.info("Nextens Fiscal Cijfer scraping completed successfully!")
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}", exc_info=True)
