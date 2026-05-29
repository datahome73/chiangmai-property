"""DD Property Thailand — https://www.ddproperty.com

清迈房源爬虫。支持出租/出售类型。
该站点使用 Cloudflare 保护，建议使用 Playwright。
"""

import scrapy
import json
import re
from urllib.parse import urlencode, urljoin
from datetime import datetime

from crawlers.items import PropertyItem


class DdpropertySpider(scrapy.Spider):
    name = "ddproperty"
    allowed_domains = ["ddproperty.com"]
    base_url = "https://www.ddproperty.com"

    # ── Chiang Mai entry URLs ──────────────────────────────
    # 出租 / 清迈 / 所有类型
    start_urls = [
        "https://www.ddproperty.com/%E0%B9%83%E0%B8%AB%E0%B9%89%E0%B9%80%E0%B8%8A%E0%B9%88%E0%B8%B2/%E0%B9%80%E0%B8%8A%E0%B8%B5%E0%B8%A2%E0%B8%87%E0%B9%83%E0%B8%AB%E0%B8%A1%E0%B9%88",
    ]

    use_playwright = True  # Enable Cloudflare auto-retry with Playwright
    max_pages = 50         # Safety limit

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 5.0,
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,
    }

    def __init__(self, rent=True, sale=False, max_pages=50, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        if rent and sale:
            # Both
            self.start_urls = [
                "https://www.ddproperty.com/%E0%B9%83%E0%B8%AB%E0%B9%89%E0%B9%80%E0%B8%8A%E0%B9%88%E0%B8%B2/%E0%B9%80%E0%B8%8A%E0%B8%B5%E0%B8%A2%E0%B8%87%E0%B9%83%E0%B8%AB%E0%B8%A1%E0%B9%88",
                "https://www.ddproperty.com/%E0%B8%82%E0%B8%B2%E0%B8%A2/%E0%B9%80%E0%B8%8A%E0%B8%B5%E0%B8%A2%E0%B8%87%E0%B9%83%E0%B8%AB%E0%B8%A1%E0%B9%88",
            ]
        elif sale:
            self.start_urls = [
                "https://www.ddproperty.com/%E0%B8%82%E0%B8%B2%E0%B8%A2/%E0%B9%80%E0%B8%8A%E0%B8%B5%E0%B8%A2%E0%B8%87%E0%B9%83%E0%B8%AB%E0%B8%A1%E0%B9%88",
            ]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse,
            )

    async def parse(self, response):
        """Parse listing grid — extract cards and follow pagination."""
        self.logger.info("📄 Parsing page: %s", response.url)

        # ── Extract listing cards ───────────────────────────
        # Common patterns on ddproperty:
        cards = response.css(
            "div.listing-card, "
            "div[class*='ListingCard'], "
            "div[class*='listing-card'], "
            "div[data-test='listing-card'], "
            "article[class*='card'], "
            "div[class*='property-card']"
        )

        if not cards:
            # Try broader selectors
            cards = response.css(
                "a[href*='/detail/'], "
                "a[href*='-%E0%B9%83%E0%B8%AB%E0%B9%89%E0%B9%80%E0%B8%8A%E0%B9%88%E0%B8%B2-'], "
                "a[href*='-%E0%B8%82%E0%B8%B2%E0%B8%A2-']"
            )
            listing_urls = cards
        else:
            listing_urls = cards.css("a::attr(href)").getall()

        for url in listing_urls:
            href = url if isinstance(url, str) else url.root  # handle selector results
            if not href or href.startswith("#") or href.startswith("javascript"):
                continue
            absolute_url = urljoin(self.base_url, href)
            yield scrapy.Request(
                absolute_url,
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse_listing,
            )

        # ── Pagination ─────────────────────────────────────
        next_page = response.css(
            'a[rel="next"]::attr(href), '
            'a.pagination__next::attr(href), '
            'a[class*="next"]::attr(href), '
            'li.next a::attr(href)'
        ).get()

        if next_page and self.max_pages > 0:
            self.max_pages -= 1
            yield scrapy.Request(
                urljoin(self.base_url, next_page),
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse,
            )

    async def parse_listing(self, response):
        """Parse individual property detail page."""
        self.logger.info("🏠 Parsing listing: %s", response.url)

        item = PropertyItem()
        item["source"] = "ddproperty"
        item["url"] = response.url
        item["crawled_at"] = datetime.utcnow().isoformat()

        # Extract source ID from URL
        id_match = re.search(r"[./](\d+)(?:/|$)", response.url)
        item["source_id"] = id_match.group(1) if id_match else response.url.split("/")[-1]

        # ── Title ──────────────────────────────────────────
        item["title"] = (
            response.css("h1::text").get("").strip()
            or response.css("h1[class*='title']::text").get("").strip()
            or response.css("[data-test='listing-title']::text").get("").strip()
        )

        # ── Price ──────────────────────────────────────────
        price_text = (
            response.css("[class*='price']::text").get("")
            or response.css("[data-test='price']::text").get("")
            or response.css(".listing-price::text").get("")
        )
        if price_text:
            item["original_price_text"] = price_text.strip()
            digits = re.sub(r"[^\d]", "", price_text)
            if digits:
                item["price"] = float(digits)
            # Determine listing type
            if "rent" in response.url.lower() or "ให้เช่า" in response.url:
                item["listing_type"] = "rent"
            elif "sale" in response.url.lower() or "ขาย" in response.url:
                item["listing_type"] = "sale"

        # ── Location ───────────────────────────────────────
        location = (
            response.css("[class*='location']::text").get("")
            or response.css("[data-test='location']::text").get("")
        )
        if location:
            item["location_name"] = location.strip()
            parts = location.strip().split(",")
            if len(parts) >= 1:
                item["province"] = "Chiang Mai"
            if len(parts) >= 2:
                item["district"] = parts[-2].strip()
            if len(parts) >= 3:
                item["subdistrict"] = parts[-3].strip()

        # ── Property Details ───────────────────────────────
        details_text = " ".join(response.css("[class*='detail'], [class*='feature'], [class*='info'], li::text").getall())

        # Bedrooms
        bed_match = re.search(r"(\d+)\s*(?:bed|bedroom|ห้องนอน)|(\d+)\s*(?=Bed)", details_text, re.I)
        if bed_match:
            item["bedrooms"] = int(bed_match.group(1) or bed_match.group(2))

        # Bathrooms
        bath_match = re.search(r"(\d+)\s*(?:bath|bathroom|ห้องน้ำ)", details_text, re.I)
        if bath_match:
            item["bathrooms"] = int(bath_match.group(1))

        # Floor area
        area_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*m|ตารางเมตร|m²|sqm)", details_text, re.I)
        if area_match:
            item["floor_area"] = float(area_match.group(1))

        # Floor number
        floor_match = re.search(r"(?:ชั้น|Floor)\s*(\d+)", details_text, re.I)
        if floor_match:
            item["floor_number"] = int(floor_match.group(1))

        # Furnishing
        if "fully furnished" in details_text.lower() or "fully-furnished" in details_text.lower():
            item["furnishing"] = "Fully Furnished"
        elif "semi" in details_text.lower() and "furnish" in details_text.lower():
            item["furnishing"] = "Semi-Furnished"
        elif "unfurnished" in details_text.lower() or "ไม่ furnished" in details_text.lower():
            item["furnishing"] = "Unfurnished"

        # ── Description ────────────────────────────────────
        desc = (
            response.css("[class*='description']::text").get("")
            or response.css("[data-test='description']::text").get("")
            or response.css("meta[name='description']::attr(content)").get("")
        )
        if desc:
            item["description"] = desc.strip()

        # ── Images ─────────────────────────────────────────
        image_urls = response.css(
            "img[class*='gallery']::attr(src), "
            "img[class*='photo']::attr(src), "
            "div[class*='gallery'] img::attr(src), "
            "[data-test='gallery'] img::attr(src)"
        ).getall()
        if image_urls:
            # Filter out thumbnails, keep full-size
            full_images = [u for u in image_urls if "thumb" not in u.lower()]
            item["images"] = [urljoin(self.base_url, u) for u in full_images[:20]]

        # ── Agent ──────────────────────────────────────────
        item["agent_name"] = (
            response.css("[class*='agent'] [class*='name']::text").get("")
            or response.css("[data-test='agent-name']::text").get("")
        )

        yield item
