import asyncio
import os
import re
import tempfile
from datetime import datetime
from typing import Set, List
from urllib.parse import urljoin, urlparse

import html2text
import requests
from playwright.async_api import async_playwright, Page, TimeoutError
from pymupdf4llm import to_markdown
from tqdm import tqdm

from cloud.storage import AzureStorageClient
from definitions.enums import Source, DataCategory
from logger.logger import Logger

logger = Logger.get_logger(__name__)

class ExtraLinksScraper:
    """
    Scraper for extracting extra links from Belastingdienst pages using the sitemap.
    This script finds all <a> tags in the content area of sitemap URLs and scrapes those linked pages.
    """
    BASE_URL = "https://www.belastingdienst.nl"
    SITEMAP_URL = "https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/niet_in_enig_menu/sitemap/sitemap"
    BLOB_FOLDER = f"{Source.BELASTINGDIENST.value}/extra_links"
    
    def __init__(self, max_workers: int = 8):
        self.sitemap_urls: Set[str] = set()
        self.extra_urls: Set[str] = set()
        self.pdf_urls: Set[str] = set()  # Track PDF URLs separately
        self.pdf_titles: dict = {}  # Track PDF titles: {url: title}
        self.scraped_urls: Set[str] = set()
        self.storage_client = AzureStorageClient()
        self.processed_count = 0
        self.pdf_count = 0  # Track PDF files separately
        self.recursion_depth = 0  # Track recursion depth
        self.max_recursion_depth = 5  # Prevent infinite recursion
        self.max_workers = max_workers  # Number of parallel workers
        
        # Thread-safe counters for parallel processing
        self._processed_count_lock = asyncio.Lock()
        self._pdf_count_lock = asyncio.Lock()
        self._scraped_urls_lock = asyncio.Lock()
        self._extra_urls_lock = asyncio.Lock()
        self._pdf_urls_lock = asyncio.Lock()
        
        # Create local directory for temporary files
        os.makedirs("temp", exist_ok=True)
        
    def get_filename_from_url(self, url: str) -> str:
        """
        Generate a sanitized filename from a URL.
        Removes http/https, www, and replaces slashes with underscores.
        """
        # Remove protocol (http/https)
        filename = re.sub(r'^https?://', '', url)
        
        # Remove www
        filename = re.sub(r'^www\.', '', filename)
        
        # Replace invalid filename characters with underscores
        filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
        
        # Replace slashes with underscores
        filename = filename.replace('/', '_')
        
        # Replace multiple underscores with a single one
        filename = re.sub(r'_+', '_', filename)
        
        # Ensure the filename isn't too long (max 200 chars) and ends with .txt
        if len(filename) > 200:
            filename = filename[:200]
        
        # Add .txt extension if it doesn't have one
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        return filename
    
    def get_filename_from_title(self, title: str, url: str = None) -> str:
        """
        Generate a sanitized filename from a title.
        If title is empty or too short, falls back to URL.
        
        Args:
            title: The title to use for the filename
            url: Optional URL to use as fallback
            
        Returns:
            A sanitized filename based on the title
        """
        if not title or len(title) < 5:
            # Title is too short or empty, fallback to URL
            if url:
                return self.get_filename_from_url(url)
            else:
                title = "untitled"
        
        # Remove any characters that aren't allowed in filenames
        filename = re.sub(r'[\\/*?:"<>|]', '', title)
        
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        
        # Replace multiple underscores with a single one
        filename = re.sub(r'_+', '_', filename)
        
        # Limit the length
        if len(filename) > 100:
            filename = filename[:100]
        
        # Add .txt extension
        filename = f"{filename}.txt"
        
        return filename
    
    async def start_scraping(self):
        """Main method to start the extra links scraping process."""
        logger.info(f"Starting Extra Links scraping process with {self.max_workers} workers")
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            
            # First extract all URLs from the sitemap
            context = await browser.new_context()
            page = await context.new_page()
            await self.extract_urls_from_sitemap(page)
            await page.close()
            await context.close()
            
            # Log the number of URLs found in sitemap
            logger.info(f"Found {len(self.sitemap_urls)} URLs in the sitemap")
            
            # Now process each sitemap URL to find extra links (parallel)
            await self._extract_extra_links_parallel(playwright)
            
            # Log the number of extra URLs and PDFs found
            logger.info(f"Found {len(self.extra_urls)} extra URLs to scrape")
            logger.info(f"Found {len(self.pdf_urls)} PDF files to scrape")
            
            # Sort extra URLs to process them in a consistent order
            sorted_extra_urls = sorted(self.extra_urls)
            
            # Scrape extra URLs with parallel processing
            await self._scrape_extra_links_parallel(playwright, sorted_extra_urls)
            
            await browser.close()
        
        # Log the final counts
        logger.info(f"Extra links scraping completed. Summary:")
        logger.info(f"  - Extra link files processed: {self.processed_count}")
        logger.info(f"  - PDF files processed: {self.pdf_count}")
        logger.info(f"  - Total files saved to blob storage: {self.processed_count + self.pdf_count}")
        logger.info(f"  - Max recursion depth: {self.max_recursion_depth}")
        logger.info(f"  - Parallel workers used: {self.max_workers}")
        return None
    
    async def _extract_extra_links_parallel(self, playwright):
        """Extract extra links from sitemap URLs using parallel processing."""
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def extract_single_url(url):
            async with semaphore:
                try:
                    browser = await playwright.chromium.launch(headless=True)
                    context = await browser.new_context()
                    page = await context.new_page()
                    
                    await self.extract_extra_links(page, url)
                    
                    await page.close()
                    await context.close()
                    await browser.close()
                    
                except Exception as e:
                    logger.error(f"Error extracting extra links from {url}: {str(e)}")
        
        # Create tasks for all sitemap URLs
        tasks = [extract_single_url(url) for url in sorted(self.sitemap_urls)]
        
        # Process with progress bar
        with tqdm(total=len(tasks), desc="Finding extra links", unit="url") as pbar:
            for coro in asyncio.as_completed(tasks):
                await coro
                pbar.update(1)
    
    async def _scrape_extra_links_parallel(self, playwright, urls):
        """Scrape extra URLs using parallel processing."""
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def scrape_single_url(url):
            async with semaphore:
                async with self._scraped_urls_lock:
                    if url in self.scraped_urls:
                        logger.debug(f"Extra link already processed: {url}")
                        return
                
                try:
                    browser = await playwright.chromium.launch(headless=True)
                    context = await browser.new_context()
                    page = await context.new_page()
                    
                    await self._scrape_content_page_recursive(page, url, context)
                    
                    await page.close()
                    await context.close()
                    await browser.close()
                    
                    # Small delay to be respectful to the server
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Error scraping {url}: {str(e)}")
        
        # Create tasks for all URLs
        tasks = [scrape_single_url(url) for url in urls]
        
        # Process with progress bar
        with tqdm(total=len(tasks), desc="Scraping extra links", unit="url") as pbar:
            for coro in asyncio.as_completed(tasks):
                await coro
                pbar.update(1)
    
    async def extract_urls_from_sitemap(self, page: Page):
        """Extract all URLs from the nav elements in the sitemap page."""
        await page.goto(self.SITEMAP_URL, timeout=600000)  # 10 minutes timeout
        
        # Wait for the sitemap content to load
        await page.wait_for_selector('div.col-sm-6.col-md-3 nav')
        
        # Extract nav sections and their links
        sections = [
            'div.col-sm-6.col-md-3 nav:has(h2#head-prive)',  # Privé section
            'div.col-sm-6.col-md-3 nav:has(h2#head-zakelijk)',  # Zakelijk section
            'div.col-sm-12.col-md-3 nav:has(h2#head-intermediair)',  # Intermediairs section
            'div.col-sm-12.col-md-3 nav:has(h2#head-douane)'  # Douane section
        ]
        
        for section_selector in sections:
            # Get all links in the section's nav element, including nested links
            links = await page.query_selector_all(f"{section_selector} a")
            
            for link in links:
                href = await link.get_attribute('href')
                if href and (href.startswith('/wps/wcm/connect/bldcontentnl/belastingdienst/') or 
                            href.startswith('/wps/wcm/connect/nl/')):
                    # Convert to absolute URL
                    full_url = urljoin(self.BASE_URL, href)
                    
                    # Only add URLs that belong to the belastingdienst.nl domain
                    if urlparse(full_url).netloc == 'www.belastingdienst.nl':
                        self.sitemap_urls.add(full_url)
    
    async def extract_extra_links(self, page: Page, source_url: str):
        """
        Extract all <a> tags from the content area of a source URL.
        Also extract PDF download links from .bldc-file elements.
        
        Args:
            page: The playwright page object
            source_url: The URL to extract extra links from
        """
        try:
            await page.goto(source_url, timeout=600000, wait_until="domcontentloaded")  # 10 minutes timeout
            extracted_link_count = 0
            
            # First identify and exclude any footer links from being collected
            footer_links = set()
            footer_elements = await page.query_selector_all('footer, [id="footer"], .bldc-footer')
            
            # Collect all URLs from footer elements to exclude them later
            for footer in footer_elements:
                links = await footer.query_selector_all('a')
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        full_url = urljoin(self.BASE_URL, href)
                        footer_links.add(full_url)
            
            logger.debug(f"Found {len(footer_links)} links in footer elements that will be excluded")
            
            # Find the main content area - same logic as in the original scraper
            content_element = await page.query_selector('article.content_main')
            
            if not content_element:
                content_element = await page.query_selector('div.article-content')
            
            if not content_element:
                content_element = await page.query_selector('main')
            
            if not content_element:
                content_element = await page.query_selector('div.bld-paragrap, div.mainpanel')
            
            if content_element:
                # First, extract PDF download links from .bldc-file elements
                pdf_file_elements = await content_element.query_selector_all('.bldc-file a.bldc-file-block')
                
                for pdf_element in pdf_file_elements:
                    href = await pdf_element.get_attribute('href')
                    if href and href.strip():
                        # Convert to absolute URL
                        full_url = urljoin(self.BASE_URL, href)
                        
                        # Check if this is actually a PDF URL
                        if self._is_pdf_url(full_url):
                            # Extract the PDF title from the .bldc-file-name element
                            file_name_element = await pdf_element.query_selector('.bldc-file-name')
                            if file_name_element:
                                pdf_title = await file_name_element.inner_text()
                                pdf_title = pdf_title.strip()
                            else:
                                pdf_title = self._get_pdf_title_from_url(full_url)
                            
                            async with self._pdf_urls_lock:
                                self.pdf_urls.add(full_url)
                                self.pdf_titles[full_url] = pdf_title
                            logger.debug(f"Found PDF download link: {full_url} with title: {pdf_title}")
                            extracted_link_count += 1
                
                # Then extract regular <a> tags from the content area
                links = await content_element.query_selector_all('a')
                
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        # Skip ReadSpeaker links
                        if href.startswith('//app-eu.readspeaker.com'):
                            continue
                        
                        # Skip Mijn Belastingdienst links which require login
                        if 'mijn.belastingdienst.nl' in href:
                            continue
                        
                        # Skip external links
                        if href.startswith('http') and not href.startswith(self.BASE_URL):
                            continue
                        
                        # Convert to absolute URL
                        full_url = urljoin(self.BASE_URL, href)
                        
                        # Skip if this URL is found in footer
                        if full_url in footer_links:
                            logger.debug(f"Skipping footer link: {full_url}")
                            continue
                        
                        # Only add URLs that belong to the belastingdienst.nl domain
                        if urlparse(full_url).netloc == 'www.belastingdienst.nl':
                            # Skip the source URL itself
                            if full_url != source_url:
                                # Check if this is a PDF URL (but not already processed as a download link)
                                if self._is_pdf_url(full_url) and full_url not in self.pdf_urls:
                                    self.pdf_urls.add(full_url)
                                    # Try to get the PDF title from the page
                                    pdf_title = await self._get_pdf_title_from_page(page, full_url)
                                    self.pdf_titles[full_url] = pdf_title
                                    logger.debug(f"Found PDF link: {full_url} with title: {pdf_title}")
                                elif not self._is_pdf_url(full_url):
                                    async with self._extra_urls_lock:
                                        self.extra_urls.add(full_url)
                                extracted_link_count += 1
                
                logger.debug(f"Extracted {extracted_link_count} extra links from {source_url}")
            else:
                logger.warning(f"No content area found on {source_url}")
                
        except TimeoutError:
            logger.warning(f"Timeout (10 min) while loading {source_url} - page may be slow or unavailable")
        except Exception as e:
            logger.error(f"Error extracting extra links from {source_url}: {str(e)}")
    
    async def _scrape_content_page(self, page: Page, url: str):
        """Scrape a content page and save its content using html2text for cleaner output."""
        try:
            await page.goto(url, timeout=600000, wait_until="domcontentloaded")  # 10 minutes timeout
            
            # Check if this is a footer page that shouldn't be scraped
            is_footer_page = await page.evaluate('''() => {
                // Check if this page mainly consists of footer-style navigation
                const footer = document.querySelector('footer#footer, .bldc-footer');
                
                if (footer) {
                    // Get navigation lists in the footer
                    const footerLists = footer.querySelectorAll('ul.bld-hyperlink');
                    const footerLinks = footer.querySelectorAll('a');
                    
                    // Get main content
                    const mainContent = document.querySelector('main');
                    
                    if (mainContent) {
                        // Compare link density - if the ratio of footer links to main content is high,
                        // this might be a footer navigation page
                        const mainLinks = mainContent.querySelectorAll('a');
                        const mainParagraphs = mainContent.querySelectorAll('p');
                        
                        // If there are many links in both footer and main, and few paragraphs,
                        // it's likely a navigation page
                        if (footerLists.length > 2 && mainLinks.length > 5 && mainParagraphs.length < 3) {
                            // Check for similar structure between main and footer
                            const mainLists = mainContent.querySelectorAll('ul.bld-hyperlink');
                            if (mainLists.length > 3) {
                                return true;
                            }
                        }
                    }
                }
                
                // Check if the page URL is actually in the footer links
                const currentPath = window.location.pathname;
                const footerLinks = document.querySelectorAll('footer a');
                
                for (const link of footerLinks) {
                    if (link.getAttribute('href') === currentPath) {
                        return true;
                    }
                }
                
                return false;
            }''')
            
            if is_footer_page:
                logger.debug(f"Skipping footer navigation page: {url}")
                return
            
            # Get the title
            title_element = await page.query_selector('h1')
            title = await title_element.inner_text() if title_element else "No Title"
            
            # First explicitly remove all footer elements from the page
            await page.evaluate('''() => {
                // Remove all footer elements
                const footers = document.querySelectorAll('footer, [id="footer"], .bldc-footer');
                footers.forEach(footer => footer.remove());
                
                // Remove all nav elements that might contain footerish links
                const navElements = document.querySelectorAll('nav.bld-hyperlink');
                navElements.forEach(nav => nav.remove());
                
                // Remove all bottom navigation lists
                const bottomNav = document.querySelectorAll('.bldc-footer-lists, .bldc-footer-basic');
                bottomNav.forEach(nav => nav.remove());
                
                // Remove ReadSpeaker elements
                const readSpeakerElements = document.querySelectorAll('[class*="readspeaker"]');
                readSpeakerElements.forEach(el => el.remove());
            }''')
            
            # Setup html2text converter
            h = html2text.HTML2Text()
            h.ignore_links = True  # Don't show URLs
            h.ignore_images = True
            h.ignore_tables = False
            h.body_width = 0  # No wrapping
            h.ignore_emphasis = False  # Preserve emphasis and headers
            h.unicode_snob = True  # Use unicode characters
            h.ul_item_mark = ''  # No bullet points

            # First check if there's an article.content_main which has the main article content
            content_element = await page.query_selector('article.content_main')
            
            # If no article.content_main, check for div.article-content which is also used
            if not content_element:
                content_element = await page.query_selector('div.article-content')
            
            content = ""
            
            if content_element:
                # Get the HTML content of the article
                article_html = await content_element.inner_html()
                
                # Convert HTML to plain text
                content = h.handle(article_html)
                
                # Post-processing to clean up text (but preserve headers)
                # Remove markdown formatting remnants except headers
                content = re.sub(r'\[|\]|\*|_', '', content)
                
                # Remove excessive newlines (more than 2) but preserve paragraph breaks
                content = re.sub(r'\n{3,}', '\n\n', content)
                
                # Remove the feedback section at the bottom if present
                content = re.sub(r'Bedankt! We hebben uw feedback ontvangen\..*$', '', content, flags=re.DOTALL)
                
                # Remove any indentation (leading spaces on lines)
                content = '\n'.join(line.lstrip() for line in content.split('\n'))
                
                # Clean up any leading/trailing whitespace
                content = content.strip()
            else:
                # Fallback to the previous method if article.content_main is not found
                # First try for main content area, but exclude any lists that might be navigation
                main_content = await page.query_selector('main')
                
                if main_content:
                    # Remove navigation-like elements from main before processing
                    await main_content.evaluate('''(element) => {
                        // Remove all list elements that have fewer than 3 paragraphs nearby
                        // These are likely navigation rather than content
                        const lists = element.querySelectorAll('ul');
                        lists.forEach(list => {
                            const surroundingParagraphs = list.parentElement.querySelectorAll('p');
                            if (surroundingParagraphs.length < 3) {
                                list.remove();
                            }
                        });
                        
                        // Also remove heading + list combinations with no paragraphs
                        const headings = element.querySelectorAll('h2, h3, h4');
                        headings.forEach(heading => {
                            const nextElement = heading.nextElementSibling;
                            if (nextElement && nextElement.tagName === 'UL') {
                                const surroundingParagraphs = heading.parentElement.querySelectorAll('p');
                                if (surroundingParagraphs.length < 2) {
                                    heading.remove();
                                    nextElement.remove();
                                }
                            }
                        });
                    }''')
                    
                    # Get HTML and convert with header preservation
                    main_html = await main_content.inner_html()
                    content = h.handle(main_html)
                    
                    # Post-processing to clean up text (but preserve headers)
                    # Remove markdown formatting remnants except headers
                    content = re.sub(r'\[|\]|\*|_', '', content)
                    
                    # Remove excessive newlines (more than 2) but preserve paragraph breaks
                    content = re.sub(r'\n{3,}', '\n\n', content)
                    
                    # Remove the feedback section at the bottom if present
                    content = re.sub(r'Bedankt! We hebben uw feedback ontvangen\..*$', '', content, flags=re.DOTALL)
                    
                    # Remove any indentation (leading spaces on lines)
                    content = '\n'.join(line.lstrip() for line in content.split('\n'))
                    
                    # Clean up any leading/trailing whitespace
                    content = content.strip()
                else:
                    # Last resort - fallback to any content div
                    content_element = await page.query_selector('div.bld-paragrap, div.mainpanel')
                    
                    if content_element:
                        element_html = await content_element.inner_html()
                        content = h.handle(element_html)
                        content = re.sub(r'\[|\]|\*|_', '', content)
                        # Remove excessive newlines (more than 2) but preserve paragraph breaks
                        content = re.sub(r'\n{3,}', '\n\n', content)
                        # Remove the feedback section at the bottom if present
                        content = re.sub(r'Bedankt! We hebben uw feedback ontvangen\..*$', '', content, flags=re.DOTALL)
                        # Remove any indentation (leading spaces on lines)
                        content = '\n'.join(line.lstrip() for line in content.split('\n'))
                        content = content.strip()
            
            # Skip empty content
            if not content.strip():
                logger.warning(f"No content found on {url}")
                return
                
            # Final check - if content looks like just navigation (lots of short lines),
            # skip it as it's likely a navigation/language page
            content_lines = content.strip().split('\n')
            non_empty_lines = [line for line in content_lines if line.strip()]
            
            if len(non_empty_lines) > 0:
                avg_line_length = sum(len(line) for line in non_empty_lines) / len(non_empty_lines)
                
                # If average line length is very short and there are several lines,
                # it's probably a navigation menu, not content
                if avg_line_length < 30 and len(non_empty_lines) > 5 and len(non_empty_lines) < 20:
                    logger.warning(f"Content appears to be navigation menu, skipping: {url}")
                    return
            
            # Save the content to a temporary file
            temp_filename = f"temp/belastingdienst_extra_links_temp.txt"
            with open(temp_filename, "w", encoding="utf-8") as f:
                f.write(f"Year: [2023, 2024, 2025]\n")
                f.write(f"Title: {title}\n")
                f.write(f"Source: {Source.BELASTINGDIENST.value}\n")
                f.write(f"Data Category: {DataCategory.PRIMAIRE.value}\n")
                f.write(f"URL: {url}\n")
                f.write(f"Scraped at: {datetime.now().isoformat()}\n")
                f.write(f"Content:\n{content}")
            
            # Upload to blob storage
            blob_name = self._get_blob_name_for_url(url)
            self.storage_client.upload_blob(blob_name, temp_filename)
            
            # Mark as scraped
            self.scraped_urls.add(url)
            self.processed_count += 1
            
            # Clean up temporary file
            os.remove(temp_filename)
            
            logger.info(f"Successfully scraped and saved extra link: {title} ({url})")
            
        except TimeoutError:
            logger.warning(f"Timeout (10 min) while loading {url} - page may be slow or unavailable")
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
    
    def _get_blob_name_for_url(self, url: str) -> str:
        """Generate a blob name for a URL."""
        # Create sanitized filename from URL
        filename = self.get_filename_from_url(url)
        return f"{self.BLOB_FOLDER}/{filename}"
    
    def _get_blob_name_for_title(self, title: str, url: str) -> str:
        """
        Generate a blob name using the title, similar to scraper.py's lees verder method.
        
        Args:
            title: The title of the content
            url: The URL of the content (used as fallback and for uniqueness)
            
        Returns:
            The blob name for storage
        """
        # Create sanitized filename from title
        filename = self.get_filename_from_title(title, url)
        
        # Create a hash of the URL to ensure uniqueness even if titles are the same
        url_hash = hash(url) % 10000  # Simple hash to keep it short
        
        # Combine the title-based filename with the URL hash
        filename_parts = filename.rsplit('.', 1)
        if len(filename_parts) == 2:
            filename = f"{filename_parts[0]}_{url_hash}.{filename_parts[1]}"
        else:
            filename = f"{filename}_{url_hash}.txt"
        
        return f"{self.BLOB_FOLDER}/{filename}"
    
    async def _scrape_content_page_recursive(self, page: Page, url: str, context, current_depth: int = 0):
        """
        Recursively scrape a content page and follow any links found within it.
        
        Args:
            page: The playwright page object
            url: The URL to scrape
            context: The browser context for creating new pages
            current_depth: Current recursion depth
        """
        # Check recursion depth limit
        if current_depth >= self.max_recursion_depth:
            logger.debug(f"Reached max recursion depth ({self.max_recursion_depth}) for {url}")
            return
        
        # Get the title first (we'll need it for the blob name)
        try:
            await page.goto(url, timeout=600000, wait_until="domcontentloaded")  # 10 minutes timeout
            title_element = await page.query_selector('h1')
            title = await title_element.inner_text() if title_element else "No Title"
        except Exception as e:
            logger.error(f"Error getting title for {url}: {str(e)}")
            title = "No Title"
        
        # Check if this page contains PDF downloads
        pdf_download_elements = await page.query_selector_all('.bldc-file a.bldc-file-block')
        if pdf_download_elements:
            logger.info(f"Found PDF download page: {url} with {len(pdf_download_elements)} PDFs")
            
            # Process each PDF download
            for pdf_element in pdf_download_elements:
                href = await pdf_element.get_attribute('href')
                if href and href.strip():
                    # Convert to absolute URL
                    pdf_url = urljoin(self.BASE_URL, href)
                    
                    # Check if this is actually a PDF URL
                    if self._is_pdf_url(pdf_url):
                        # Extract the PDF title from the .bldc-file-name element
                        file_name_element = await pdf_element.query_selector('.bldc-file-name')
                        if file_name_element:
                            pdf_title = await file_name_element.inner_text()
                            pdf_title = pdf_title.strip()
                        else:
                            pdf_title = self._get_pdf_title_from_url(pdf_url)
                        
                        # Check if already scraped using title-based blob name
                        pdf_blob_name = self._get_blob_name_for_title(pdf_title, pdf_url)
                        if self.storage_client.blob_exist(pdf_blob_name):
                            logger.info(f"PDF content already exists in blob storage: {pdf_blob_name}")
                            continue
                        
                        try:
                            # Download and parse the actual PDF file
                            pdf_content = await self._scrape_pdf_content(pdf_url, pdf_title)
                            
                            if pdf_content:
                                # Save the PDF content to a temporary file
                                temp_filename = f"temp/belastingdienst_pdf_temp.txt"
                                with open(temp_filename, "w", encoding="utf-8") as f:
                                    f.write(f"Year: [2023, 2024, 2025]\n")
                                    f.write(f"Title: {pdf_title}\n")
                                    f.write(f"Source: {Source.BELASTINGDIENST.value}\n")
                                    f.write(f"Data Category: {DataCategory.PRIMAIRE.value}\n")
                                    f.write(f"URL: {pdf_url}\n")
                                    f.write(f"Scraped at: {datetime.now().isoformat()}\n")
                                    f.write(f"Content:\n{pdf_content}")
                                
                                # Upload to blob storage using title-based blob name
                                self.storage_client.upload_blob(pdf_blob_name, temp_filename)
                                
                                # Mark as scraped
                                async with self._scraped_urls_lock:
                                    self.scraped_urls.add(pdf_url)
                                async with self._pdf_count_lock:
                                    self.pdf_count += 1
                                
                                # Clean up temporary file
                                os.remove(temp_filename)
                                
                                logger.info(f"Successfully downloaded and parsed PDF: {pdf_title} ({pdf_url})")
                            
                            # Sleep briefly to avoid overwhelming the server
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            logger.error(f"Error downloading/parsing PDF {pdf_url}: {str(e)}")
            
            # Mark the original page as processed (since we handled its PDFs)
            async with self._scraped_urls_lock:
                self.scraped_urls.add(url)
            async with self._processed_count_lock:
                self.processed_count += 1
            
            # Continue with recursive link discovery
            await self._find_and_scrape_nested_links(page, context, current_depth + 1)
            return
        
        # Check if already scraped at this depth using title-based blob name (for regular pages)
        blob_name = self._get_blob_name_for_title(title, url)
        if self.storage_client.blob_exist(blob_name):
            logger.debug(f"Content already exists in blob storage: {blob_name}")
            async with self._scraped_urls_lock:
                self.scraped_urls.add(url)
            return
        
        try:
            
            # Check if this is a footer page that shouldn't be scraped
            is_footer_page = await page.evaluate('''() => {
                // Check if this page mainly consists of footer-style navigation
                const footer = document.querySelector('footer#footer, .bldc-footer');
                
                if (footer) {
                    // Get navigation lists in the footer
                    const footerLists = footer.querySelectorAll('ul.bld-hyperlink');
                    const footerLinks = footer.querySelectorAll('a');
                    
                    // Get main content
                    const mainContent = document.querySelector('main');
                    
                    if (mainContent) {
                        // Compare link density - if the ratio of footer links to main content is high,
                        // this might be a footer navigation page
                        const mainLinks = mainContent.querySelectorAll('a');
                        const mainParagraphs = mainContent.querySelectorAll('p');
                        
                        // If there are many links in both footer and main, and few paragraphs,
                        // it's likely a navigation page
                        if (footerLists.length > 2 && mainLinks.length > 5 && mainParagraphs.length < 3) {
                            // Check for similar structure between main and footer
                            const mainLists = mainContent.querySelectorAll('ul.bld-hyperlink');
                            if (mainLists.length > 3) {
                                return true;
                            }
                        }
                    }
                }
                
                // Check if the page URL is actually in the footer links
                const currentPath = window.location.pathname;
                const footerLinks = document.querySelectorAll('footer a');
                
                for (const link of footerLinks) {
                    if (link.getAttribute('href') === currentPath) {
                        return true;
                    }
                }
                
                return false;
            }''')
            
            if is_footer_page:
                logger.debug(f"Skipping footer navigation page: {url}")
                return
            
            # First explicitly remove all footer elements from the page
            await page.evaluate('''() => {
                // Remove all footer elements
                const footers = document.querySelectorAll('footer, [id="footer"], .bldc-footer');
                footers.forEach(footer => footer.remove());
                
                // Remove all nav elements that might contain footerish links
                const navElements = document.querySelectorAll('nav.bld-hyperlink');
                navElements.forEach(nav => nav.remove());
                
                // Remove all bottom navigation lists
                const bottomNav = document.querySelectorAll('.bldc-footer-lists, .bldc-footer-basic');
                bottomNav.forEach(nav => nav.remove());
                
                // Remove ReadSpeaker elements
                const readSpeakerElements = document.querySelectorAll('[class*="readspeaker"]');
                readSpeakerElements.forEach(el => el.remove());
            }''')
            
            # Setup html2text converter
            h = html2text.HTML2Text()
            h.ignore_links = True  # Don't show URLs
            h.ignore_images = True
            h.ignore_tables = False
            h.body_width = 0  # No wrapping
            h.ignore_emphasis = False  # Preserve emphasis and headers
            h.unicode_snob = True  # Use unicode characters
            h.ul_item_mark = ''  # No bullet points

            # First check if there's an article.content_main which has the main article content
            content_element = await page.query_selector('article.content_main')
            
            # If no article.content_main, check for div.article-content which is also used
            if not content_element:
                content_element = await page.query_selector('div.article-content')
            
            content = ""
            
            if content_element:
                # Get the HTML content of the article
                article_html = await content_element.inner_html()
                
                # Convert HTML to plain text
                content = h.handle(article_html)
                
                # Post-processing to clean up text (but preserve headers)
                # Remove markdown formatting remnants except headers
                content = re.sub(r'\[|\]|\*|_', '', content)
                
                # Remove excessive newlines (more than 2) but preserve paragraph breaks
                content = re.sub(r'\n{3,}', '\n\n', content)
                
                # Remove the feedback section at the bottom if present
                content = re.sub(r'Bedankt! We hebben uw feedback ontvangen\..*$', '', content, flags=re.DOTALL)
                
                # Remove any indentation (leading spaces on lines)
                content = '\n'.join(line.lstrip() for line in content.split('\n'))
                
                # Clean up any leading/trailing whitespace
                content = content.strip()
            else:
                # Fallback to the previous method if article.content_main is not found
                # First try for main content area, but exclude any lists that might be navigation
                main_content = await page.query_selector('main')
                
                if main_content:
                    # Remove navigation-like elements from main before processing
                    await main_content.evaluate('''(element) => {
                        // Remove all list elements that have fewer than 3 paragraphs nearby
                        // These are likely navigation rather than content
                        const lists = element.querySelectorAll('ul');
                        lists.forEach(list => {
                            const surroundingParagraphs = list.parentElement.querySelectorAll('p');
                            if (surroundingParagraphs.length < 3) {
                                list.remove();
                            }
                        });
                        
                        // Also remove heading + list combinations with no paragraphs
                        const headings = element.querySelectorAll('h2, h3, h4');
                        headings.forEach(heading => {
                            const nextElement = heading.nextElementSibling;
                            if (nextElement && nextElement.tagName === 'UL') {
                                const surroundingParagraphs = heading.parentElement.querySelectorAll('p');
                                if (surroundingParagraphs.length < 2) {
                                    heading.remove();
                                    nextElement.remove();
                                }
                            }
                        });
                    }''')
                    
                    # Get HTML and convert with header preservation
                    main_html = await main_content.inner_html()
                    content = h.handle(main_html)
                    
                    # Post-processing to clean up text (but preserve headers)
                    # Remove markdown formatting remnants except headers
                    content = re.sub(r'\[|\]|\*|_', '', content)
                    
                    # Remove excessive newlines (more than 2) but preserve paragraph breaks
                    content = re.sub(r'\n{3,}', '\n\n', content)
                    
                    # Remove the feedback section at the bottom if present
                    content = re.sub(r'Bedankt! We hebben uw feedback ontvangen\..*$', '', content, flags=re.DOTALL)
                    
                    # Remove any indentation (leading spaces on lines)
                    content = '\n'.join(line.lstrip() for line in content.split('\n'))
                    
                    # Clean up any leading/trailing whitespace
                    content = content.strip()
                else:
                    # Last resort - fallback to any content div
                    content_element = await page.query_selector('div.bld-paragrap, div.mainpanel')
                    
                    if content_element:
                        element_html = await content_element.inner_html()
                        content = h.handle(element_html)
                        content = re.sub(r'\[|\]|\*|_', '', content)
                        # Remove excessive newlines (more than 2) but preserve paragraph breaks
                        content = re.sub(r'\n{3,}', '\n\n', content)
                        # Remove the feedback section at the bottom if present
                        content = re.sub(r'Bedankt! We hebben uw feedback ontvangen\..*$', '', content, flags=re.DOTALL)
                        # Remove any indentation (leading spaces on lines)
                        content = '\n'.join(line.lstrip() for line in content.split('\n'))
                        content = content.strip()
            
            # Skip empty content
            if not content.strip():
                logger.warning(f"No content found on {url}")
                return
                
            # Final check - if content looks like just navigation (lots of short lines),
            # skip it as it's likely a navigation/language page
            content_lines = content.strip().split('\n')
            non_empty_lines = [line for line in content_lines if line.strip()]
            
            if len(non_empty_lines) > 0:
                avg_line_length = sum(len(line) for line in non_empty_lines) / len(non_empty_lines)
                
                # If average line length is very short and there are several lines,
                # it's probably a navigation menu, not content
                if avg_line_length < 30 and len(non_empty_lines) > 5 and len(non_empty_lines) < 20:
                    logger.warning(f"Content appears to be navigation menu, skipping: {url}")
                    return
            
            # Save the content to a temporary file
            temp_filename = f"temp/belastingdienst_extra_links_temp.txt"
            with open(temp_filename, "w", encoding="utf-8") as f:
                f.write(f"Year: [2023, 2024, 2025]\n")
                f.write(f"Title: {title}\n")
                f.write(f"Source: {Source.BELASTINGDIENST.value}\n")
                f.write(f"Data Category: {DataCategory.PRIMAIRE.value}\n")
                f.write(f"URL: {url}\n")
                f.write(f"Scraped at: {datetime.now().isoformat()}\n")
                f.write(f"Content:\n{content}")
            
            # Upload to blob storage
            self.storage_client.upload_blob(blob_name, temp_filename)
            
            # Mark as scraped
            async with self._scraped_urls_lock:
                self.scraped_urls.add(url)
            async with self._processed_count_lock:
                self.processed_count += 1
            
            # Clean up temporary file
            os.remove(temp_filename)
            
            logger.info(f"Successfully scraped and saved extra link (depth {current_depth}): {title} ({url})")
            
            # Now find and recursively scrape any links in this content
            await self._find_and_scrape_nested_links(page, context, current_depth + 1)
            
        except TimeoutError:
            logger.warning(f"Timeout (10 min) while loading {url} - page may be slow or unavailable")
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
    
    async def _find_and_scrape_nested_links(self, page: Page, context, current_depth: int):
        """
        Find links in the current page and recursively scrape them.
        
        Args:
            page: The current page object
            context: The browser context for creating new pages
            current_depth: Current recursion depth
        """
        # Check recursion depth limit
        if current_depth >= self.max_recursion_depth:
            logger.debug(f"Reached max recursion depth ({self.max_recursion_depth})")
            return
        
        try:
            # First identify and exclude any footer links from being collected
            footer_links = set()
            footer_elements = await page.query_selector_all('footer, [id="footer"], .bldc-footer')
            
            # Collect all URLs from footer elements to exclude them later
            for footer in footer_elements:
                links = await footer.query_selector_all('a')
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        full_url = urljoin(self.BASE_URL, href)
                        footer_links.add(full_url)
            
            # Find the main content area - same logic as in the original scraper
            content_element = await page.query_selector('article.content_main')
            
            if not content_element:
                content_element = await page.query_selector('div.article-content')
            
            if not content_element:
                content_element = await page.query_selector('main')
            
            if not content_element:
                content_element = await page.query_selector('div.bld-paragrap, div.mainpanel')
            
            if content_element:
                # First, extract PDF download links from .bldc-file elements
                pdf_file_elements = await content_element.query_selector_all('.bldc-file a.bldc-file-block')
                
                for pdf_element in pdf_file_elements:
                    href = await pdf_element.get_attribute('href')
                    if href and href.strip():
                        # Convert to absolute URL
                        full_url = urljoin(self.BASE_URL, href)
                        
                        # Check if this is actually a PDF URL
                        if self._is_pdf_url(full_url) and full_url not in self.scraped_urls:
                            # Extract the PDF title from the .bldc-file-name element
                            file_name_element = await pdf_element.query_selector('.bldc-file-name')
                            if file_name_element:
                                pdf_title = await file_name_element.inner_text()
                                pdf_title = pdf_title.strip()
                            else:
                                pdf_title = self._get_pdf_title_from_url(full_url)
                            
                            async with self._pdf_urls_lock:
                                self.pdf_urls.add(full_url)
                                self.pdf_titles[full_url] = pdf_title
                            logger.debug(f"Found nested PDF download link: {full_url} with title: {pdf_title}")
                
                # Then extract regular <a> tags from the content area
                links = await content_element.query_selector_all('a')
                nested_urls = set()
                
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        # Skip ReadSpeaker links
                        if href.startswith('//app-eu.readspeaker.com'):
                            continue
                        
                        # Skip Mijn Belastingdienst links which require login
                        if 'mijn.belastingdienst.nl' in href:
                            continue
                        
                        # Skip external links
                        if href.startswith('http') and not href.startswith(self.BASE_URL):
                            continue
                        
                        # Convert to absolute URL
                        full_url = urljoin(self.BASE_URL, href)
                        
                        # Skip if this URL is found in footer
                        if full_url in footer_links:
                            continue
                        
                        # Only add URLs that belong to the belastingdienst.nl domain
                        if urlparse(full_url).netloc == 'www.belastingdienst.nl':
                            # Skip if already scraped
                            if full_url not in self.scraped_urls:
                                # Check if this is a PDF URL (but not already processed as a download link)
                                if self._is_pdf_url(full_url) and full_url not in self.pdf_urls:
                                    self.pdf_urls.add(full_url)
                                    # Try to get the PDF title from the page
                                    pdf_title = await self._get_pdf_title_from_page(page, full_url)
                                    self.pdf_titles[full_url] = pdf_title
                                    logger.debug(f"Found nested PDF link: {full_url} with title: {pdf_title}")
                                elif not self._is_pdf_url(full_url):
                                    nested_urls.add(full_url)
                
                # Recursively scrape each nested URL
                for nested_url in nested_urls:
                    try:
                        # Note: We don't check blob existence here since _scrape_content_page_recursive
                        # will handle that with the proper title-based blob name
                        if nested_url in self.scraped_urls:
                            logger.debug(f"Nested link already processed: {nested_url}")
                            continue
                        
                        # Create a new page for the nested URL
                        nested_page = await context.new_page()
                        await self._scrape_content_page_recursive(nested_page, nested_url, context, current_depth)
                        await nested_page.close()
                        
                        # Sleep briefly to avoid overwhelming the server
                        await asyncio.sleep(0.3)
                        
                    except Exception as e:
                        logger.error(f"Error scraping nested link {nested_url}: {str(e)}")
                
                if nested_urls:
                    logger.debug(f"Found and processed {len(nested_urls)} nested links at depth {current_depth}")
            
        except Exception as e:
            logger.error(f"Error finding nested links: {str(e)}")
    
    def _add_page_numbers_to_content(self, content: str) -> str:
        """
        Replace ----- page boundaries with numbered page markers.
        
        Args:
            content: The markdown content with ----- page boundaries
            
        Returns:
            Content with numbered page markers like --- page 1 ---, --- page 2 ---, etc.
        """
        # Split content by ----- boundaries
        parts = re.split(r'-----+', content)
        
        # If no page boundaries found, return original content
        if len(parts) <= 1:
            return content
        
        # Reconstruct content with numbered page markers
        result_parts = []
        page_number = 1
        
        for i, part in enumerate(parts):
            # Skip empty parts (which can happen with consecutive -----)
            if part.strip():
                result_parts.append(part.strip())
                # Add page marker after each part (except the last one)
                if i < len(parts) - 1:
                    result_parts.append(f"\n--- page {page_number} ---\n")
                    page_number += 1
        
        return '\n'.join(result_parts)

    async def _scrape_pdf_content(self, url: str, title: str = None) -> str:
        """
        Download and parse a PDF file using pymupdf4llm.
        
        Args:
            url: The URL of the PDF file
            title: Optional title for the PDF (used for logging)
            
        Returns:
            The parsed content as markdown text with numbered page markers
        """
        try:
            logger.info(f"Downloading and parsing PDF: {title or url}")
            
            # Download the PDF
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # Create a temporary file to store the PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            try:
                # Parse the PDF using pymupdf4llm
                markdown_content = to_markdown(temp_file_path)
                
                # Add numbered page markers
                markdown_content = self._add_page_numbers_to_content(markdown_content)
                
                # Clean up the temporary file
                os.unlink(temp_file_path)
                
                logger.info(f"Successfully parsed PDF: {title or url}")
                return markdown_content
                
            except Exception as e:
                # Clean up the temporary file in case of error
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                raise e
                
        except Exception as e:
            logger.error(f"Error downloading/parsing PDF {url}: {str(e)}")
            return None
    

    
    def _is_pdf_url(self, url: str) -> bool:
        """
        Check if a URL points to a PDF file.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL points to a PDF file
        """
        # Check if URL ends with .pdf
        if url.lower().endswith('.pdf'):
            return True
        
        # Check if URL contains common PDF indicators
        pdf_indicators = ['/pdf/', '/document/', '/download/', '.pdf']
        return any(indicator in url.lower() for indicator in pdf_indicators)
    
    async def _get_pdf_title_from_page(self, page: Page, pdf_url: str) -> str:
        """
        Extract PDF title from the page content using bldc-file-name class.
        Falls back to URL-based title if not found.
        
        Args:
            page: The playwright page object
            pdf_url: The PDF URL
            
        Returns:
            The PDF title
        """
        try:
            # Look for PDF download sections with bldc-file-name
            pdf_elements = await page.query_selector_all('.bldc-file a[href*=".pdf"]')
            
            for pdf_element in pdf_elements:
                href = await pdf_element.get_attribute('href')
                if href and pdf_url in href:
                    # Find the bldc-file-name element within this PDF section
                    file_name_element = await pdf_element.query_selector('.bldc-file-name')
                    if file_name_element:
                        title = await file_name_element.inner_text()
                        if title and title.strip():
                            logger.debug(f"Found PDF title from page: {title}")
                            return title.strip()
            
            # Fallback to URL-based title
            return self._get_pdf_title_from_url(pdf_url)
            
        except Exception as e:
            logger.debug(f"Error extracting PDF title from page: {str(e)}")
            # Fallback to URL-based title
            return self._get_pdf_title_from_url(pdf_url)
    
    def _get_pdf_title_from_url(self, url: str) -> str:
        """
        Extract a title from a PDF URL.
        
        Args:
            url: The PDF URL
            
        Returns:
            A sanitized title based on the URL
        """
        # Remove the domain and path, keep only the filename
        filename = url.split('/')[-1]
        
        # Remove .pdf extension
        if filename.lower().endswith('.pdf'):
            filename = filename[:-4]
        
        # Replace underscores and hyphens with spaces
        title = filename.replace('_', ' ').replace('-', ' ')
        
        # Capitalize words
        title = ' '.join(word.capitalize() for word in title.split())
        
        return title


async def main():
    """Run the Extra Links scraper to extract content from extra links in sitemap pages."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape extra links from Belastingdienst pages')
    parser.add_argument('--workers', type=int, default=8, 
                       help='Number of parallel workers (default: 8, recommended: 6-12)')
    parser.add_argument('--max-workers', type=int, default=16,
                       help='Maximum number of workers (default: 16)')
    
    args = parser.parse_args()
    
    # Validate worker count
    workers = min(max(args.workers, 1), args.max_workers)
    
    start_time = datetime.now()
    logger.info(f"Starting Extra Links scraper at {start_time.isoformat()}")
    logger.info(f"Using {workers} parallel workers")
    
    # Create temp directory if it doesn't exist
    os.makedirs("temp", exist_ok=True)
    
    # Create and run the scraper
    scraper = ExtraLinksScraper(max_workers=workers)
    page_contents = await scraper.start_scraping()
    
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Extra Links scraper completed at {end_time.isoformat()}")
    logger.info(f"Total duration: {duration}")
    
    # Avoid error if page_contents is None
    num_pages = len(page_contents) if page_contents else 0
    logger.info(f"Total extra link pages scraped: {num_pages}")


if __name__ == "__main__":
    asyncio.run(main()) 