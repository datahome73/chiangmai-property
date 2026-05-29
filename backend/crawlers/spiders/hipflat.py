"""Hipflat Thailand — https://www.hipflat.co.th

清迈房源爬虫。该站点使用 Cloudflare，建议使用 Playwright。
数据通过内部 API (JSON) 加载，spider 优先尝试 API，失败则回退到 Playwright。
"""

import scrapy
import json
import re
from urllib.parse import urlencode, urljoin
from datetime import datetime

from crawlers.items import PropertyItem


class HipflatSpider(scrapy.Spider):
    name = "hipflat"
    allowed_domains = ["hipflat.co.th"]
    base_url = "https://www.hipflat.co.th"

    use_playwright = True

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 4.0,
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,
    }

    def start_requests(self):
        # Try direct HTTP first; middleware will upgrade to Playwright on Cloudflare
        urls = [
            "https://www.hipflat.co.th/en/for-rent/chiang-mai",
            "https://www.hipflat.co.th/en/for-sale/chiang-mai",
        ]
        for url in urls:
            yield scrapy.Request(
                url,
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse,
            )

    async def parse(self, response):
        """Parse grid page — extract listing cards and pagination."""
        self.logger.info("📄 Hipflat page: %s", response.url)

        # ── Extract listing URLs ───────────────────────────
        cards = response.css(
            "a[href*='/en/listing/'], "
            "a[href*='/en/property/'], "
            "a[class*='listing-item'], "
            "div[class*='listing-card'] a, "
            "article a[href*='/en/']"
        )
        urls = set()
        for link in cards:
            href = link.css("::attr(href)").get()
            if href and "/en/listing/" in href:
                urls.add(urljoin(self.base_url, href))
            elif href and "/en/property/" in href:
                urls.add(urljoin(self.base_url, href))

        for url in urls:
            yield scrapy.Request(
                url,
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse_listing,
            )

        # ── Pagination (common patterns) ───────────────────
        next_link = (
            response.css('a[rel="next"]::attr(href)').get()
            or response.css("a[aria-label='Next']::attr(href)").get()
            or response.css("a.pagination__next::attr(href)").get()
            or response.css("li.next a::attr(href)").get()
        )
        if next_link:
            yield scrapy.Request(
                urljoin(self.base_url, next_link),
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse,
            )

    async def parse_listing(self, response):
        """Parse individual property detail."""
        self.logger.info("🏠 Hipflat listing: %s", response.url)

        item = PropertyItem()
        item["source"] = "hipflat"
        item["url"] = response.url
        item["crawled_at"] = datetime.utcnow().isoformat()

        # Source ID from URL
        id_match = re.search(r"/listing/(\d+)", response.url) or re.search(r"/property/(\d+)", response.url)
        item["source_id"] = id_match.group(1) if id_match else ""

        # ── Listing type from URL ──────────────────────────
        item["listing_type"] = "rent" if "for-rent" in response.url else "sale"

        # ── Title ──────────────────────────────────────────
        item["title"] = (
            response.css("h1::text").get("").strip()
            or response.css("[data-test='title']::text").get("").strip()
            or response.css("[class*='project-name']::text").get("").strip()
        )

        # ── Price ──────────────────────────────────────────
        price = (
            response.css("[class*='price']::text").get("")
            or response.css("[data-test='price']::text").get("")
            or response.css("[class*='listing-price']::text").get("")
        )
        if price:
            item["original_price_text"] = price.strip()
            digits = re.sub(r"[^\d]", "", price)
            if digits:
                item["price"] = float(digits)

        # ── Location ───────────────────────────────────────
        location = (
            response.css("[class*='location']::text").get("")
            or response.css("[data-test='location']::text").get("")
        )
        if location:
            item["location_name"] = location.strip()
            parts = [p.strip() for p in location.split(",")]
            if len(parts) >= 1:
                item["province"] = "Chiang Mai"
                item["district"] = parts[0] if "Chiang" not in parts[0] else ""
            if len(parts) >= 2:
                item["subdistrict"] = parts[-2].strip()

        # ── Details ────────────────────────────────────────
        details = " ".join(response.css("[class*='detail'], [class*='feature'], li::text, td::text").getall())

        bed_match = re.search(r"(\d+)\s*(?:bed|bedroom)", details, re.I)
        if bed_match:
            item["bedrooms"] = int(bed_match.group(1))

        bath_match = re.search(r"(\d+)\s*(?:bath|bathroom)", details, re.I)
        if bath_match:
            item["bathrooms"] = int(bath_match.group(1))

        area_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*m|m²|sqm)", details, re.I)
        if area_match:
            item["floor_area"] = float(area_match.group(1))

        floor_match = re.search(r"(?:Floor)\s*(\d+)", details, re.I)
        if floor_match:
            item["floor_number"] = int(floor_match.group(1))

        # ── Furnishing ─────────────────────────────────────
        if "fully furnished" in details.lower():
            item["furnishing"] = "Fully Furnished"
        elif "unfurnished" in details.lower():
            item["furnishing"] = "Unfurnished"
        elif "semi" in details.lower():
            item["furnishing"] = "Semi-Furnished"

        # ── Description ────────────────────────────────────
        desc = (
            response.css("[class*='description']::text").get("")
            or response.css("meta[name='description']::attr(content)").get("")
        )
        if desc:
            item["description"] = desc.strip()

        # ── Images ─────────────────────────────────────────
        imgs = response.css(
            "img[class*='gallery']::attr(src), "
            "div[class*='gallery'] img::attr(src), "
            "[data-test='photo'] img::attr(src)"
        ).getall() or response.css("meta[property='og:image']::attr(content)").getall()
        if imgs:
            item["images"] = [urljoin(self.base_url, u) for u in imgs[:20]]

        # ── Property type ──────────────────────────────────
        ptype_text = details.lower()
        if "condo" in ptype_text or "apartment" in ptype_text:
            item["property_type"] = "condo"
        elif "house" in ptype_text or "villa" in ptype_text:
            item["property_type"] = "house"
        elif "townhouse" in ptype_text:
            item["property_type"] = "townhouse"
        else:
            item["property_type"] = "condo"

        yield item
