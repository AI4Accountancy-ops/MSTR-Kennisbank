import os
import re
from datetime import datetime

import html2text
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

from cloud.storage import AzureStorageClient
from definitions.enums import DataCategory, Source
from definitions.paths import Paths
from scrapers.nextens.nextens_login import NextensLogin
from logger.logger import Logger

logger = Logger.get_logger(__name__)


class OnderwerpScraper:
    def __init__(self):
        # Initialize login
        self.login = NextensLogin()
        
        # Base URL
        self.base_url = "https://naslag.nextens.nl"
        
        # Folder structure
        self.paths = Paths()
        self.onderwerp_folder = Source.NEXTENS_ONDERWERPEN.value
        
        # Initialize storage client for uploading files
        self.storage_client = AzureStorageClient()
        
        # Initialize the HTML to Markdown converter
        self.converter = html2text.HTML2Text()
        self.converter.ignore_links = True
        self.converter.ignore_images = True  # Ignore images
        self.converter.bypass_tables = False  # Process tables
        self.converter.body_width = 0  # Prevent wrapping
        
        # Track statistics
        self.total_docs_processed = 0
        self.total_docs_uploaded = 0
        
        # Initialize the browser context to None
        self.context = None

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

    def navigate_to_onderwerpen(self, page: Page):
        """Navigate to the 'onderwerpen' page after authentication."""
        try:
            target_url = f"{self.base_url}/onderwerpen"
            logger.info(f"Navigating to {target_url}...")
            page.goto(target_url, timeout=600000)
            page.wait_for_load_state("networkidle", timeout=600000)
            logger.info("Successfully navigated to the Onderwerpen page.")
        except Exception as e:
            logger.error(f"Failed to navigate to onderwerpen page: {e}")
            raise

    def expand_all_accordions(self, page: Page):
        """
        Expand all accordion items to reveal all links by clicking 'Toon alle onderwerpen'.
        """
        try:
            logger.info("Looking for 'Toon alle onderwerpen' button...")
            
            # Try to locate the 'Toon alle onderwerpen' button using its text content
            show_all_selector = "div.c-link__text:has-text('Toon alle onderwerpen')"
            
            # Wait for the element to be visible
            page.wait_for_selector(show_all_selector, state="visible", timeout=10000)
            
            # Click the button to show all topics
            logger.info("Clicking 'Toon alle onderwerpen' button...")
            page.click(show_all_selector)
            
            # Wait for the page to update after clicking the button
            page.wait_for_load_state("networkidle", timeout=10000)
            logger.info("All topics should now be expanded.")
            
        except Exception as e:
            logger.error(f"Failed to expand accordions: {e}")
            # Try alternative approach if the button is not found
            try:
                logger.info("Trying alternative approach to expand accordions...")
                # Try clicking each accordion header individually
                accordion_groups = page.query_selector_all("nextens-accordion-top-level-group")
                logger.info(f"Found {len(accordion_groups)} accordion groups.")

                for index, group in enumerate(accordion_groups, start=1):
                    try:
                        # Locate the collapse button within the group
                        collapse_button = group.query_selector("a.c-link.accordion-top-level-item")
                        if collapse_button:
                            # Check if the accordion is already expanded
                            aria_expanded = collapse_button.get_attribute("aria-expanded")
                            if aria_expanded != "true":
                                logger.info(f"Expanding accordion group {index}...")
                                collapse_button.click()
                                # Wait for the expansion animation to complete
                                page.wait_for_timeout(500)
                        else:
                            logger.warning(f"No collapse button found in accordion group {index}.")
                    except Exception as e:
                        logger.error(f"Error expanding accordion group {index}: {e}")
                        
                logger.info("Alternative expansion completed.")
            except Exception as e:
                logger.error(f"Both expansion methods failed: {e}")
                raise e

    def scrape_anchor_tags(self, page: Page) -> list:
        """
        Scrape all anchor tags from accordion items and return their hrefs and texts.
        """
        try:
            logger.info("Scraping all anchor tags from accordion items...")
            
            # Look for all accordion items with links
            links = []
            
            # First, find all accordion-item-resolver elements
            item_resolvers = page.query_selector_all("nextens-accordion-item-resolver")
            logger.info(f"Found {len(item_resolvers)} accordion item resolvers.")
            
            # Process each item resolver to find the relevant links
            for idx, resolver in enumerate(item_resolvers, 1):
                try:
                    # Find all accordion items within this resolver
                    anchor_tags = resolver.query_selector_all("a.c-link.accordion-item")
                    
                    for anchor_idx, anchor in enumerate(anchor_tags, 1):
                        href = anchor.get_attribute("href")
                        if not href:
                            continue
                            
                        # Get the link text
                        text_element = anchor.query_selector("div.c-link__text")
                        text = text_element.inner_text().strip() if text_element else anchor.inner_text().strip()
                        
                        if href:
                            full_url = f"{self.base_url}{href}" if href.startswith("/") else href
                            logger.info(f"Link {idx}.{anchor_idx}: {text} - {full_url}")
                            links.append({"text": text, "url": full_url})
                except Exception as e:
                    logger.error(f"Error processing item resolver {idx}: {e}")
                    continue
            
            # If no links found through item resolvers, try a more general approach
            if not links:
                logger.warning("No links found through item resolvers. Trying general approach...")
                anchor_tags = page.query_selector_all("a.c-link.accordion-item")
                logger.info(f"Found {len(anchor_tags)} anchor tags.")
                
                for index, anchor in enumerate(anchor_tags, start=1):
                    href = anchor.get_attribute("href")
                    if not href:
                        continue
                        
                    text_element = anchor.query_selector("div.c-link__text")
                    text = text_element.inner_text().strip() if text_element else anchor.inner_text().strip()
                    
                    full_url = f"{self.base_url}{href}" if href.startswith("/") else href
                    logger.info(f"Link {index}: {text} - {full_url}")
                    links.append({"text": text, "url": full_url})
            
            logger.info(f"Total links scraped: {len(links)}")
            return links
        except Exception as e:
            logger.error(f"Failed to scrape anchor tags: {e}")
            raise e

    def extract_and_clean_html(self, html_content: str) -> str:
        """
        Extract specific HTML elements and remove unwanted elements.

        Args:
            html_content (str): The raw HTML content of the page.

        Returns:
            str: The cleaned HTML content containing only the desired elements.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract <nextens-page-header>
            page_header = soup.find('nextens-page-header')
            if not page_header:
                logger.warning("No <nextens-page-header> found on the page.")
                page_header = ""  # Or handle accordingly

            # Extract <app-shared-markup>
            shared_markup = soup.find('app-shared-markup')
            if not shared_markup:
                logger.warning("No <app-shared-markup> found on the page.")
                shared_markup = ""  # Or handle accordingly

            # Remove all <p class="toc"> elements within the document
            toc_paragraphs = soup.find_all('p', class_='toc')
            for toc in toc_paragraphs:
                toc.decompose()  # Remove the element from the tree
                
            # Also remove any remaining elements with class containing "toc"
            toc_elements = soup.find_all(class_=lambda c: c and 'toc' in c)
            for element in toc_elements:
                element.decompose()

            # Combine the extracted parts
            combined_html = str(page_header) + str(shared_markup)
            
            # If both elements were empty, try a more general approach
            if not combined_html.strip():
                logger.warning("No content found. Trying more general extraction...")
                
                # Try to extract any main content
                main_content = soup.find('main')
                if main_content:
                    combined_html = str(main_content)
                else:
                    # Just get the body content as a last resort
                    body = soup.find('body')
                    if body:
                        combined_html = str(body)

            return combined_html

        except Exception as e:
            logger.error(f"Failed to extract and clean HTML: {e}")
            raise e

    def extract_year_from_page(self, page: Page) -> str:
        """
        Extract year from 'LAATST GECONTROLEERD OP' text in the page.
        
        Args:
            page (Page): The Playwright page object.
            
        Returns:
            str: Extracted year or empty string if not found.
        """
        try:
            # Look for the tag element with the "LAATST GECONTROLEERD OP" text
            year = ""
            
            # Use a more specific selector to find the tags element
            tags_selector = "span.c-tags__items__item--static"
            tags_elements = page.query_selector_all(tags_selector)
            
            # Extract text from each tag and look for "LAATST GECONTROLEERD OP"
            for tag in tags_elements:
                tag_text = tag.inner_text().strip()
                if "LAATST GECONTROLEERD OP" in tag_text:
                    # Extract the date part
                    date_parts = tag_text.split("OP")
                    if len(date_parts) > 1:
                        date_str = date_parts[1].strip()
                        # Extract year from the date (assumed format DD.MM.YYYY)
                        if "." in date_str:
                            year_part = date_str.split(".")[-1].strip()
                            if year_part.isdigit() and len(year_part) == 4:
                                year = year_part
                                logger.info(f"Extracted year from last checked date: {year}")
            
            return year
        except Exception as e:
            logger.error(f"Failed to extract year from page: {e}")
            return ""

    def convert_html_to_markdown(self, combined_html: str) -> str:
        """
        Convert HTML content to Markdown.

        Args:
            combined_html (str): The cleaned HTML content.

        Returns:
            str: The converted Markdown content.
        """
        try:
            markdown_content = self.converter.handle(combined_html)
            return markdown_content
        except Exception as e:
            logger.error(f"Failed to convert HTML to Markdown: {e}")
            raise

    def clean_content(self, markdown_content: str) -> str:
        """
        Clean the Markdown content by replacing multiple newlines with a single newline.

        Args:
            markdown_content (str): The raw Markdown content.

        Returns:
            str: The cleaned Markdown content.
        """
        try:
            # Replace multiple consecutive newlines with a single newline
            cleaned_content = re.sub(r'\n{3,}', '\n\n', markdown_content).strip()
            return cleaned_content
        except Exception as e:
            logger.error(f"Failed to clean Markdown content: {e}")
            raise

    def scrape_and_save_content(self, context: BrowserContext, links: list):
        """
        Scrape the content of each URL, convert it to Markdown, and save it to Azure Storage.
        """
        logger.info(f"Starting to scrape content from {len(links)} links.")

        for idx, link in enumerate(links, 1):
            title = link['text']
            url = link['url']

            # Sanitize the filename
            sanitized_title = self.sanitize_filename(title)
            
            # Create new page for content
            content_page = context.new_page()
            
            try:
                logger.info(f"[{idx}/{len(links)}] Scraping URL: {url}")
                # Navigate to the content page
                content_page.goto(url, timeout=300000, wait_until="domcontentloaded")
                content_page.wait_for_load_state("networkidle", timeout=120000)

                # Extract year from the page if possible
                year = self.extract_year_from_page(content_page)
                
                # Get the page content
                html_content = content_page.content()

                # Extract and clean HTML
                combined_html = self.extract_and_clean_html(html_content)

                # Convert HTML to Markdown
                markdown_content = self.convert_html_to_markdown(combined_html)

                # Clean markdown_content
                cleaned_content = self.clean_content(markdown_content)
                
                # Check if content was extracted successfully
                if cleaned_content.strip():
                    # Format the content with metadata headers
                    formatted_content = ""
                    # Add year information
                    if year:
                        formatted_content += f"Year: {year}\n"
                    else:
                        # If year is empty, include current years
                        formatted_content += f"Year: [2023, 2024, 2025]\n"
                    formatted_content += f"Title: {title}\n"
                    formatted_content += f"Source: {Source.NEXTENS_ONDERWERPEN.value}\n"
                    formatted_content += f"Data Category: {DataCategory.COMMENTAAR.value}\n"
                    formatted_content += f"URL: {url}\n"
                    formatted_content += f"Scraped at: {datetime.now().isoformat()}\n"
                    formatted_content += f"Content:\n{cleaned_content}"
                    
                    doc_size = len(formatted_content)
                    
                    # Upload to Azure Storage
                    if self.storage_client:
                        blob_name = f"{self.onderwerp_folder}/{sanitized_title}.txt"
                        self.storage_client.upload_text_as_blob(blob_name, formatted_content)
                        self.total_docs_uploaded += 1
                        logger.info(f"  Uploaded document to Azure Storage: {blob_name} ({doc_size} bytes)")
                    else:
                        logger.warning("Storage client not initialized, content not uploaded")
                    
                    # Update metrics    
                    self.total_docs_processed += 1
                else:
                    logger.warning(f"  No content extracted for {title}")

            except Exception as e:
                logger.error(f"Failed to scrape or save content from {url}: {e}")
                logger.exception(e)  # Print full stack trace
            finally:
                content_page.close()

    def scrape_onderwerp_docs(self):
        """Run the scraper to get all onderwerp documents."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                # Authenticate and get browser context
                context = self.authenticate(browser)
                
                # Open a new page in the authenticated context
                page = context.new_page()
                
                # Navigate to the onderwerpen page
                self.navigate_to_onderwerpen(page)
                
                # Expand all accordions to reveal all onderwerp links
                self.expand_all_accordions(page)
                
                # Scrape all onderwerp links
                links = self.scrape_anchor_tags(page)
                
                if not links:
                    logger.error("No onderwerp links were found. Aborting.")
                    return
                
                # Scrape and save content from each link
                self.scrape_and_save_content(context, links)
                
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
    Main entry point for testing the OnderwerpScraper directly.
    Run this file directly to start scraping onderwerpen.
    """
    try:
        # Initialize and run the scraper
        logger.info("Starting Nextens Onderwerp scraper...")
        scraper = OnderwerpScraper()
        scraper.scrape_onderwerp_docs()
        logger.info("Nextens Onderwerp scraping completed successfully!")
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}", exc_info=True)
