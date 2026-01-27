import asyncio
import os
import re
from datetime import datetime
from typing import Set
from urllib.parse import urljoin, urlparse

import html2text
from playwright.async_api import async_playwright, Page, TimeoutError
from tqdm import tqdm

from cloud.storage import AzureStorageClient
from definitions.enums import Source, DataCategory
from logger.logger import Logger

logger = Logger.get_logger(__name__)

class BelastingdienstScraper:
    """
    Scraper for the Belastingdienst website that extracts content from the sitemap.
    """
    BASE_URL = "https://www.belastingdienst.nl"
    SITEMAP_URL = "https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/niet_in_enig_menu/sitemap/sitemap"
    BLOB_FOLDER = Source.BELASTINGDIENST.value
    
    def __init__(self):
        self.sitemap_urls: Set[str] = set()
        self.content_urls: Set[str] = set()
        self.scraped_urls: Set[str] = set()
        self.storage_client = AzureStorageClient()
        self.processed_count = 0
        self.lees_verder_count = 0  # Track lees verder files separately
        
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
        
        # Add a timestamp for uniqueness
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Add .txt extension
        filename = f"{filename}_{timestamp}.txt"
        
        return filename
    
    async def start_scraping(self):
        """Main method to start the scraping process."""
        logger.info("Starting Belastingdienst scraping process")
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            
            # First extract all URLs from the sitemap
            page = await context.new_page()
            await self.extract_urls_from_sitemap(page)
            await page.close()
            
            # Log the number of URLs found in sitemap
            logger.info(f"Found {len(self.sitemap_urls)} URLs in the sitemap")
            
            # Now process each sitemap URL to find content-overview sections
            content_page = await context.new_page()
            
            # Process sitemap URLs
            for url in tqdm(sorted(self.sitemap_urls), desc="Finding content URLs"):
                try:
                    # Extract content URLs from this sitemap URL
                    await self.extract_content_urls(content_page, url)
                except Exception as e:
                    logger.error(f"Error extracting content URLs from {url}: {str(e)}")
            
            await content_page.close()
            
            # Log the number of content URLs found
            logger.info(f"Found {len(self.content_urls)} content URLs to scrape")
            
            # Sort content URLs to process them in a consistent order
            sorted_content_urls = sorted(self.content_urls)
            
            for url in tqdm(sorted_content_urls, desc="Scraping content"):
                # Check if already scraped
                blob_name = self._get_blob_name_for_url(url)
                if self.storage_client.blob_exist(blob_name):
                    logger.info(f"Content already exists in blob storage: {blob_name}")
                    self.scraped_urls.add(url)
                    self.processed_count += 1
                    continue
                
                try:
                    # Use a new page for each URL to avoid state issues
                    content_page = await context.new_page()
                    await self._scrape_content_page(content_page, url)
                    await content_page.close()
                    
                    # Sleep briefly to avoid overwhelming the server
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error scraping {url}: {str(e)}")
            
            await browser.close()
        
        # Log the final counts with detailed breakdown
        logger.info(f"Scraping completed. Summary:")
        logger.info(f"  - Main content files processed: {self.processed_count}")
        logger.info(f"  - 'Lees verder' files processed: {self.lees_verder_count}")
        logger.info(f"  - Total files saved to blob storage: {self.processed_count + self.lees_verder_count}")
        return None
    
    async def extract_urls_from_sitemap(self, page: Page):
        """Extract all URLs from the nav elements in the sitemap page."""
        await page.goto(self.SITEMAP_URL, timeout=60000)
        
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
    
    async def extract_content_urls(self, page: Page, url: str):
        """
        Extract URLs from card components on a page.
        First look for <section data-type="content-overview"> elements, then fall back to other methods.
        
        Handles multiple formats:
        1. The content-overview sections with cards
        2. The card structure (div.col-sm/md/lg with card-body and ul.bld-hyperlink)
        3. The simpler format (div.col-sm-6 with ul.hyperlinks)
        
        If no card components or link lists are found, scrape the page content directly.
        """
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            extracted_link_count = 0
            
            # First identify and exclude any footer links from being collected
            # Find all links in footer elements
            footer_links = set()
            
            # This will find all links inside any footer element, but particularly with id="footer"
            footer_elements = await page.query_selector_all('footer, [id="footer"], .bldc-footer')
            
            # Collect all URLs from footer elements to exclude them later
            for footer in footer_elements:
                links = await footer.query_selector_all('a')
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        # Convert to absolute URL
                        full_url = urljoin(self.BASE_URL, href)
                        footer_links.add(full_url)
                        
            logger.debug(f"Found {len(footer_links)} links in footer elements that will be excluded")
            
            # First try to find content-overview sections
            content_overview_sections = await page.query_selector_all('section[data-type="content-overview"]')
            
            if content_overview_sections and len(content_overview_sections) > 0:
                logger.debug(f"Found {len(content_overview_sections)} content-overview sections on {url}")
                
                # Extract links from each content-overview section
                for section in content_overview_sections:
                    # Look for all link elements within the content-overview section
                    links = await section.query_selector_all('a')
                    
                    for link in links:
                        href = await link.get_attribute('href')
                        if href:
                            # Skip ReadSpeaker links
                            if href.startswith('//app-eu.readspeaker.com'):
                                continue
                            
                            # Skip Mijn Belastingdienst links which require login
                            if 'mijn.belastingdienst.nl' in href:
                                continue
                            
                            # Convert to absolute URL
                            full_url = urljoin(self.BASE_URL, href)
                            
                            # Skip if this URL is found in footer
                            if full_url in footer_links:
                                logger.debug(f"Skipping footer link: {full_url}")
                                continue
                            
                            # Only add URLs that belong to the belastingdienst.nl domain
                            if urlparse(full_url).netloc == 'www.belastingdienst.nl':
                                self.content_urls.add(full_url)
                                extracted_link_count += 1
            
            # If no content-overview sections found, try the card structure format
            if extracted_link_count == 0:
                # First try the card structure format
                cards = await page.query_selector_all('div[class*="col-sm-"][class*="col-md-"][class*="col-lg-"][class*="mb-4"]')
                
                if not cards or len(cards) == 0:
                    # Try with a more relaxed selector if the strict one doesn't work
                    cards = await page.query_selector_all('div[class*="col-sm-"][class*="mb-4"]')
                
                if cards and len(cards) > 0:
                    logger.debug(f"Found {len(cards)} content cards on {url}")
                    
                    # Extract links from each card
                    for card in cards:
                        # Skip if this card is inside a footer
                        is_in_footer = await page.evaluate('''
                            (card) => {
                                let parent = card;
                                while (parent) {
                                    if (parent.tagName === 'FOOTER' || parent.id === 'footer' || 
                                        (parent.className && parent.className.includes('bldc-footer'))) {
                                        return true;
                                    }
                                    parent = parent.parentElement;
                                }
                                return false;
                            }
                        ''', card)
                        
                        if is_in_footer:
                            logger.debug("Skipping card that is inside a footer element")
                            continue
                            
                        # Look for the card body which contains links
                        card_body = await card.query_selector('div.card-body')
                        
                        if card_body:
                            # First try to find links within ul.bld-hyperlink (most common structure)
                            link_lists = await card_body.query_selector_all('ul.bld-hyperlink')
                            
                            if link_lists and len(link_lists) > 0:
                                for link_list in link_lists:
                                    links = await link_list.query_selector_all('a')
                                    
                                    for link in links:
                                        href = await link.get_attribute('href')
                                        if href:
                                            # Skip ReadSpeaker links
                                            if href.startswith('//app-eu.readspeaker.com'):
                                                continue
                                            
                                            # Skip Mijn Belastingdienst links which require login
                                            if 'mijn.belastingdienst.nl' in href:
                                                continue
                                            
                                            # Convert to absolute URL
                                            full_url = urljoin(self.BASE_URL, href)
                                            
                                            # Skip if this URL is found in footer
                                            if full_url in footer_links:
                                                logger.debug(f"Skipping footer link: {full_url}")
                                                continue
                                            
                                            # Only add URLs that belong to the belastingdienst.nl domain
                                            if urlparse(full_url).netloc == 'www.belastingdienst.nl':
                                                self.content_urls.add(full_url)
                                                extracted_link_count += 1
                            else:
                                # If no ul.bld-hyperlink, try finding any links in the card body
                                links = await card_body.query_selector_all('a')
                                
                                for link in links:
                                    href = await link.get_attribute('href')
                                    if href:
                                        # Skip ReadSpeaker links
                                        if href.startswith('//app-eu.readspeaker.com'):
                                            continue
                                        
                                        # Skip Mijn Belastingdienst links which require login
                                        if 'mijn.belastingdienst.nl' in href:
                                            continue
                                        
                                        # Convert to absolute URL
                                        full_url = urljoin(self.BASE_URL, href)
                                        
                                        # Skip if this URL is found in footer
                                        if full_url in footer_links:
                                            logger.debug(f"Skipping footer link: {full_url}")
                                            continue
                                        
                                        # Only add URLs that belong to the belastingdienst.nl domain
                                        if urlparse(full_url).netloc == 'www.belastingdienst.nl':
                                            self.content_urls.add(full_url)
                                            extracted_link_count += 1
            
            # If no content-overview sections or traditional cards found, try the alternative format
            if extracted_link_count == 0:
                # Try the alternative format with div.col-sm-6 and ul.hyperlinks
                col_divs = await page.query_selector_all('div.col-sm-6')
                
                if col_divs and len(col_divs) > 0:
                    logger.debug(f"Found {len(col_divs)} column divs on {url}")
                    
                    for col_div in col_divs:
                        # Skip if this div is inside a footer
                        is_in_footer = await page.evaluate('''
                            (element) => {
                                let parent = element;
                                while (parent) {
                                    if (parent.tagName === 'FOOTER' || parent.id === 'footer' || 
                                        (parent.className && parent.className.includes('bldc-footer'))) {
                                        return true;
                                    }
                                    parent = parent.parentElement;
                                }
                                return false;
                            }
                        ''', col_div)
                        
                        if is_in_footer:
                            logger.debug("Skipping div that is inside a footer element")
                            continue
                            
                        # Check for link lists (either ul.hyperlinks or ul.bld-hyperlink) within the column div
                        for list_class in ['ul.hyperlinks', 'ul.bld-hyperlink']:
                            link_lists = await col_div.query_selector_all(list_class)
                            
                            if link_lists and len(link_lists) > 0:
                                for link_list in link_lists:
                                    links = await link_list.query_selector_all('a')
                                    
                                    for link in links:
                                        href = await link.get_attribute('href')
                                        if href:
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
                                                self.content_urls.add(full_url)
                                                extracted_link_count += 1
                        
                        # Also check for links in the h2 header
                        h2_links = await col_div.query_selector_all('h2 > a')
                        for link in h2_links:
                            href = await link.get_attribute('href')
                            if href:
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
                                    self.content_urls.add(full_url)
                                    extracted_link_count += 1
                
                logger.debug(f"Extracted {extracted_link_count} URLs from alternative format on {url}")
            
            # If we still didn't find any links, fall back to scraping the page content directly
            if extracted_link_count == 0:
                logger.debug(f"No links found in any format on {url}, will scrape this page directly")
                self.content_urls.add(url)
            else:
                logger.debug(f"Total extracted links: {extracted_link_count}")
                
        except TimeoutError:
            logger.warning(f"Timeout while loading {url}")
            # Still add the URL to be tried again later
            self.content_urls.add(url)
        except Exception as e:
            logger.error(f"Error extracting content URLs from {url}: {str(e)}")
            # Still add the URL to be tried again later
            self.content_urls.add(url)
    
    async def _scrape_content_page(self, page: Page, url: str):
        """Scrape a content page and save its content using html2text for cleaner output."""
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
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
            
            # Check for "bd-lees-verder" links and process them separately
            await self._handle_lees_verder_links(page, url)
            
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
                
                # Post-processing to clean up text
                # Remove markdown formatting remnants (but preserve headers)
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
                    
                    # Get HTML and convert
                    main_html = await main_content.inner_html()
                    content = h.handle(main_html)
                    
                    # Post-processing to clean up text
                    # Remove markdown formatting remnants (but preserve headers)
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
            temp_filename = f"temp/belastingdienst_temp.txt"
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
            
            logger.info(f"Successfully scraped and saved: {title} ({url})")
            
        except TimeoutError:
            logger.warning(f"Timeout while loading {url}")
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
    
    def _get_blob_name_for_url(self, url: str) -> str:
        """Generate a blob name for a URL."""
        # Create sanitized filename from URL
        filename = self.get_filename_from_url(url)
        return f"{self.BLOB_FOLDER}/{filename}"
    
    def _get_blob_name_for_lees_verder(self, title: str, url: str) -> str:
        """
        Generate a blob name for a "lees verder" link, using the title.
        
        Args:
            title: The title of the lees verder content
            url: The URL of the lees verder content (used as fallback)
            
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
    
    async def _handle_lees_verder_links(self, page: Page, parent_url: str) -> None:
        """
        Handle "lees verder" links (bd-lees-verder class) by extracting their URLs and content.
        Each "lees verder" link content is saved to a separate file.
        
        Args:
            page: The playwright page object
            parent_url: The URL of the parent page
        """
        # Find all "bd-lees-verder" elements
        lees_verder_elements = await page.query_selector_all('p.bd-lees-verder')
        
        if not lees_verder_elements or len(lees_verder_elements) == 0:
            logger.debug(f"No 'lees verder' links found on {parent_url}")
            return
        
        logger.info(f"Found {len(lees_verder_elements)} 'lees verder' links on {parent_url}")
        
        # Get the browser context from the current page
        context = page.context
        
        # Iterate through each "lees verder" element
        for lv_element in lees_verder_elements:
            try:
                # Get the link URL from the anchor tag
                link_element = await lv_element.query_selector('a')
                if not link_element:
                    continue
                
                href = await link_element.get_attribute('href')
                if not href:
                    continue
                
                # Get the link title (used for filename)
                link_title = await link_element.get_attribute('title')
                if link_title and link_title.startswith("Lees verder over "):
                    # Extract the actual title part after "Lees verder over "
                    link_title = link_title[17:]
                
                # Convert to absolute URL
                lv_url = urljoin(self.BASE_URL, href)
                
                # Skip if URL is not in the belastingdienst.nl domain
                if urlparse(lv_url).netloc != 'www.belastingdienst.nl':
                    continue
                
                # Create a new page to navigate to the link
                lv_page = await context.new_page()
                
                try:
                    await lv_page.goto(lv_url, timeout=60000, wait_until="domcontentloaded")
                    
                    # Setup html2text converter
                    h = html2text.HTML2Text()
                    h.ignore_links = True
                    h.ignore_images = True
                    h.ignore_tables = False
                    h.body_width = 0
                    h.ignore_emphasis = False  # Preserve emphasis and headers
                    h.unicode_snob = True
                    h.ul_item_mark = ''
                    
                    # Remove footer and navigation elements
                    await lv_page.evaluate('''() => {
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
                    
                    # Get the title
                    lv_title_element = await lv_page.query_selector('h1')
                    lv_title = await lv_title_element.inner_text() if lv_title_element else link_title or "No Title"
                    
                    # Get the blob name based on the title
                    lv_blob_name = self._get_blob_name_for_lees_verder(lv_title, lv_url)
                    
                    # Check if already scraped to avoid duplicating work
                    if lv_url in self.scraped_urls or self.storage_client.blob_exist(lv_blob_name):
                        logger.info(f"'Lees verder' content already exists in blob storage: {lv_blob_name}")
                        await lv_page.close()
                        continue
                    
                    logger.info(f"Processing 'lees verder' link: {lv_url}")
                    
                    # Extract content using similar logic as in _scrape_content_page
                    content_element = await lv_page.query_selector('article.content_main')
                    
                    if not content_element:
                        content_element = await lv_page.query_selector('div.article-content')
                    
                    content = ""
                    
                    if content_element:
                        article_html = await content_element.inner_html()
                        content = h.handle(article_html)
                    else:
                        main_content = await lv_page.query_selector('main')
                        if main_content:
                            main_html = await main_content.inner_html()
                            content = h.handle(main_html)
                        else:
                            content_element = await lv_page.query_selector('div.bld-paragrap, div.mainpanel')
                            if content_element:
                                element_html = await content_element.inner_html()
                                content = h.handle(element_html)
                            else:
                                logger.warning(f"No content found on 'lees verder' page: {lv_url}")
                    
                    # Clean up the content (but preserve headers)
                    content = re.sub(r'\[|\]|\*|_', '', content)
                    content = re.sub(r'\n{3,}', '\n\n', content)
                    content = re.sub(r'Bedankt! We hebben uw feedback ontvangen\..*$', '', content, flags=re.DOTALL)
                    content = '\n'.join(line.lstrip() for line in content.split('\n'))
                    content = content.strip()
                    
                    # Skip empty content
                    if not content.strip():
                        logger.warning(f"No content found on 'lees verder' page: {lv_url}")
                        await lv_page.close()
                        continue
                    
                    # Save to a separate file
                    lv_temp_filename = f"temp/belastingdienst_lees_verder_temp_{len(self.scraped_urls)}.txt"
                    with open(lv_temp_filename, "w", encoding="utf-8") as f:
                        f.write(f"Year: [2023, 2024, 2025]\n")
                        f.write(f"Title: {lv_title}\n")
                        f.write(f"Source: {Source.BELASTINGDIENST.value}\n")
                        f.write(f"Data Category: {DataCategory.PRIMAIRE.value}\n")
                        f.write(f"URL: {lv_url}\n")
                        f.write(f"Scraped at: {datetime.now().isoformat()}\n")
                        f.write(f"Content:\n{content}")
                    
                    # Upload to blob storage
                    self.storage_client.upload_blob(lv_blob_name, lv_temp_filename)
                    
                    # Mark as scraped
                    self.scraped_urls.add(lv_url)
                    self.processed_count += 1
                    self.lees_verder_count += 1  # Track lees verder count separately
                    
                    # Clean up temporary file
                    os.remove(lv_temp_filename)
                    logger.info(f"Successfully scraped and saved 'lees verder' content: {lv_title} ({lv_url})")
                    
                    # Check for nested "lees verder" links to handle recursive content
                    await self._handle_lees_verder_links(lv_page, lv_url)
                
                except TimeoutError:
                    logger.warning(f"Timeout while loading 'lees verder' page: {lv_url}")
                except Exception as e:
                    logger.error(f"Error scraping 'lees verder' page {lv_url}: {str(e)}")
                finally:
                    await lv_page.close()
            
            except Exception as e:
                logger.error(f"Error processing 'lees verder' element on {parent_url}: {str(e)}") 