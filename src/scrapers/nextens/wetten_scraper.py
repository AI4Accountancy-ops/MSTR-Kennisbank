import re
import os
from datetime import datetime
from bs4 import BeautifulSoup

import html2text

from playwright.sync_api import (
    Page,
    sync_playwright,
)

from cloud.storage import AzureStorageClient
from definitions.enums import DataCategory, Source
from definitions.paths import Paths
from logger.logger import Logger

logger = Logger.get_logger(__name__)
html2md = html2text.HTML2Text()
html2md.ignore_links = True  # We strip out links in Markdown output


class WettenScraper:
    def __init__(self):
        # Initialize fiscal topic
        self.links_file = 'Links.txt'
        self.wetten_urls = self.load_urls()

        # Folder structure
        self.paths = Paths()
        self.output_folder = self.paths.scraped_documents
        self.data_category = DataCategory.PRIMAIRE.value
        self.wetten_folder = Source.WETTEN_OVERHEID.value
        self.base_url = "https://wetten.overheid.nl/"
        
        # Initialize storage client for uploading files
        self.storage_client = AzureStorageClient()
        
        # Track statistics
        self.total_docs_processed = 0
        self.total_docs_uploaded = 0

        self.context = None

    def load_urls(self):
        with open(self.links_file, 'r') as file:
            lines = file.readlines()
            lines = [line.strip() for line in lines]  # Removes newline characters
        return lines

    def clean_markdown_formatting(self, text: str) -> str:
        lines = text.splitlines()
        adjusted_lines = []
        prev_line = ""

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Remove blank lines between bullet items
            if not stripped:
                if prev_line.strip().startswith("-"):
                    # Peek ahead: if next line is also a bullet, skip this blank line
                    if i + 1 < len(lines) and lines[i + 1].strip().startswith("-"):
                        continue
                if adjusted_lines and adjusted_lines[-1] != "":
                    adjusted_lines.append("")
                prev_line = line
                continue

            adjusted_lines.append(stripped)
            prev_line = line

        return "\n".join(adjusted_lines)

    def sanitize_filename(self, title: str) -> str:
        import re
        import unicodedata

        # Normalize unicode but keep base letters
        title = unicodedata.normalize("NFKC", title)

        # Remove soft hyphens and control characters
        title = re.sub(r'[\u00AD\u200B\r\n\t]', ' ', title)

        # Replace all dash variants with plain hyphen
        title = re.sub(r'[‐‑–—]', '-', title)

        # Replace invalid filename characters with underscore
        title = re.sub(r'[<>:"/\\|?*]', '_', title)

        # Collapse multiple dashes/underscores/spaces
        title = re.sub(r'[\s_-]+', '_', title)

        # Strip leading/trailing junk
        return title.strip('_ ')

    def format_year(self, text: str) -> list[int]:
        """
        Extracts a 'Geldend van ... t/m ...' date range from text and returns a list of active years.
        Examples: 
        - "Geldend van 18-07-2007 t/m heden" => [2007, 2008, ..., 2025]
        - "Geldend van 15-03-2025 t/m 18-07-2025" => [2025]
        """
        # Pattern for "t/m heden" (until present)
        match_heden = re.search(r"Geldend van \d{2}-\d{2}-(\d{4}) t/m heden", text)
        if match_heden:
            start_year = int(match_heden.group(1))
            end_year = datetime.now().year
            return list(range(start_year, end_year + 1))
        
        # Pattern for specific end date "t/m DD-MM-YYYY"
        match_specific = re.search(r"Geldend van \d{2}-\d{2}-(\d{4}) t/m \d{2}-\d{2}-(\d{4})", text)
        if match_specific:
            start_year = int(match_specific.group(1))
            end_year = int(match_specific.group(2))
            return list(range(start_year, end_year + 1))
        
        return []

    def scrape_urls(self, page: Page):
        """
        1) Navigate to https://wetten.overheid.nl/
        2) Find the "content" div
        3) Extract the contents of the content div
        """
        try:
            # Step 1: Go to main page
            for link in self.wetten_urls:
                wetten_url = f"{self.base_url}/{link}"
                page.goto(wetten_url, wait_until="networkidle")
                logger.info("Page loaded successfully.")

                page.wait_for_selector("#regeling", timeout=150000)
                logger.info("Page content found.")

                #Step 2: Extract page title
                title = page.locator("#regeling h1").first.text_content()
                logger.info(f"Page Title:{title}")

                #Step 3: Extract year
                year_info = page.locator("p.regeling-toestand-meldingen").text_content()
                formatted_year = self.format_year(year_info)
                logger.info(f"Year:{formatted_year}")

                #Step 4: Extract website content
                content = self.extract_page_content(page)

                #Construct a safe filename
                safe_filename = re.sub(r'[\\/*?:"<>|]', "-", title).strip()
                sanitized_filename = self.sanitize_filename(safe_filename)
                logger.info(f"Sanitized File Name:{sanitized_filename}")

                txt_filename = f"{sanitized_filename}.txt"
                
                # Create the formatted content with metadata
                formatted_content = ""
                formatted_content += f"Year: {formatted_year}\n"
                formatted_content += f"Title: {title}\n"
                formatted_content += f"Source: {Source.WETTEN_OVERHEID.value}\n"
                formatted_content += f"Data Category: {DataCategory.PRIMAIRE.value}\n"
                formatted_content += f"URL: {wetten_url}\n"
                formatted_content += f"Scraped at: {datetime.now().isoformat()}\n"
                formatted_content += f"Content:\n{self.fix_missing_list_breaks(self.clean_markdown_formatting(content))}"
                
                # Update metrics
                self.total_docs_processed += 1
                
                # Upload to Azure Storage
                if self.storage_client:
                    blob_name = f"{self.wetten_folder}/{sanitized_filename}.txt"
                    self.storage_client.upload_text_as_blob(blob_name, formatted_content)
                    self.total_docs_uploaded += 1
                    doc_size = len(formatted_content)
                    logger.info(f"Uploaded document to Azure Storage: {blob_name} ({doc_size} bytes)")
                else:
                    # Fallback to local storage if storage client is not available
                    file_path = os.path.join(f'{self.output_folder}/{self.data_category}/{self.wetten_folder}', txt_filename)
                    logger.info(f"Sanitized File Name:{txt_filename}")
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(formatted_content)
                    logger.info(f"Saved to {file_path}")
                    logger.info(f"Saved to {os.path.abspath(file_path)}")
        except Exception as e:
            logger.error(f"Error while scraping chapter content for {title}: {e}")
            logger.exception(e)  # Print full stack trace

        finally:
            page.close()

    def fix_missing_list_breaks(self, markdown: str) -> str:
        lines = markdown.splitlines()
        adjusted = []

        for i in range(len(lines)):
            current = lines[i].strip()
            adjusted.append(current)

            if i + 1 >= len(lines):
                break

            next_line = lines[i + 1].strip()

            # Pattern matches
            is_top_level_number = re.match(r"- \d+(?!°)", current)
            is_next_top_level_number = re.match(r"- \d+(?!°)", next_line)

            is_sub_bullet = re.match(r"- [a-zA-Z]\.", current)
            is_next_top_level_number = re.match(r"- \d+(?!°)", next_line)

            is_degree_bullet = re.match(r"- \d+°\.?", current)
            is_next_degree = re.match(r"- \d+°\.?", next_line)

            # Insert line break between top-level number bullets (e.g., - 1 ➝ - 2)
            if is_top_level_number and is_next_top_level_number:
                adjusted.append("")

            # Insert line break between sub-bullet and new top-level number (e.g., - b. ➝ - 3)
            elif is_sub_bullet and is_next_top_level_number:
                adjusted.append("")

            # Insert line break between last degree item and a *new* top-level section
            elif is_degree_bullet and not is_next_degree and re.match(r"- \d+(?!°)|#{1,3}|Artikel", next_line):
                adjusted.append("")

        return "\n".join(adjusted)

    def extract_page_content(self, page: Page) -> str:
        try:
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            content_div = soup.find("div", class_=["wettekst", "regeling", "wetgeving"])

            if not content_div:
                return ""
            "bijlage", "origineel-opschrift-en-aanhef"
            for bijlage in content_div.find_all("div", class_=["bijlage", "origineel-opschrift-en-aanhef", "slotformulier-en-ondertekening", "origineel-opschrift-en-aanhef"]):
                bijlage.decompose()

            # Remove UI junk <ul role="list" ...>
            for junk_ul in content_div.find_all("ul", {"role": "list"}):
                aria_label = junk_ul.get("aria-label", "").lower()
                if "mogelijk" in aria_label or "acties" in aria_label:
                    junk_ul.decompose()

            # Unwrap all <a> tags
            for a in content_div.find_all("a"):
                a.unwrap()

            # Convert to markdown
            h = html2text.HTML2Text()
            h.ignore_links = True  # Don't show URLs
            h.ignore_images = True
            h.ignore_tables = False
            h.body_width = 0  # No wrapping
            h.ignore_emphasis = False  # Preserve emphasis and headers
            h.unicode_snob = True  # Use unicode characters
            h.ul_item_mark = ''  # No bullet points

            markdown = h.handle(str(content_div)).strip()

            # Cleanup extra spacing but preserve headers
            markdown = re.sub(r'\n{3,}', '\n\n', markdown)

            return markdown.strip()

        except Exception as e:
            logger.error(f"Error extracting article content: {e}")
            return ""

    def close(self):
        """Close the browser context."""
        if self.context:
            self.context.close()
            logger.info("Browser context closed.")

    def scrape_wetten_docs(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context()
                page = context.new_page()
                self.scrape_urls(page)
                logger.info(f"Scraping completed! Processed {self.total_docs_processed} documents and uploaded {self.total_docs_uploaded} to Azure Storage.")
            finally:
                browser.close()

if __name__ == "__main__":
    """
    Main entry point for testing the WettenScraper directly.
    Run this file directly to start scraping wetten.
    """
    try:
        logger.info("Starting Wetten scraper...")
        scraper = WettenScraper()
        scraper.scrape_wetten_docs()
        logger.info("Wetten scraping completed successfully!")
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}", exc_info=True)
