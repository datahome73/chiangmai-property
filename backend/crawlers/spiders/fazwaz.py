import scrapy
from urllib.parse import urlencode

from crawlers.items import PropertyItem


class FazwazSpider(scrapy.Spider):
    """Scraper for FazWaz Thailand — https://www.fazwaz.com"""

    name = "fazwaz"
    allowed_domains = ["fazwaz.com"]
    base_url = "https://www.fazwaz.com"

    # Rentals in Chiang Mai
    start_urls = [
        "https://www.fazwaz.com/property-for-rent/chiang-mai",
    ]

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 3.0,
    }

    def parse(self, response):
        """Parse listing grid page — extract individual listing URLs and follow pagination."""
        self.logger.info("Parsing page: %s", response.url)

        # Extract listing card URLs
        # TODO: refine selector after inspecting actual page structure
        listing_urls = response.css(
            "a[href*='/property-for-rent/'], a[href*='/property-for-sale/']"
        )

        for url in listing_urls:
            yield response.follow(url, callback=self.parse_listing)

        # Follow pagination
        next_page = response.css('a[rel="next"]::attr(href)').get()
        # TODO: refine pagination selector
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_listing(self, response):
        """Parse individual listing detail page."""
        self.logger.info("Parsing listing: %s", response.url)

        item = PropertyItem()
        item["source"] = "fazwaz"
        item["url"] = response.url
        item["listing_type"] = "rent"

        # TODO: extract fields from the page
        # item['title'] = response.css('h1::text').get()
        # item['price'] = response.css('.price::text').get()
        # item['location_name'] = response.css('.location::text').get()
        # item['bedrooms'] = response.css('.bedrooms::text').get()
        # item['bathrooms'] = response.css('.bathrooms::text').get()

        yield item
