import asyncio

from definitions.enums import FiscalTopic
from scrapers.belastingdienst.belastingdienst_scraper import BelastingdienstScraper
from scrapers.indicator.indicator_scraper import IndicatorScraper
from scrapers.mfas.mfas_scraper import MFASScraper
from scrapers.nextens.almanak_scraper import AlmanakScraper
from scrapers.nextens.besluiten_scraper import BesluitenScraper
from scrapers.nextens.onderwerp_scraper import OnderwerpScraper
from scrapers.nextens.tarieven_scraper import TarievenScraper
from scrapers.nextens.wetten_scraper import WettenScraper
from logger.logger import Logger

logger = Logger.get_logger(__name__)

# Configure setting to scrape documents based on fiscal topic: "OB", "IB", or "VPB"
#   Examples:
#       - scraper_setting = FiscalTopic.OB.value
#       - scraper_setting = FiscalTopic.IB.value
#       - scraper_setting = FiscalTopic.VPB.value
# Initialize setting below:
scraper_setting = FiscalTopic.OB.value

class DocumentScraper:
    def __init__(self, scraper_setting: FiscalTopic):
        # Initialize scraper setting as fiscal topic
        self.fiscal_topic = scraper_setting

        # Belastingdienst scraper
        self.belastingdienst_scraper = BelastingdienstScraper(self.fiscal_topic)

        # Nextens scrapers
        self.almanak_scraper = AlmanakScraper(self.fiscal_topic)
        self.besluiten_scraper = BesluitenScraper(self.fiscal_topic)
        self.tarieven_scraper = TarievenScraper(self.fiscal_topic)
        self.onderwerp_scraper = OnderwerpScraper(self.fiscal_topic)
        self.wetten_scraper = WettenScraper(self.fiscal_topic)

        # Indicator scraper
        self.indicator_scraper = IndicatorScraper(self.fiscal_topic)

        # MFAS scraper
        self.mfas_scraper = MFASScraper(self.fiscal_topic)

    def scrape_documents(self):
        # Scrape all documents
        # TODO: Save in Azure blob storage
        self.belastingdienst_scraper.scrape_belastingdienst_docs()
        self.almanak_scraper.scrape_almanak_docs()
        self.besluiten_scraper.scrape_besluiten_docs()
        self.tarieven_scraper.scrape_tarieven_docs()
        self.onderwerp_scraper.scrape_onderwerp_docs()
        self.wetten_scraper.scrape_wetten_docs()
        self.indicator_scraper.scrape_indicator_docs()
        asyncio.run(self.mfas_scraper.scrape_mfas_docs())


def main():
    document_scraper = DocumentScraper(scraper_setting)
    document_scraper.scrape_documents()

if __name__ == "__main__":
    main()


