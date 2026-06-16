"""FazWaz crawler — fixes price extraction using JSON-LD from listing page.

Current problem: Detail page prices are JS-rendered and ScrapingAnt can't get them.
Solution: Use JSON-LD in listing page to extract prices directly.
"""
import json
import logging
import re
from parsel import Selector

from proxy_crawler.base_crawler import BaseCrawler

logger = logging.getLogger("fazwaz-crawler")


class FazwazCrawler(BaseCrawler):
    SOURCE = "fazwaz"
    BASE_URL = "https://www.fazwaz.com"
    RATE_LIMIT = 3.0
    CRAWL_LIST_ONLY = True  # Extract price from listing page JSON-LD

    LIST_URLS = [
        "https://www.fazwaz.com/property-for-rent/chiang-mai",
        "https://www.fazwaz.com/property-for-sale/chiang-mai",
    ]

    def get_list_urls(self) -> list[str]:
        return self.LIST_URLS

    def parse_list(self, html: str) -> list[dict]:
        sel = Selector(text=html)
        listings = []

        # Method 1: JSON-LD (most reliable for price)
        for script in sel.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
            except json.JSONDecodeError:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") in ("Product", "ItemList"):
                    # Handle both single product and item list
                    if item.get("@type") == "ItemList":
                        for el in item.get("itemListElement", []):
                            p = el.get("item", el)
                            self._extract_listing(p, listings)
                    else:
                        self._extract_listing(item, listings)

        # Method 2: HTML card parsing (fallback for items without JSON-LD)
        if not listings:
            for card in sel.css("div.property-card, article.property-item"):
                title = card.css("h2 a::text, .title::text").get("").strip()
                href = card.css("a::attr(href)").get("")
                price_text = card.css(".price::text, .sale-price::text").get("")
                price = None
                if price_text:
                    digits = re.sub(r"[^\d]", "", price_text)
                    if digits:
                        price = float(digits)
                source_id = ""
                if href:
                    m = re.search(r"/property/([a-z0-9-]+)", href)
                    source_id = m.group(1) if m else ""
                if source_id and title:
                    listings.append({
                        "url": "https://www.fazwaz.com" + href if href.startswith("/") else href,
                        "source_id": source_id,
                        "title": title,
                        "price": price,
                        "listing_type": "RENT" if "for-rent" in str(href).lower() else "SALE",
                    })

        logger.info("  Parsed %d listings from FazWaz", len(listings))
        return listings

    def _extract_listing(self, item: dict, listings: list) -> None:
        """Extract a single listing from JSON-LD item."""
        url = item.get("url", "")
        if not url or "chiang-mai" not in url.lower():
            return

        offers = item.get("offers", {})
        if isinstance(offers, dict):
            price = offers.get("price")
        elif isinstance(offers, list) and offers:
            price = offers[0].get("price")
        else:
            price = None

        if price:
            try:
                price = float(price)
            except (ValueError, TypeError):
                price = None

        name = item.get("name", "")
        source_id = ""
        m = re.search(r"/property/([a-z0-9-]+)", url)
        if m:
            source_id = m.group(1)

        if source_id:
            # Full URL
            if url.startswith("/"):
                url = "https://www.fazwaz.com" + url
            listing_type = "RENT" if "for-rent" in url.lower() else "SALE"

            listings.append({
                "url": url,
                "source_id": source_id,
                "title": name,
                "price": price,
                "listing_type": listing_type,
            })

    def parse_detail(self, html: str, listing: dict) -> dict:
        return listing
