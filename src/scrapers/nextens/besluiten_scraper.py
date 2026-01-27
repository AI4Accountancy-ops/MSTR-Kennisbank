import os
import re
import time
from datetime import datetime

import html2text
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

import definitions.names as n
from definitions.enums import FiscalTopic, DataCategory, Source
from definitions.paths import Paths
from scrapers.nextens.nextens_login import NextensLogin
from logger.logger import Logger

logger = Logger.get_logger(__name__)


class BesluitenScraper:
    def __init__(self, fiscal_topic: FiscalTopic):
        # Initialize fiscal topic
        self.fiscal_topic = fiscal_topic

        # Element identifiers
        if self.fiscal_topic == FiscalTopic.OB.value:
            self.element_identifier = n.OMZETBELASTING
        elif self.fiscal_topic == FiscalTopic.IB.value:
            self.element_identifier = n.INKOMSTENBELASTING
        elif self.fiscal_topic == FiscalTopic.VPB.value:
            self.element_identifier = n.VENNOOTSCHAPSBELASTING

        # Folder structure
        self.paths = Paths()
        self.output_folder = self.paths.scraped_documents
        self.data_category = DataCategory.JURIDISCHE_BEGELEIDING.value
        self.besluiten_folder = Source.NEXTENS_BESLUITEN.value

        self.login = NextensLogin()

        self.converter = html2text.HTML2Text()
        self.converter.ignore_links = True
        self.converter.ignore_images = True
        self.converter.body_width = 0

        # Ensure the output directory exists
        os.makedirs(self.output_folder, exist_ok=True)

        # Initialize the browser context to None
        self.context = None

    def sanitize_filename(self, filename):
        """Sanitize the filename by removing or replacing invalid characters."""
        return re.sub(r'[\\/*?:"<>|]', "_", filename)

    def authenticate(self, browser: Browser) -> Page:
        """Authenticate and return a logged-in page."""
        context = browser.new_context()
        try:
            logger.info("Attempting to authenticate...")
            self.login.authenticate(context)
            logger.info("Authentication successful!")
            # Open a new page in the authenticated context
            page = context.new_page()
            self.context = context  # Store the authenticated context
            return page
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            context.close()
            raise

    def scrape_urls(self, page: Page, max_pages=10):
        """Apply filters and scrape unique URLs from all pages in the overzicht list."""
        all_urls = set()
        try:
            # Navigate to the target URL
            target_url = "https://naslag.nextens.nl/recht/besluiten"
            logger.info(f"Navigating to {target_url}...")
            page.goto(target_url)
            page.wait_for_load_state("networkidle", timeout=150000)

            # Apply "Belastingmiddel" filter
            logger.info("Applying 'Belastingmiddel' filter...")
            belastingmiddel_dropdown = page.locator("span.c-button__text:has-text('Belastingmiddel')")
            if belastingmiddel_dropdown.count() == 0:
                logger.error("'Belastingmiddel' dropdown not found.")
                raise Exception("'Belastingmiddel' dropdown not found.")
            belastingmiddel_dropdown.click()
            page.wait_for_timeout(10000)  # Wait for dropdown to open

            # Select the "element_identifier" checkbox
            logger.info(f"Selecting '{self.element_identifier}' checkbox...")
            label_span = page.locator(f"span.c-checkbox__label:has-text('{self.element_identifier}')")
            if label_span.count() == 0:
                raise Exception(f"'{self.element_identifier}' checkbox label not found.")

            label = label_span.locator("xpath=..")
            if label.count() == 0:
                raise Exception(f"Parent <label> for '{self.element_identifier}' not found.")

            checkbox_input = label.locator("input[type='checkbox']")
            if checkbox_input.count() == 0:
                raise Exception(f"Checkbox input for '{self.element_identifier}' not found.")

            is_checked = checkbox_input.evaluate("element => element.checked")
            if not is_checked:
                label.click()
                page.wait_for_timeout(500)  # Wait briefly for the action to register
                logger.info(f"'{self.element_identifier}' checkbox selected.")
            else:
                logger.info(f"'{self.element_identifier}' checkbox is already selected.")

            # Apply "Publicatiedatum" date range filter
            logger.info("Setting 'Publicatiedatum' date range filter...")
            publicatiedatum_dropdown = page.locator("span.c-button__text:has-text('Publicatiedatum')")
            if publicatiedatum_dropdown.count() == 0:
                logger.error("'Publicatiedatum' dropdown not found.")
                raise Exception("'Publicatiedatum' dropdown not found.")
            publicatiedatum_dropdown.click()
            page.wait_for_timeout(10000)

            # Set 'Vanaf' date
            vanaf_input = page.locator("nextens-input-date[name='fromDate'] input")
            if vanaf_input.count() == 0:
                logger.error("'Vanaf' date input not found.")
                raise Exception("'Vanaf' date input not found.")
            vanaf_date = "01-01-2023"
            vanaf_input.fill(vanaf_date)
            logger.info(f"Set 'Vanaf' date to {vanaf_date}.")

            # Set 't/m' date
            to_date = datetime.today().strftime("%d-%m-%Y")  # e.g., "14-01-2025"
            to_input = page.locator("nextens-input-date[name='toDate'] input")
            if to_input.count() == 0:
                logger.error("'t/m' date input not found.")
                raise Exception("'t/m' date input not found.")
            to_input.fill(to_date)
            logger.info(f"Set 't/m' date to {to_date}.")

            # Click the "Toepassen" (Apply) button to apply the filters
            logger.info("Clicking the 'Toepassen' button to apply filters...")
            toepassen_button = page.locator("button.c-button.primary.small:has-text('Toepassen')")
            if toepassen_button.count() == 0:
                logger.error("'Toepassen' button not found.")
                raise Exception("'Toepassen' button not found.")
            toepassen_button.click()

            # Wait for the overview list to load
            logger.info("Waiting for the overview list to load...")
            page.wait_for_selector("nextens-overview-list", timeout=10000)
            page.wait_for_load_state("networkidle", timeout=10000)

            page_number = 1

            while True:
                if page_number > max_pages:
                    logger.info(f"Reached maximum page limit of {max_pages}. Stopping pagination.")
                    break

                logger.info(f"Scraping URLs from page {page_number}...")
                # Extract URLs from the current page
                overview_list = page.locator("nextens-overview-list")
                if overview_list.count() == 0:
                    logger.error("Overview list not found.")
                    raise Exception("Overview list not found.")
                list_items = overview_list.locator("nextens-overview-list-item")

                count = list_items.count()
                logger.info(f"Found {count} items in the overview list on page {page_number}.")

                # Capture the first URL before clicking 'Next' to detect page change
                if count > 0:
                    first_link_locator = list_items.nth(0).locator("a.c-link.overview-list-item-header")
                    if first_link_locator.count() > 0:
                        first_url_before = first_link_locator.get_attribute("href")
                    else:
                        first_url_before = ''
                else:
                    first_url_before = ''

                for i in range(count):
                    item = list_items.nth(i)
                    link = item.locator("a.c-link.overview-list-item-header")
                    if link.count() == 0:
                        logger.warning(f"No link found in item {i + 1} on page {page_number}. Skipping.")
                        continue
                    href = link.get_attribute("href")
                    if href:
                        full_url = f"https://naslag.nextens.nl{href}"
                        if full_url not in all_urls:
                            all_urls.add(full_url)
                            logger.info(f"URL {len(all_urls)}: {full_url}")
                        else:
                            logger.info(f"Duplicate URL found and skipped: {full_url}")
                    else:
                        logger.warning(f"No href attribute found in link of item {i + 1} on page {page_number}. Skipping.")

                # Check if there is a next page
                logger.info("Checking for the presence of a 'Next' button...")
                next_button = page.locator(
                    "nextens-pagination button.c-button.pagination.normal.image:has(i.far.fa-angle-right)"
                )
                if next_button.count() == 0:
                    logger.info("No 'Next' button found. Assuming last page reached.")
                    break  # No pagination controls found, exit loop

                # Check if the 'Next' button is disabled
                is_disabled = next_button.get_attribute("disabled") is not None
                if is_disabled:
                    logger.info("The 'Next' button is disabled. Last page reached.")
                    break  # 'Next' button is disabled, exit loop

                # Click the 'Next' button to go to the next page
                logger.info("Clicking the 'Next' button to navigate to the next page...")
                next_button.click()

                # Wait for the new page to load by ensuring the first URL has changed
                try:
                    page.wait_for_function(
                        """
                        (old_url) => {
                            const firstLink = document.querySelector("nextens-overview-list a.c-link.overview-list-item-header");
                            if (firstLink) {
                                return firstLink.getAttribute("href") !== old_url;
                            }
                            return false;
                        }
                        """,
                        arg=first_url_before,
                        timeout=150000
                    )
                    logger.info(f"Successfully navigated to page {page_number + 1}.")
                except PlaywrightTimeoutError:
                    logger.warning("Timeout while waiting for the next page to load. Assuming no further pages.")
                    break  # Exit loop if the next page doesn't load

                page_number += 1

            logger.info(f"Total unique URLs extracted from all pages: {len(all_urls)}")
            return list(all_urls)

        except Exception as e:
            logger.error(f"An error has occured: {e}")

    def scrape_content(self, browser: Browser, urls: list):
        """Scrape content from each URL and save to .txt files."""
        all_contents = {}
        for idx, url in enumerate(urls, start=1):
            logger.info(f"Processing URL {idx}/{len(urls)}: {url}")
            try:
                # Open a new page within the authenticated context
                if not self.context:
                    logger.error("Authenticated context not found. Cannot proceed with scraping.")
                    break

                with self.context.new_page() as page:
                    page.goto(url)
                    page.wait_for_load_state("networkidle", timeout=150000)

                    # Wait for the <app-recht-besluiten-single> tag to be present
                    recht_besluiten_single = page.locator("app-recht-besluiten-single.ng-star-inserted")
                    if recht_besluiten_single.count() == 0:
                        logger.warning(f"<app-recht-besluiten-single> not found in {url}. Skipping.")
                        continue

                    # Locate the 'print-section' within <app-recht-besluiten-single>
                    print_section = recht_besluiten_single.locator("div#print-section")
                    if print_section.count() == 0:
                        logger.warning(f"'print-section' not found in {url}. Skipping.")
                        continue

                    # Locate the toggle link/button to expand the content
                    toggle_link = print_section.locator(
                        "a.c-link.panel.ignore-in-page-search.ng-star-inserted.collapse"
                    )
                    if toggle_link.count() == 0:
                        logger.warning(f"Toggle link/button not found in {url}. Skipping.")
                        continue

                    # Click the toggle to expand the content
                    logger.info(f"Clicking the toggle link/button to expand content in {url}...")
                    toggle_link.click()

                    # Wait for the expanded content to load dynamically
                    expanded_content = print_section.locator("div.c-collapse-content")
                    try:
                        expanded_content.wait_for(state="visible", timeout=50000)
                        logger.info(f"Expanded content loaded in {url}.")
                    except PlaywrightTimeoutError:
                        logger.warning(f"Expanded content did not load in {url} within the timeout period.")

                    # Extract the first <h1> text for filename
                    h1 = print_section.locator("h1")
                    if h1.count() == 0:
                        logger.warning(f"No <h1> found in 'print-section' of {url}. Using default filename.")
                        filename = self.sanitize_filename(f"file_{idx}.txt")
                    else:
                        h1_text = h1.first.inner_text().strip()
                        # Optionally, limit the length of the filename
                        h1_text = h1_text[:100]  # Limit to 100 characters
                        filename = self.sanitize_filename(f"{h1_text}.txt")

                    # Extract the inner HTML of 'print-section'
                    html_content = print_section.inner_html()
                    if not html_content:
                        logger.warning(f"No HTML content found in 'print-section' of {url}.")
                        continue

                    # Convert HTML to Markdown
                    markdown_content = self.converter.handle(html_content)

                    # Remove five consecutive lines of double underscores
                    markdown_content = re.sub(r'(?:__\s*\n){5}', '', markdown_content)

                    # Clean the Markdown content by collapsing multiple newlines
                    cleaned_content = re.sub(r'\n+', '\n', markdown_content).strip()

                    # Prepare the content with the URL prepended
                    final_content = f"URL: {url}\n{cleaned_content}"

                    # Define the file path
                    file_path = os.path.join(f'{self.output_folder}/{self.fiscal_topic}/{self.data_category}/{self.besluiten_folder}', filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    # Handle duplicate filenames by appending an index if necessary
                    if os.path.exists(file_path):
                        logger.warning(f"Filename '{filename}' already exists. Appending index to filename.")
                        base, ext = os.path.splitext(filename)
                        file_path = os.path.join(f'{self.output_folder}/{self.fiscal_topic}/{self.data_category}/{self.besluiten_folder}', f"{base}_{idx}{ext}")

                    # Save to .txt file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(final_content)
                    logger.info(f"Content saved to {file_path}")

                    # Optionally, store in a dictionary
                    all_contents[url] = cleaned_content

                    # Optional: Add delay to respect server load
                    time.sleep(1)  # Sleep for 1 second

            except PlaywrightTimeoutError as te:
                logger.error(f"Timeout while processing {url}: {te}")
                continue
            except Exception as e:
                logger.error(f"An error occurred while processing {url}: {e}")
                continue

        logger.info(f"Total contents scraped and saved: {len(all_contents)}")
        return all_contents

    def scrape_besluiten_docs(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = self.authenticate(browser)
                urls = self.scrape_urls(page)
                if not urls:
                    logger.error("No URLs were scraped. Exiting.")
                    return
                logger.info(f"Total URLs to process: {len(urls)}")
                self.scrape_content(browser, urls)
                logger.info("Scraping completed successfully.")
            except Exception as e:
                logger.error(f"Scraping failed: {e}")
            finally:
                browser.close()
