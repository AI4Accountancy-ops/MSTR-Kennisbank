from playwright.sync_api import BrowserContext

import definitions.names as n
from definitions.credentials import Credentials


class NextensLogin:
    def __init__(self):
        # Retrieve credentials and URLs from definitions
        self.username = Credentials.get_scraping_credentials().get(n.NEXTENS_USERNAME)
        self.password = Credentials.get_scraping_credentials().get(n.NEXTENS_PASSWORD)
        self.base_url = "https://naslag.nextens.nl"
        self.login_url = "https://naslag.nextens.nl/Account/Login"

    def authenticate(self, context: BrowserContext):
        """
        Handles user login and returns an authenticated page context.
        """
        page = context.new_page()

        # Navigate to login page
        page.goto(self.login_url, timeout=600000, wait_until="domcontentloaded")

        # Fill in login credentials
        page.fill("#email", self.username, timeout=600000)
        page.fill("#password", self.password, timeout=600000)

        # Submit the form
        page.click("#submitButton")
        page.wait_for_url(self.base_url + "/*", timeout=100000)

        return context
