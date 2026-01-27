import re
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from bs4 import BeautifulSoup
from datetime import datetime

from cloud.storage import AzureStorageClient
from definitions.enums import DataCategory, Source
from definitions.paths import Paths
from scrapers.nextens.nextens_login import NextensLogin
from logger.logger import Logger

logger = Logger.get_logger(__name__)


class AlmanakScraper:
    """Scraper for Nextens Almanak pages."""

    def __init__(self):
        # Folder structure
        self.paths = Paths()
        self.almanak_folder = Source.NEXTENS_ALMANAKKEN.value
        
        # Initialize storage client for uploading files
        self.storage_client = AzureStorageClient()

        # Initialize login
        self.login = NextensLogin()
        self.base_url = "https://naslag.nextens.nl"
        self.almanak_urls = {}
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

    def extract_almanak_urls(self, page: Page):
        """
        Extract almanak URLs from the main Almanakken page.
        Only extract URLs for the years 2023, 2024, and 2025 if available.
        """
        almanak_page_url = f"{self.base_url}/almanakken"
        logger.info(f"Navigating to main Almanakken page: {almanak_page_url}")
        page.goto(almanak_page_url, timeout=300000)
        
        # Wait longer for the page to fully load
        page.wait_for_load_state("networkidle", timeout=120000)
        
        try:
            # Wait for book elements to appear
            page.wait_for_selector("div.c-book", timeout=150000)
            
            # First try to find books based on c-book elements
            book_elements = page.query_selector_all("div.c-book")
            logger.info(f"Found {len(book_elements)} book elements")
            
            for i, book_element in enumerate(book_elements):
                try:
                    # Extract tax type from class attribute
                    tax_type = None
                    class_attr = book_element.get_attribute("class")
                    if class_attr:
                        for cls in class_attr.split():
                            if cls not in ["c-book", "has-tax-type", "single"]:
                                tax_type = cls
                                break
                    
                    if not tax_type:
                        logger.warning(f"Book {i+1}: Could not extract tax type from class: {class_attr}")
                    
                    # Get the book title
                    title_element = book_element.query_selector("a.book-title, a.c-link.book-title")
                    if not title_element:
                        logger.warning(f"Book {i+1}: No title element found")
                        continue
                    
                    book_title = title_element.text_content().strip()
                    if not book_title:
                        logger.warning(f"Book {i+1}: Could not extract book title")
                        continue
                        
                    logger.info(f"Book {i+1}: {book_title} ({tax_type if tax_type else 'Unknown type'})")
                    
                    # First try to find multiple volume books (e.g., Deel I, Deel II, or jan-jun, jul-dec)
                    multiple_volume_elements = book_element.query_selector_all("nextens-multiple-volume-book")
                    
                    if multiple_volume_elements and len(multiple_volume_elements) > 0:
                        logger.info(f"Book {i+1}: Found {len(multiple_volume_elements)} multiple volume elements")
                        
                        for vol_idx, vol_element in enumerate(multiple_volume_elements):
                            # Get the year from span.text
                            year_span = vol_element.query_selector("span.text")
                            if not year_span:
                                logger.warning(f"Book {i+1} Vol {vol_idx+1}: No year span found")
                                continue
                            
                            year = year_span.text_content().strip()
                            logger.info(f"Book {i+1} Vol {vol_idx+1}: Year {year}")
                            
                            # Only process years 2023-2025
                            if year not in ["2023", "2024", "2025"]:
                                logger.info(f"Book {i+1} Vol {vol_idx+1}: Skipping year {year} (not in 2023-2025)")
                                continue
                            
                            # Get all volume links
                            volume_links = vol_element.query_selector_all("a[href]")
                            
                            for link_idx, link in enumerate(volume_links):
                                href = link.get_attribute("href")
                                if not href:
                                    continue
                                
                                # Try to get the volume text (e.g., "Deel I", "jan-jun")
                                volume_text_element = link.query_selector("div.c-link__text")
                                volume_text = volume_text_element.text_content().strip() if volume_text_element else f"Part {link_idx+1}"
                                
                                # Create a descriptive key for this volume
                                key = f"{tax_type if tax_type else 'UNKNOWN'} {book_title} {year} {volume_text}"
                                full_url = f"{self.base_url}{href}" if not href.startswith("http") else href
                                
                                self.almanak_urls[key] = full_url
                                logger.info(f"Book {i+1} Vol {vol_idx+1}: Added URL for {key}")
                    else:
                        # Look for single volume books
                        logger.info(f"Book {i+1}: Looking for single volume books")
                        
                        # Try to find the content div containing single-volume-book elements
                        content_div = book_element.query_selector("div.content")
                        if not content_div:
                            logger.warning(f"Book {i+1}: No content div found")
                            
                        # Find all single-volume-book elements
                        single_volume_elements = []
                        if content_div:
                            single_volume_elements = content_div.query_selector_all("nextens-single-volume-book")
                        
                        if single_volume_elements and len(single_volume_elements) > 0:
                            logger.info(f"Book {i+1}: Found {len(single_volume_elements)} single volume elements")
                            
                            for vol_idx, vol_element in enumerate(single_volume_elements):
                                # Get the link with year information
                                year_link = vol_element.query_selector("a")
                                if not year_link:
                                    logger.warning(f"Book {i+1} Single Vol {vol_idx+1}: No link found")
                                    continue
                                
                                # Get the year text
                                year_element = year_link.query_selector("div.c-link__text")
                                year = year_element.text_content().strip() if year_element else ""
                                
                                if not year:
                                    # Try getting entire link text
                                    year = year_link.text_content().strip()
                                
                                # Check if year is one we want
                                if year not in ["2023", "2024", "2025"]:
                                    logger.info(f"Book {i+1} Single Vol {vol_idx+1}: Skipping year {year} (not in 2023-2025)")
                                    continue
                                
                                # Get the URL
                                href = year_link.get_attribute("href")
                                if not href:
                                    logger.warning(f"Book {i+1} Single Vol {vol_idx+1}: No href attribute on link")
                                    continue
                                
                                # Create key and add URL
                                key = f"{tax_type if tax_type else 'UNKNOWN'} {book_title} {year}"
                                full_url = f"{self.base_url}{href}" if not href.startswith("http") else href
                                
                                self.almanak_urls[key] = full_url
                                logger.info(f"Book {i+1} Single Vol {vol_idx+1}: Added URL for {key}")
                        else:
                            # If no volume elements found, try a single link for the book itself
                            logger.info(f"Book {i+1}: No volume elements found, checking for direct book link")
                            
                            # Look for year in the title
                            year_match = re.search(r'\b(202[345])\b', book_title)
                            year = year_match.group(1) if year_match else None
                            
                            if not year:
                                # Try to find year in nearby elements
                                year_element = book_element.query_selector("span.year, div.year")
                                if year_element:
                                    year_text = year_element.text_content().strip()
                                    year_match = re.search(r'\b(202[345])\b', year_text)
                                    if year_match:
                                        year = year_match.group(1)
                            
                            if not year:
                                logger.info(f"Book {i+1}: No year found in title or elements, assuming current year")
                                # If no year found, check if this might be a current almanac
                                # For non-year books, still include them with the current year tag
                                from datetime import datetime
                                current_year = str(datetime.now().year)
                                if current_year in ["2023", "2024", "2025"]:
                                    year = current_year
                            
                            # Only proceed if we have a valid year
                            if year and year in ["2023", "2024", "2025"]:
                                # Get href from title element
                                href = title_element.get_attribute("href")
                                if href:
                                    key = f"{tax_type if tax_type else 'UNKNOWN'} {book_title} {year}"
                                    full_url = f"{self.base_url}{href}" if not href.startswith("http") else href
                                    
                                    self.almanak_urls[key] = full_url
                                    logger.info(f"Book {i+1}: Added URL for {key}")
                                else:
                                    logger.warning(f"Book {i+1}: No href found on title element")
                            else:
                                logger.info(f"Book {i+1}: No valid year found or year not in 2023-2025")
                
                except Exception as e:
                    logger.error(f"Error processing book {i+1}: {str(e)}")
            
            # If no URLs were found, try an alternative approach
            if not self.almanak_urls:
                logger.warning("No almanac URLs found using primary method. Trying alternative approach...")
                
                # Look for links that include the year in the title
                all_links = page.query_selector_all("a[href*='/almanakken/book/']")
                
                for link_idx, link in enumerate(all_links):
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    
                    # Get all text content from the link
                    link_text = link.text_content().strip()
                    
                    # Check parent for additional text content
                    parent = link.evaluate_handle("el => el.parentElement")
                    parent_text = ""
                    if parent:
                        parent_text = parent.text_content().strip()
                    
                    # Combine all text to search for year and tax type
                    combined_text = f"{link_text} {parent_text}"
                    
                    # Look for year in the text
                    year_match = re.search(r'\b(202[345])\b', combined_text)
                    if year_match:
                        year = year_match.group(1)
                        
                        # Try to determine tax type from URL or text content
                        tax_type = "UNKNOWN"
                        tax_types = ["IB", "VPB", "BTW", "LB", "SW"]
                        for t in tax_types:
                            if t in combined_text:
                                tax_type = t
                                break
                        
                        key = f"{tax_type} Almanak {year}"
                        full_url = f"{self.base_url}{href}" if not href.startswith("http") else href
                        
                        self.almanak_urls[key] = full_url
                        logger.info(f"Alternative method: Added URL for {key}")
            
            logger.info(f"Total almanac URLs extracted: {len(self.almanak_urls)}")
            
        except Exception as e:
            logger.error(f"Error extracting almanac URLs: {e}")
            logger.exception(e)  # Print full stack trace
            raise

    def scrape_chapter_content(self, context, overview_url, almanak_name, year, tax_type, filename):
        """
        Scrape content from a chapter overview page and all its sub-chapter pages.
        This handles both direct content pages and pages with sub-chapters.
        """
        if not overview_url:
            logger.warning(f"No URL to scrape for {filename}")
            return

        # Create new page for content
        content_page = context.new_page()
        try:
            # Initialize content collection
            content_str = ""
            
            # First, navigate to the overview page
            logger.info(f"  Navigating to chapter overview: {overview_url}")
            try:
                # Set a longer timeout for navigation
                content_page.goto(overview_url, timeout=300000, wait_until="domcontentloaded")
                # Wait for networkidle to ensure page is fully loaded
                content_page.wait_for_load_state("networkidle", timeout=120000)
            except Exception as e:
                logger.warning(f"  Navigation issue for {overview_url}: {e}")
                # Try to proceed anyway if the page loaded partially
            
            # Check if this is an overview page with sub-chapters
            subchapter_links = []
            try:
                subchapter_links = content_page.query_selector_all("a.c-link.book-toc-ii")
            except Exception as e:
                logger.warning(f"  Error finding subchapter links: {e}")
            
            # Get the chapter title
            chapter_title = filename  # Default to filename if no title found
            try:
                title_element = content_page.query_selector("h1")
                if title_element:
                    chapter_title = title_element.text_content().strip()
            except Exception as e:
                logger.warning(f"  Error finding title element: {e}")
            
            if subchapter_links and len(subchapter_links) > 0:
                # This is an overview page with sub-chapters
                logger.info(f"  Found {len(subchapter_links)} sub-chapters")
                
                # Add the chapter title as a heading
                content_str += f"# {chapter_title}\n\n"
                
                # Get the summary content if available
                try:
                    summary_element = content_page.query_selector("div#summary")
                    if summary_element:
                        summary_text = summary_element.inner_text().strip()
                        if summary_text:
                            content_str += f"{summary_text}\n\n"
                except Exception as e:
                    logger.warning(f"  Error extracting summary: {e}")
                
                # Process each sub-chapter
                for idx, link in enumerate(subchapter_links):
                    try:
                        href = link.get_attribute("href")
                        if not href:
                            continue
                        
                        # Get the subchapter title
                        title_element = link.query_selector("div.c-link--text-toc-ii span.c-link--text-prefix-text")
                        subchapter_title = ""
                        if title_element:
                            subchapter_title = title_element.text_content().strip()
                        
                        # Get the subchapter number
                        number_element = link.query_selector("div.c-link--text-toc-ii span.c-link--text-prefix")
                        subchapter_number = ""
                        if number_element:
                            subchapter_number = number_element.text_content().strip()
                        
                        full_title = f"{subchapter_number} {subchapter_title}".strip()
                        
                        full_url = f"{self.base_url}{href}" if not href.startswith("http") else href
                        logger.info(f"  Processing sub-chapter {idx+1}/{len(subchapter_links)}: {full_title}")
                        
                        # Navigate to the sub-chapter using a new page instead of reusing the current one
                        # This prevents context destruction issues
                        with context.new_page() as subchapter_page:
                            try:
                                # Navigate to the sub-chapter
                                subchapter_page.goto(full_url, timeout=300000, wait_until="domcontentloaded")
                                subchapter_page.wait_for_load_state("networkidle", timeout=60000)
                                
                                # Add the sub-chapter title as a heading
                                content_str += f"## {full_title}\n\n"
                                
                                # Extract content
                                content_str = self.extract_page_content(subchapter_page, content_str)
                            except Exception as e:
                                logger.error(f"  Error processing subchapter {full_title}: {e}")
                                # Continue with next subchapter
                    except Exception as e:
                        logger.error(f"  Error with subchapter link {idx+1}: {e}")
                        # Continue with next link
            else:
                # This is a direct content page
                logger.info("  This is a direct content page")
                content_str = self.extract_page_content(content_page, content_str)
            
            # Remove excessive newlines
            content_str = re.sub(r'\n{3,}', '\n\n', content_str)
            
            # If content extracted successfully
            if content_str.strip():
                # Update metrics
                self.total_docs_processed += 1
                
                # Format the content with metadata headers similar to belastingdienst scraper
                formatted_content = ""
                if year:
                    formatted_content += f"Year: {year}\n"
                else:
                    # If year is empty, include current years like in belastingdienst scraper
                    formatted_content += f"Year: [2023, 2024, 2025]\n"
                formatted_content += f"Title: {chapter_title}\n"
                formatted_content += f"Source: {Source.NEXTENS_ALMANAKKEN.value}\n"
                formatted_content += f"Data Category: {DataCategory.JURIDISCHE_BEGELEIDING.value}\n"
                formatted_content += f"URL: {overview_url}\n"
                formatted_content += f"Scraped at: {datetime.now().isoformat()}\n"
                formatted_content += f"Content:\n{content_str}"
                
                doc_size = len(formatted_content)
                
                # Upload to Azure Storage
                if self.storage_client:
                    blob_name = f"{self.almanak_folder}/{filename}.txt"
                    self.storage_client.upload_text_as_blob(blob_name, formatted_content)
                    self.total_docs_uploaded += 1
                    logger.info(f"  Uploaded document to Azure Storage: {blob_name} ({doc_size} bytes)")
                else:
                    logger.info(f"  Processed document: {filename} ({doc_size} bytes)")
            else:
                logger.warning(f"  No content extracted for {filename}")

        except Exception as e:
            logger.error(f"Error while scraping chapter content for {filename}: {e}")
            logger.exception(e)  # Print full stack trace
        finally:
            content_page.close()
            
    def extract_page_content(self, page, content_str):
        """Extract the main content from a page."""
        try:
            # Try to get the chapter title if not already included
            if not re.search(r'^#\s', content_str.split('\n')[-2] if len(content_str.split('\n')) > 1 else ''):
                try:
                    title_element = page.query_selector("h1")
                    if title_element:
                        chapter_title = title_element.text_content().strip()
                        content_str += f"# {chapter_title}\n\n"
                except Exception as e:
                    logger.warning(f"  Error extracting page title: {e}")
            
            # Try different content extraction methods and use the one that yields best results
            content_extracted = False
            
            # Method 1: Try to get content from app-external-html-content which contains the main text
            try:
                content_elements = page.query_selector_all("app-external-html-content")
                
                if content_elements and len(content_elements) > 0:
                    for content_element in content_elements:
                        try:
                            paragraphs = content_element.query_selector_all("p, h2, h3, h4, ul, ol, table")
                            for p in paragraphs:
                                tag_name = p.evaluate("el => el.tagName.toLowerCase()")
                                text = p.inner_text().strip()
                                
                                if text:
                                    if tag_name.startswith('h'):
                                        # Add appropriate heading level based on the tag
                                        heading_level = int(tag_name[1]) + 1  # h2 becomes ###, etc.
                                        prefix = '#' * heading_level
                                        content_str += f"{prefix} {text}\n\n"
                                    elif tag_name == 'ul' or tag_name == 'ol':
                                        # Process lists
                                        list_items = p.query_selector_all("li")
                                        for item in list_items:
                                            item_text = item.inner_text().strip()
                                            if item_text:
                                                content_str += f"- {item_text}\n"
                                        content_str += "\n"
                                    elif tag_name == 'table':
                                        # Process tables (convert to simple text)
                                        rows = p.query_selector_all("tr")
                                        for row in rows:
                                            cells = row.query_selector_all("td, th")
                                            row_text = " | ".join([cell.inner_text().strip() for cell in cells if cell.inner_text().strip()])
                                            if row_text:
                                                content_str += f"{row_text}\n"
                                        content_str += "\n"
                                    else:
                                        # Regular paragraph
                                        content_str += f"{text}\n\n"
                            content_extracted = True
                        except Exception as e:
                            logger.warning(f"  Error processing content element: {e}")
                            # Continue with next element
            except Exception as e:
                logger.warning(f"  Error with method 1 content extraction: {e}")
            
            # Method 2: If no content was found, try alternative selectors
            if not content_extracted:
                try:
                    # Try to get content from app-shared-markup
                    markup_element = page.query_selector("app-shared-markup")
                    if markup_element:
                        paragraphs = markup_element.query_selector_all("p, h2, h3, h4, div.c-markup, ul, ol")
                        for p in paragraphs:
                            text = p.inner_text().strip()
                            if text:
                                content_str += f"{text}\n\n"
                                content_extracted = True
                except Exception as e:
                    logger.warning(f"  Error with method 2 content extraction: {e}")
            
            # Method 3: If still no content, try getting content from the entire page body
            if not content_extracted:
                try:
                    # Try to get content from main element or article
                    main_content = page.query_selector("main, article, app-shared-book-chapter-overview")
                    if main_content:
                        # Get all text nodes but exclude navigation, menus, and other non-content areas
                        text_nodes = main_content.query_selector_all(
                            "p, h1, h2, h3, h4, h5, h6, ul, ol, div:not(:has(*)), " +
                            "div.content, div.c-chapter-content, div.chapter-content"
                        )
                        
                        for node in text_nodes:
                            try:
                                text = node.inner_text().strip()
                                # Filter out very short text that's likely UI elements
                                if text and len(text) > 10:
                                    content_str += f"{text}\n\n"
                                    content_extracted = True
                            except Exception as e:
                                # Skip this node if there's an error
                                continue
                except Exception as e:
                    logger.warning(f"  Error with method 3 content extraction: {e}")
            
            # Method 4: Last resort - get entire page text
            if not content_extracted:
                try:
                    # Get text from the body element
                    body_text = page.evaluate("() => document.body.innerText")
                    if body_text and len(body_text) > 100:  # Ensure it's substantial content
                        # Split into lines and filter out navigation, menu items, etc.
                        lines = body_text.split('\n')
                        content_lines = [line.strip() for line in lines if len(line.strip()) > 10 and not line.strip().startswith("Menu") and not line.strip().startswith("Home")]
                        if content_lines:
                            content_str += "\n\n".join(content_lines)
                            content_extracted = True
                except Exception as e:
                    logger.warning(f"  Error with method 4 content extraction: {e}")
            
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

    def scrape_almanak_docs(self):
        """Scrape main Almanak pages, follow sub-links, extract and store content."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                # Authenticate and get the browser context
                context = self.authenticate(browser)

                # Open a new page in the authenticated context
                page = context.new_page()

                # Extract almanak URLs dynamically
                self.extract_almanak_urls(page)

                if not self.almanak_urls:
                    logger.error("No almanac URLs were found. Aborting.")
                    return
                
                logger.info(f"Beginning to process {len(self.almanak_urls)} almanacs")
                
                # Process each almanac
                for almanak_name, overview_url in self.almanak_urls.items():
                    # Extract metadata from almanak_name
                    parts = almanak_name.split(' ')
                    tax_type = parts[0] if parts else "UNKNOWN"
                    
                    # Extract year from the almanak_name
                    year_match = re.search(r'\b(202[345])\b', almanak_name)
                    year = year_match.group(1) if year_match else ""
                    
                    logger.info(f"Processing almanac: {almanak_name}")
                    logger.info(f"URL: {overview_url}, Tax type: {tax_type}, Year: {year}")
                    
                    # Navigate to the overview page
                    page.goto(overview_url, timeout=300000)
                    page.wait_for_load_state("networkidle", timeout=120000)
                    
                    # Check if this is a book overview page with chapter list
                    chapter_links = None
                    
                    # Try to find chapter links - first check standard chapter list
                    chapter_links = page.query_selector_all("ul.c-list.book-toc-i li a.c-link.book-toc-i")
                    
                    if not chapter_links or len(chapter_links) == 0:
                        # Try alternative selectors
                        chapter_links = page.query_selector_all("a[href*='/book/chapter/']")
                        
                    if not chapter_links or len(chapter_links) == 0:
                        # Last attempt: try to find any links that might be chapters
                        potential_links = page.query_selector_all("a[href]")
                        chapter_links = [link for link in potential_links if '/book/chapter/' in link.get_attribute("href") or '/almanakken/book/chapter/' in link.get_attribute("href") or '/chapter/' in link.get_attribute("href")]
                    
                    if chapter_links and len(chapter_links) > 0:
                        logger.info(f"Found {len(chapter_links)} chapters for {almanak_name}")
                        
                        # Process each chapter
                        for idx, link in enumerate(chapter_links):
                            href = link.get_attribute("href")
                            if not href:
                                continue
                                
                            # Try different ways to get the chapter title
                            chapter_title = ""
                            
                            # Try to get from prefix + text div structure
                            title_element = link.query_selector("div.c-link--text-toc-i")
                            if title_element:
                                # Get chapter number
                                prefix_span = title_element.query_selector("span.c-link--text-prefix")
                                chapter_num = prefix_span.text_content().strip() if prefix_span else ""
                                
                                # Get chapter title
                                title_div = title_element.query_selector("div")
                                title_text = title_div.text_content().strip() if title_div else ""
                                
                                chapter_title = f"{chapter_num} {title_text}".strip()
                            else:
                                # Try direct text content
                                chapter_title = link.text_content().strip()
                            
                            # Skip voorwerk
                            if "voorwerk" in href.lower() or "voorwerk" in chapter_title.lower():
                                logger.info(f"  Skipping 'Voorwerk' chapter: {chapter_title}")
                                continue
                            
                            full_chapter_url = f"{self.base_url}{href}" if not href.startswith("http") else href
                            logger.info(f"  Processing chapter {idx+1}/{len(chapter_links)}: {chapter_title}")
                            
                            # Create safe filename
                            clean_title = re.sub(r'^\d+\.?\s*', '', chapter_title).strip()
                            sanitized_filename = self.sanitize_filename(clean_title)
                            
                            # Process this chapter
                            self.scrape_chapter_content(context, full_chapter_url, almanak_name, year, tax_type, sanitized_filename)
                    else:
                        # If no chapter links found, treat the page itself as content
                        logger.info(f"No chapter links found for {almanak_name}, processing page as direct content")
                        
                        # Create safe filename
                        sanitized_filename = self.sanitize_filename(almanak_name)
                        
                        # Process the page as direct content
                        self.scrape_chapter_content(context, overview_url, almanak_name, year, tax_type, sanitized_filename)

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
    Main entry point for testing the AlmanakScraper directly.
    Run this file directly to start scraping almanacs.
    """
    try:
        # Initialize and run the scraper
        logger.info("Starting Nextens Almanak scraper...")
        scraper = AlmanakScraper()
        scraper.scrape_almanak_docs()
        logger.info("Nextens Almanak scraping completed successfully!")
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}", exc_info=True)
