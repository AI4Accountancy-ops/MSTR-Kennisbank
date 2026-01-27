import os
import re

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from definitions.enums import FiscalTopic, DataCategory, Source
from definitions.paths import Paths
from logger.logger import Logger

logger = Logger.get_logger(__name__)


class MFASScraper:
    def __init__(self, fiscal_topic: FiscalTopic):
        # Initialize fiscal topic
        self.fiscal_topic = fiscal_topic

        # Initialize adviesteksten_type
        if self.fiscal_topic == FiscalTopic.OB.value:
            self.adviesteksten_type = [
                "12.%20Omzetbelasting"
            ]
        elif self.fiscal_topic == FiscalTopic.IB.value:
            self.adviesteksten_type = [
                "03.%20Eigen%20woning",
                "06.%20Inkomstenbelasting%20-%20beleggen",
                "07.%20Inkomstenbelasting%20-%20varia",
                "05.%20IB-onderneming",
                "11.%20Auto",
                "14.%20Belastingcontrole%20en%20fiscaal%20strafrecht",
                "17.%20Diversen",
                "18.%20Toeslagen"
            ]
        elif self.fiscal_topic == FiscalTopic.VPB.value:
            self.adviesteksten_type = [
                "01.%20Familievennootschappen%20-%20dga",
                "02.%20Vennootschapsbelasting",
                "11.%20Auto",
                "14.%20Belastingcontrole%20en%20fiscaal%20strafrecht"
            ]

        # Folder structure
        self.paths = Paths()
        self.output_folder = self.paths.scraped_documents
        self.data_category = DataCategory.PRAKTISCH_ADVIES.value
        self.mfas_folder = Source.MFAS.value

        self.base_url = "https://mfas.nl"
        self.login_url = "https://mfas.nl/wps/portal/h/login/"
        self.paths = Paths()
        self.output_folder = self.paths.scraped_documents
        # Store your cookies so they can be re-added for each context.
        self.cookies = [
            {
                "name": "JSESSIONID",
                "value": "put real value here",
                "domain": "mfas.nl",
                "path": "/",
                "httpOnly": True,
                "secure": True
            },
            {
                "name": "SSOToken",
                "value": "put real value here",
                "domain": "mfas.nl",
                "path": "/",
                "httpOnly": True,
                "secure": True
            }
        ]
        # We'll store the browser instance here to use it for new contexts.
        self.browser = None

    async def scrape_mfas_docs(self) -> None:
        async with async_playwright() as p:
            # Launch browser in headless mode and store it in self.browser
            self.browser = await p.chromium.launch(headless=True)
            # Create an initial context to scrape the main page
            main_context = await self.browser.new_context()
            await main_context.add_cookies(self.cookies)
            page = await main_context.new_page()

            # Loop over each adviesteksten type and build its target URL
            for adv in self.adviesteksten_type:
                # Navigate to the target URL
                target_url = f"https://mfas.nl/wps/myportal/home/mfas/modules/Adviesteksten/{adv}/"
                await page.goto(target_url)
                await page.wait_for_selector("ul#bap_nav_display", timeout=600000)

                # Extract all folder links
                links = page.locator("ul#bap_nav_display li a")
                count = await links.count()
                for i in range(count):
                    href = await links.nth(i).get_attribute("href")
                    if href:
                        full_url = self.base_url + href
                        # For each folder URL, create a fresh context
                        await self.scrape_articles_in_folder(full_url)

            # Clean up
            await main_context.close()
            await self.browser.close()

    async def scrape_articles_in_folder(self, folder_url: str) -> None:
        # Create a new browser context for this folder
        folder_context = await self.browser.new_context()
        await folder_context.add_cookies(self.cookies)
        page = await folder_context.new_page()
        try:
            await page.goto(folder_url)
        except Exception as e:
            logger.error(f"Failed to load folder {folder_url}: {e}")
            await folder_context.close()
            return

        # Extract folder name for output folder
        folder_name = folder_url.split("/")[-2].replace("+", "-").replace("%20", "-")
        folder_path = os.path.join(f'{self.output_folder}/{self.fiscal_topic}/{self.data_category}/{self.mfas_folder}', folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Wait for the articles list to load; if the primary selector fails,
        # you can use your polling method or alternative selectors here.
        element = await page.wait_for_selector("ul#bap_nav_display", timeout=60000)
        if not element:
            logger.error(f"List not found for folder {folder_url}. Skipping this folder.")
            await folder_context.close()
            return

        # Process all links in the folder
        visited_urls = set()  # to avoid duplicates
        article_links = page.locator("ul#bap_nav_display li a")
        count = await article_links.count()
        for i in range(count):
            href = await article_links.nth(i).get_attribute("href")
            if href:
                full_url = self.base_url + href
                if "WCM_Page.ResetAll=TRUE" in href:
                    continue
                if full_url not in visited_urls:
                    visited_urls.add(full_url)
                    if "?pagedesign" in href:
                        logger.info(f"Found URL: {full_url}")  # It's a folder link
                    else:
                        logger.info(f"Found article URL: {full_url}")
                        await self.scrape_article_content(full_url, folder_path)

        await folder_context.close()

    async def scrape_article_content(self, article_url: str, folder_path: str) -> None:
        # Create a fresh context for each article if desired, or reuse the folder context
        # (here we simply create a new page using the main browser)
        article_context = await self.browser.new_context()
        await article_context.add_cookies(self.cookies)
        page = await article_context.new_page()
        try:
            await page.goto(article_url)
            await page.wait_for_load_state('networkidle', timeout=20000)
        except Exception as e:
            logger.error(f"Failed to load article {article_url}: {e}")
            await article_context.close()
            return

        # Check for the content element
        content_locator = page.locator("#printContent")
        if await content_locator.count() == 0:
            logger.error(f"Content not found for article {article_url}. Skipping.")
            await article_context.close()
            return

        raw_html = await content_locator.inner_html()
        cleaned_text = self.clean_content(raw_html, article_url)

        # Get the title from within the content
        title_locator = page.locator("#printContent .content-to-index h1")
        if await title_locator.count() == 0:
            logger.error(f"Title not found for article {article_url}. Skipping.")
            await article_context.close()
            return

        h1_tag = await title_locator.first.inner_text()

        def sanitize_filename(name: str) -> str:
            return re.sub(r"[<>:\"/\\|?*\n\r\t]", "_", name).strip("_")

        file_name = sanitize_filename(h1_tag) + ".txt"
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
        logger.info(f"Saved article content to {file_path}")

        await article_context.close()

    def clean_content(self, content: str, article_url: str) -> str:
        # Step 1: Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')

        # Step 2: Define a helper function to process unordered and ordered lists
        def process_list(tag):
            items = []
            for li in tag.find_all("li", recursive=False):
                text = li.get_text(separator=" ", strip=True)
                sublist = li.find(["ul", "ol"])
                if sublist:
                    text += "\n" + process_list(sublist)
                items.append(text)

            if tag.name == "ul":
                return "\n".join(f"- {item}" for item in items)
            elif tag.name == "ol":
                return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
            return ""

        # Step 3: Replace all <ul> and <ol> tags with their processed plain text equivalents
        for ul in soup.find_all("ul"):
            ul.replace_with(process_list(ul))

        for ol in soup.find_all("ol"):
            ol.replace_with(process_list(ol))

        # Step 4: Extract and clean the plain text from the modified HTML
        plain_text = soup.get_text()
        cleaned_text = "\n".join(line.strip() for line in plain_text.splitlines() if line.strip())

        # Step 5: Combine the article URL with the cleaned text and return the result
        return f'URL: "{article_url}"\n{cleaned_text}'
