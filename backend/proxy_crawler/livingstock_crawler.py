"""LivingStock crawler — extends BaseCrawler.

LivingStock.com is server-side rendered, HTML structure is stable.
List page prices/bedrooms/area are directly available.
"""
import json
import logging
import re
from parsel import Selector
from urllib.parse import urljoin

from proxy_crawler.base_crawler import BaseCrawler

logger = logging.getLogger("livingstock-crawler")

BASE_URL = "https://www.livingstock.com"


class LivingstockCrawler(BaseCrawler):
    SOURCE = "livingstock"
    BASE_URL = BASE_URL
    RATE_LIMIT = 2.5
    CRAWL_LIST_ONLY = True

    LIST_URLS = [
        "https://www.livingstock.com/property-for-rent/chiang-mai",
        "https://www.livingstock.com/property-for-sale/chiang-mai",
    ]

    def get_list_urls(self) -> list[str]:
        return self.LIST_URLS

    def parse_list(self, html: str) -> list[dict]:
        sel = Selector(text=html)
        listings = []

        for card in sel.css("div.property-item, article.property-card, div.listing-item"):
            title = card.css("h2::text, .title::text, h3::text").get("")
            if not title:
                title = card.css("a::attr(title)").get("")

            href = card.css("a::attr(href)").get("")
            url = urljoin(BASE_URL, href) if href else ""

            price_text = card.css(".price::text, .sale-price::text, .rent-price::text").get("")
            price = None
            if price_text:
                digits = re.sub(r"[^\d]", "", price_text)
                if digits:
                    price = float(digits)

            location = card.css(".location::text, .address::text, .district::text").get("")

            summary_parts = card.css(".features span::text, .summary span::text, .details span::text").getall()
            summary = " ".join(summary_parts)

            bedrooms = None
            bed_match = re.search(r"(\d+)\s*(?:bed|bedroom|br)", summary, re.I)
            if bed_match:
                bedrooms = int(bed_match.group(1))

            area_sqm = None
            area_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*m|m²|sqm|sqm)", summary, re.I)
            if area_match:
                area_sqm = float(area_match.group(1))

            source_id = ""
            if href:
                m = re.search(r"/property/([^/]+)", href)
                if m:
                    source_id = m.group(1)
                else:
                    m = re.search(r"/(\d+)", href)
                    if m:
                        source_id = m.group(1)

            if not source_id:
                continue

            listing_type = "RENT" if "for-rent" in url.lower() else "SALE"
            img = card.css("img::attr(src)").get("")
            images = [urljoin(BASE_URL, img)] if img and "http" not in img[:4] else ([img] if img else [])

            listings.append({
                "url": url,
                "source_id": source_id,
                "title": title.strip() if title else "",
                "price": price,
                "listing_type": listing_type,
                "location_name": location.strip() if location else "",
                "bedrooms": bedrooms,
                "floor_area": area_sqm,
                "images": images,
                "source_url": url,
            })

        logger.info("  Parsed %d listings from LivingStock", len(listings))
        return listings

    def parse_detail(self, html: str, listing: dict) -> dict:
        return listing
