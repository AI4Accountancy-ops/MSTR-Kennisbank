import asyncio
import os
import re
import tempfile
from datetime import datetime

import aiohttp
from playwright.async_api import async_playwright
from pymupdf4llm import to_markdown

from definitions.enums import DataCategory, Source
from definitions.paths import Paths
from logger.logger import Logger
from cloud.storage import AzureStorageClient

logger = Logger.get_logger(__name__)

BASE_URL = "https://www.belastingdienst.nl"
BROCHURE_URL = "https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/themaoverstijgend/brochures_en_publicaties/brochures_en_publicaties_ondernemer"

# Years to scrape
YEARS_TO_SCRAPE = ["2023", "2024", "2025"]


class BrochureScraper:
    def __init__(self):
        # Initialize storage client for uploading files
        self.storage_client = AzureStorageClient()
        
        # Folder structure
        self.paths = Paths()
        self.output_folder = self.paths.scraped_documents
        self.belastingdienst_folder = Source.BELASTINGDIENST.value
        
        # Track statistics
        self.total_docs_processed = 0
        self.total_docs_uploaded = 0

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

    async def fetch_brochure_links(self, year):
        """Uses Playwright to extract brochure links for a specific year."""
        logger.info(f"Starting Playwright browser for year {year}...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            logger.info(f"Navigating to {BROCHURE_URL}")
            await page.goto(BROCHURE_URL)

            # Select "Alle" for Onderwerp
            logger.info("Selecting 'Alle' from Onderwerp dropdown...")
            await page.select_option("#selOnderwerp", "", timeout=60000)  # 60 second timeout

            # Select the specific year
            logger.info(f"Selecting year {year} from Belastingjaar dropdown...")
            await page.select_option("#selBelastingjaar", year, timeout=60000)  # 60 second timeout

            # Wait for results to load
            logger.info("Waiting for results to load...")
            await page.wait_for_selector("#ovz_result li a", timeout=60000)  # 60 second timeout

            # Extract all links and titles from the results
            results = await page.evaluate("""
                () => {
                    const items = Array.from(document.querySelectorAll('#ovz_result li'));
                    return items.map(item => {
                        const linkElement = item.querySelector('a.results-list__title');
                        const metaElement = item.querySelector('.results-list__meta');
                        return {
                            title: linkElement ? linkElement.textContent.trim() : null,
                            url: linkElement ? linkElement.href : null,
                            year: metaElement ? metaElement.textContent.trim() : null
                        };
                    });
                }
            """)

            # Filter out any items with missing URLs
            valid_results = [r for r in results if r["url"]]
            
            logger.info(f"Extracted {len(valid_results)} brochure links for year {year}:")
            for result in valid_results:
                logger.info(f"Title: {result['title']}, URL: {result['url']}")

            await browser.close()
            logger.info(f"Browser closed for year {year}.")

        return valid_results

    async def fetch_pdfs_from_url(self, brochure_info):
        """Visits a brochure URL, extracts PDF links and titles, then processes them."""
        url = brochure_info["url"]
        brochure_title = brochure_info["title"]
        search_year = brochure_info["year"]
        
        logger.info(f"Visiting URL: {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.goto(url)

            # Wait for PDF links to appear
            await page.wait_for_selector("a.bldc-file-block.bldc-icon-document.form-control", timeout=5000)

            # Extract PDF links, titles and any year information
            pdf_data = await page.evaluate(
                r"""() => {
                    return Array.from(document.querySelectorAll("a.bldc-file-block.bldc-icon-document.form-control"))
                        .map(a => {
                            const titleElement = a.querySelector(".bldc-file-name");
                            const title = titleElement ? titleElement.innerText.trim() : "Unknown";
                            
                            // Extract filename from URL or span
                            let filename = "";
                            const filenameSrOnly = a.parentElement.querySelector("span.sr-only");
                            if (filenameSrOnly) {
                                const match = filenameSrOnly.innerText.match(/Opties van bestand ([^\\.]+\\.pdf)/);
                                if (match) {
                                    filename = match[1];
                                }
                            }
                            
                            // If no filename found, try to extract from href
                            if (!filename && a.href) {
                                const urlParts = a.href.split('/');
                                if (urlParts.length > 0) {
                                    filename = urlParts[urlParts.length - 1];
                                }
                            }
                            
                            return {
                                url: a.href.startsWith("http") ? a.href : "https:" + a.href,
                                title: title,
                                filename: filename
                            };
                        });
                }"""
            )

            logger.info(f"Found {len(pdf_data)} PDF(s) at {url}")

            # Convert PDFs to text if they have the right years
            for pdf_info in pdf_data:
                # Check if this is a document we want to process
                pdf_year = self.extract_year_from_text(pdf_info["title"])
                if not pdf_year and pdf_info["filename"]:
                    pdf_year = self.extract_year_from_text(pdf_info["filename"])
                
                # Only process PDFs with years 2023, 2024, or 2025
                if pdf_year in YEARS_TO_SCRAPE:
                    await self.convert_pdf_to_text(pdf_info["url"], pdf_info["title"], 
                                                 pdf_info["filename"], brochure_title)
                else:
                    logger.info(f"Skipping PDF: {pdf_info['title']} - Year {pdf_year or 'unknown'} not in target years")

            await browser.close()

    def extract_year_from_text(self, text):
        """Extracts year (2023, 2024, 2025) from text if present."""
        for year in YEARS_TO_SCRAPE:
            if year in text:
                return year
        
        # If no specific year found, search for 4-digit numbers that could be years
        year_match = re.search(r'20\d{2}', text)
        if year_match:
            return year_match.group(0)
            
        return None

    async def convert_pdf_to_text(self, pdf_url, pdf_title, filename, brochure_title):
        """Streams a PDF from a URL, converts it to text, and uploads to blob storage."""
        safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in pdf_title).strip()

        logger.info(f"Streaming and converting PDF: {pdf_url} to text...")
        self.total_docs_processed += 1
        
        # Extract year from title or filename
        year = self.extract_year_from_text(pdf_title)
        if not year and filename:
            year = self.extract_year_from_text(filename)
            
        # If still no year found or not in our target years, skip
        if not year or year not in YEARS_TO_SCRAPE:
            logger.info(f"Skipping PDF with year {year or 'unknown'}: {pdf_title}")
            return

        logger.info(f"Processing document with year {year}: {pdf_title}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    if response.status == 200:
                        pdf_bytes = await response.read()  # Get PDF as bytes

                        # Save to a temporary file before converting
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                            temp_pdf.write(pdf_bytes)
                            temp_pdf_path = temp_pdf.name

                        # Convert the temporary PDF to Markdown
                        markdown_text = to_markdown(temp_pdf_path)

                        # Clean the extracted Markdown text
                        cleaned_text = self.clean_markdown(markdown_text)

                        # Create a temp file for the text content
                        temp_filename = f"temp/belastingdienst_brochure_temp.txt"
                        os.makedirs("temp", exist_ok=True)
                        
                        # Save the cleaned text with metadata to the temp file
                        with open(temp_filename, "w", encoding="utf-8") as f:
                            f.write(f"Year: [{year}]\n")
                            f.write(f"Title: {pdf_title}\n")
                            f.write(f"Source: {Source.BELASTINGDIENST.value}\n")
                            f.write(f"Data Category: {DataCategory.PRIMAIRE.value}\n")
                            f.write(f"URL: {pdf_url}\n")
                            f.write(f"Scraped at: {datetime.now().isoformat()}\n")
                            f.write(f"Content:\n{cleaned_text}")

                        # Upload to blob storage
                        blob_name = self._get_blob_name_for_url(pdf_url, safe_title)
                        self.storage_client.upload_blob(blob_name, temp_filename)
                        
                        # Mark as uploaded
                        self.total_docs_uploaded += 1
                        logger.info(f"Successfully uploaded to blob storage: {blob_name}")
                        
                        # Clean up temporary files
                        os.remove(temp_pdf_path)
                        os.remove(temp_filename)

                    else:
                        logger.error(f"Failed to fetch {pdf_url}, status code: {response.status}")

        except Exception as e:
            logger.error(f"Error converting {pdf_url} to text: {e}")

    def _get_blob_name_for_url(self, url: str, title: str) -> str:
        """Generate a blob name based on URL and title."""
        # For PDFs, using title as base for filename is better than the URL
        # since the URL might be generic or have a random ID
        if title:
            # Clean up the title to make it suitable for a filename
            sanitized = re.sub(r'[\\/*?:"<>|]', '_', title)
            # Replace spaces with underscores
            sanitized = sanitized.replace(' ', '_')
            # Remove multiple underscores
            sanitized = re.sub(r'_+', '_', sanitized)
            # Ensure it's not too long
            if len(sanitized) > 200:
                sanitized = sanitized[:200]
            # Add .txt extension
            if not sanitized.endswith('.txt'):
                sanitized += '.txt'
            return f"{self.belastingdienst_folder}/{sanitized}"
        else:
            # Fallback to URL-based filename
            return f"{self.belastingdienst_folder}/{self.get_filename_from_url(url)}"

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

    def clean_markdown(self, markdown_content: str) -> str:
        """Cleans up extracted Markdown text by adding page numbers and removing unnecessary characters."""
        logger.info("Cleaning extracted Markdown content...")

        # Replace "-----" page boundaries with numbered page markers
        markdown_content = self._add_page_numbers_to_content(markdown_content)

        # Remove "**" (two consecutive asterisks)
        markdown_content = re.sub(r'\*\*+', '', markdown_content)

        # Remove excessive newlines (more than 2) but preserve paragraph breaks
        # This will keep paragraph breaks (\n\n) intact while removing excessive breaks
        markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content).strip()

        return markdown_content

    async def scrape_year(self, year):
        """Scrapes all brochures for a specific year."""
        logger.info(f"Starting scraping process for year {year}...")
        
        try:
            # Fetch all brochure links for the year
            brochure_links = await self.fetch_brochure_links(year)
            
            # Process each brochure link
            for brochure_info in brochure_links:
                await self.fetch_pdfs_from_url(brochure_info)
                
            logger.info(f"Completed scraping for year {year}")
            
        except Exception as e:
            logger.error(f"Error scraping year {year}: {e}")

    async def scrape_brochures_async(self):
        """Asynchronous version of scrape_brochures to be awaited in an existing event loop."""
        logger.info("Starting the brochure scraping process for all years...")
        
        try:
            # Create tasks for each year
            tasks = []
            for year in YEARS_TO_SCRAPE:
                task = self.scrape_year(year)
                tasks.append(task)
            
            # Run all tasks concurrently
            await asyncio.gather(*tasks)
            
            logger.info(f"Brochure scraping completed successfully for all years.")
            logger.info(f"Total documents processed: {self.total_docs_processed}")
            logger.info(f"Total documents uploaded to blob storage: {self.total_docs_uploaded}")
            
        except Exception as e:
            logger.error(f"An error occurred during scraping: {e}")

    def scrape_brochures(self):
        """Entry point for extracting and converting brochure PDFs for all years."""
        try:
            # Use get_event_loop instead of creating a new one
            loop = asyncio.get_event_loop()
            
            # Run the async method with the existing event loop
            loop.run_until_complete(self.scrape_brochures_async())
            
        except RuntimeError as e:
            # If we're already in an event loop, use create_task instead
            if "This event loop is already running" in str(e):
                logger.info("Using existing event loop for brochure scraping")
                asyncio.create_task(self.scrape_brochures_async())
            else:
                # Re-raise other RuntimeErrors
                raise
