import os
import re
from urllib.parse import urljoin

import html2text
from playwright.sync_api import sync_playwright

import definitions.names as n
from definitions.credentials import Credentials
from definitions.enums import FiscalTopic, DataCategory, Source
from definitions.paths import Paths
from logger.logger import Logger

logger = Logger.get_logger(__name__)


class IndicatorScraper:
    def __init__(self, fiscal_topic: FiscalTopic):
        # Initialize fiscal topic
        self.fiscal_topic = fiscal_topic

        # Folder structure
        self.paths = Paths()
        self.output_folder = self.paths.scraped_documents
        self.data_category = DataCategory.PRAKTISCH_ADVIES.value
        self.indicator_folder = Source.INDICATOR.value

        # Credentials
        self.username = Credentials.get_scraping_credentials().get(n.INDICATOR_USERNAME)
        self.password = Credentials.get_scraping_credentials().get(n.INDICATOR_PASSWORD)

        # Configure html2text
        self.html2markdown = html2text.HTML2Text()
        self.html2markdown.ignore_links = True
        self.html2markdown.body_width = 0

    def parse_year_from_metadata(self, metadata_text: str) -> int:
        """
        Extracts a 4-digit year from a string like: "Datum: 10.01.2025".
        Returns int or None if not found.
        """
        match = re.search(r'\b(\d{4})\b', metadata_text)
        if match:
            return int(match.group(1))
        return None

    def sanitize_filename(self, filename: str, max_length: int = 100) -> str:
        """
        Remove invalid characters for most filesystems and limit length.
        """
        filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
        if len(filename) > max_length:
            filename = filename[:max_length].rstrip()
        return filename

    def scrape_detail_page(self, page, detail_url: str) -> dict:
        """
        Navigate to detail_url in the same page, then:
          - Grab the h1.title from anywhere on the page (outside artBox)
          - Remove #relDocs, #comments, #bottomArt from within #box10.art-box-contentv2
          - Extract <div class="conclusion"> separately
          - Return article_html (intro + in-between paragraphs), conclusion_html, and detail_title.
        """
        page.goto(detail_url)

        # Wait for some main element to indicate the article is loaded
        page.wait_for_selector("div.artBox", timeout=5000)

        # 1) Grab <h1 class="title"> from the entire page
        h1_el = page.query_selector("h1.title")
        detail_title = h1_el.inner_text().strip() if h1_el else "article"

        # 2) Grab the container for the main text
        container = page.query_selector("div#box10.art-box-contentv2")
        if not container:
            return {
                "article_html": "",
                "conclusion_html": "",
                "detail_title": detail_title
            }

        # 3) Remove #relDocs (Aanverwante documenten) if present
        rel_docs = container.query_selector("#relDocs")
        remove_element = "(elem) => elem.remove()"

        if rel_docs:
            page.evaluate(remove_element, rel_docs)

        # 4) Remove #comments (Reacties/Geef uw reactie) if present
        comments_section = container.query_selector("#comments")
        if comments_section:
            page.evaluate(remove_element, comments_section)

        # 5) Remove #bottomArt (subscription / recommend block, etc.) if present
        bottom_art = container.query_selector("#bottomArt")
        if bottom_art:
            page.evaluate(remove_element, bottom_art)

        # 6) Extract and remove .conclusion if present
        conclusion_el = container.query_selector("div.conclusion")
        conclusion_html = conclusion_el.inner_html() if conclusion_el else ""
        if conclusion_el:
            page.evaluate(remove_element, conclusion_el)

        # 7) The container now holds the main article (including articleIntro, paragraphs, subtitles)
        article_html = container.inner_html()

        return {
            "article_html": article_html,
            "conclusion_html": conclusion_html,
            "detail_title": detail_title
        }

    def login(self, page) -> None:
        """
        Logs into the website using credentials.
        """
        page.goto("https://ondernemingsdatabank.indicator.nl/login/")
        page.wait_for_selector("#username", state="visible", timeout=60000)
        page.fill("#username", self.username)
        page.wait_for_selector("#password", state="visible", timeout=60000)
        page.fill("#password", self.password)
        with page.expect_navigation():
            page.click("#login")
        logger.info("Login successful!")

    def fetch_search_results(self, page, current_page: int) -> list:
        """
        Navigates to the search results page and retrieves result items.
        """
        offset = 0 if current_page == 1 else current_page
        search_url = (
            "https://ondernemingsdatabank.indicator.nl/search"
            f"?offset={offset}&orderBy=dat&nrOfResults=&sd=&ed=&exact=&domstring=1"
        )
        page.goto(search_url)
        items = page.query_selector_all(".resultItem")
        if not items:
            logger.info(f"No results found on page {current_page}. Stopping.")
        return items

    def fetch_search_results_auto(self, page, current_page: int) -> list:
        """
        Navigates to the search results page for the 'auto' workflow
        and retrieves result items using the alternate URL.
        """
        offset = 0 if current_page == 1 else current_page
        search_url = (
            "https://ondernemingsdatabank.indicator.nl/search"
            f"?offset={offset}&orderBy=dat&domid=85"
        )
        page.goto(search_url)
        items = page.query_selector_all(".resultItem")
        if not items:
            logger.info(f"No results found on page {current_page}. Stopping.")
        return items

    def fetch_search_results_bv_dga(self, page, current_page: int) -> list:
        """
        Navigates to the search results page for the 'BV en dga' workflow
        and retrieves result items using the alternate URL.
        """
        offset = 0 if current_page == 1 else current_page
        search_url = (
            "https://ondernemingsdatabank.indicator.nl/search"
            f"?&offset={offset}&orderBy=dat&domid=58"
        )
        page.goto(search_url)
        items = page.query_selector_all(".resultItem")
        if not items:
            logger.info(f"No results found on page {current_page}. Stopping.")
        return items

    def process_search_results(self, items, details_to_scrape: list, stop_scraping: bool) -> bool:
        """
        Processes the search result items to extract detail URLs.
        """
        for item in items:
            date_el = item.query_selector(".metadata")
            if not date_el:
                continue
            date_text = date_el.inner_text().strip()
            year = self.parse_year_from_metadata(date_text)

            # Stop scraping if year < 2023
            if year and year < 2023:
                return True

            # Extract detail link if year >= 2023
            if year and year >= 2023:
                link_el = item.query_selector("h2 a")
                if not link_el:
                    continue
                relative_link = link_el.get_attribute("href")
                full_url = urljoin("https://ondernemingsdatabank.indicator.nl", relative_link)
                details_to_scrape.append(full_url)

        return stop_scraping

    def process_detail_pages(self, page, details_to_scrape: list, saved_count: int) -> int:
        """
        Processes the detail pages and saves their content.
        """
        for detail_url in details_to_scrape:
            detail_data = self.scrape_detail_page(page, detail_url)

            # Combine article_html + conclusion_html
            combined_html = detail_data["article_html"] + "\n" + detail_data["conclusion_html"]

            # Convert HTML => Markdown
            markdown_content = self.html2markdown.handle(combined_html)
            cleaned_content = re.sub(r"\n+", "\n", markdown_content).strip()

            # Use <h1 class="title"> text for filename
            raw_title = detail_data["detail_title"]
            safe_title = self.sanitize_filename(raw_title)

            # Prepend URL and raw title to the content
            file_content = f"URL: {detail_url}\n{cleaned_content}\n"

            # Build the output directory
            output_directory = os.path.join(f"{self.output_folder}/{self.fiscal_topic}/{self.data_category}/{self.indicator_folder}")
            os.makedirs(output_directory, exist_ok=True)

            # Build the initial file path
            file_name = f"{safe_title}.txt"
            file_path = os.path.join(str(output_directory), file_name)
            base_name, ext = os.path.splitext(file_name)
            attempt = 1

            # If the file exists, generate a new unique file name
            while os.path.exists(file_path):
                attempt += 1
                file_name = f"{base_name}_{attempt}{ext}"
                file_path = os.path.join(str(output_directory), file_name)

            # Write the content to the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_content)

            saved_count += 1
            logger.info(f"Saved article #{saved_count}: {file_name}")

        return saved_count

    def scrape_belastingen_belastingdienst(self):
        """
        Main scraping workflow.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/114.0.0.0 Safari/537.36")
            )
            page = context.new_page()

            # Login
            self.login(page)

            current_page = 1
            max_pages = 1000 # Increased max pages to 1000
            stop_scraping = False
            saved_count = 0

            while not stop_scraping and current_page <= max_pages:
                # Fetch search results
                items = self.fetch_search_results(page, current_page)
                if not items:
                    break

                # Process search results
                details_to_scrape = []
                stop_scraping = self.process_search_results(items, details_to_scrape, stop_scraping)

                # Process detail pages
                saved_count = self.process_detail_pages(page, details_to_scrape, saved_count)

                current_page += 1

            browser.close()
            logger.info(f"Done! Total articles saved: {saved_count}")

    def scrape_auto(self):
        """
        Main scraping workflow for 'auto' indicator documents.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/114.0.0.0 Safari/537.36")
            )
            page = context.new_page()

            # Login
            self.login(page)

            current_page = 1
            max_pages = 1000
            stop_scraping = False
            saved_count = 0

            while not stop_scraping and current_page <= max_pages:
                # Fetch search results using the alternate (auto) URL
                items = self.fetch_search_results_auto(page, current_page)
                if not items:
                    break

                # Process search results
                details_to_scrape = []
                stop_scraping = self.process_search_results(items, details_to_scrape, stop_scraping)

                # Process detail pages
                saved_count = self.process_detail_pages(page, details_to_scrape, saved_count)

                current_page += 1

            browser.close()
            logger.info(f"Done! Total articles saved: {saved_count}")

    def scrape_bv_dga(self):
        """
        Main scraping workflow for 'BV en dga' indicator documents.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/114.0.0.0 Safari/537.36")
            )
            page = context.new_page()

            # Login
            self.login(page)

            current_page = 1
            max_pages = 1000
            stop_scraping = False
            saved_count = 0

            while not stop_scraping and current_page <= max_pages:
                # Fetch search results using the alternate (auto) URL
                items = self.fetch_search_results_bv_dga(page, current_page)
                if not items:
                    break

                # Process search results
                details_to_scrape = []
                stop_scraping = self.process_search_results(items, details_to_scrape, stop_scraping)

                # Process detail pages
                saved_count = self.process_detail_pages(page, details_to_scrape, saved_count)

                current_page += 1

            browser.close()
            logger.info(f"Done! Total articles saved: {saved_count}")

    def scrape_indicator_docs(self):
        # Scrape specific indicator documents based on selected fiscal topic
        if self.fiscal_topic == FiscalTopic.OB.value:
            self.scrape_belastingen_belastingdienst()
        elif self.fiscal_topic == FiscalTopic.IB.value:
            self.scrape_belastingen_belastingdienst()
            self.scrape_auto()
        elif self.fiscal_topic == FiscalTopic.VPB.value:
            self.scrape_belastingen_belastingdienst()
            self.scrape_auto()
            self.scrape_bv_dga()
