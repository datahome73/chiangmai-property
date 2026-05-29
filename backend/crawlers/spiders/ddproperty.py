import scrapy
from urllib.parse import urlencode

from crawlers.items import PropertyItem


class DdpropertySpider(scrapy.Spider):
    """Scraper for DD Property Thailand — https://www.ddproperty.com"""

    name = "ddproperty"
    allowed_domains = ["ddproperty.com"]
    base_url = "https://www.ddproperty.com"

    # Rentals in Chiang Mai
    start_urls = [
        "https://www.ddproperty.com/%E0%B9%83%E0%B8%AB%E0%B9%89%E0%B9%80%E0%B8%8A%E0%B9%88%E0%B8%B2/%E0%B8%84%E0%B8%AD%E0%B8%99%E0%B9%82%E0%B8%94/%E0%B9%80%E0%B8%8A%E0%B8%B5%E0%B8%A2%E0%B8%87%E0%B9%83%E0%B8%AB%E0%B8%A1%E0%B9%88",
    ]

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 3.0,
    }

    def parse(self, response):
        """Parse listing grid page — extract individual listing URLs and follow pagination."""
        self.logger.info("Parsing page: %s", response.url)

        # Extract listing card URLs
        listing_urls = response.css(
            "a[href*='/%E0%B9%83%E0%B8%AB%E0%B9%89%E0%B9%80%E0%B8%8A%E0%B9%88%E0%B8%B2/'], "
            "a[href*='/%E0%B8%82%E0%B8%B2%E0%B8%A2/']"
        )
        # TODO: refine the selector after inspecting actual page structure
        # listing_urls = response.css('div.listing-card a::attr(href)').getall()

        for url in listing_urls:
            yield response.follow(url, callback=self.parse_listing)

        # Follow pagination
        next_page = response.css('a[rel="next"]::attr(href)').get()
        # TODO: refine pagination selector
        # next_page = response.css('a.pagination__next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_listing(self, response):
        """Parse individual listing detail page."""
        self.logger.info("Parsing listing: %s", response.url)

        item = PropertyItem()
        item["source"] = "ddproperty"
        item["url"] = response.url
        item["listing_type"] = "rent"

        # TODO: extract fields from the page
        # item['title'] = response.css('h1::text').get()
        # item['price'] = response.css('.price::text').get()
        # item['location_name'] = response.css('.location::text').get()
        # item['bedrooms'] = response.css('.bedrooms::text').get()
        # item['bathrooms'] = response.css('.bathrooms::text').get()

        yield item
