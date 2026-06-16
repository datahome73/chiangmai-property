"""HipFlat crawler — extends BaseCrawler."""
import json
import logging
import re
from urllib.parse import urljoin
from parsel import Selector

from proxy_crawler.base_crawler import BaseCrawler

logger = logging.getLogger("hipflat-crawler")

BASE_URL = "https://www.hipflat.co.th"


class HipflatCrawler(BaseCrawler):
    SOURCE = "hipflat"
    BASE_URL = BASE_URL
    RATE_LIMIT = 2.0
    CRAWL_LIST_ONLY = True  # HipFlat list page has sufficient data

    LIST_URLS = [
        "https://www.hipflat.co.th/en/condo-for-rent/chiang-mai",
        "https://www.hipflat.co.th/en/condo-for-sale/chiang-mai",
        "https://www.hipflat.co.th/en/house-for-rent/chiang-mai",
        "https://www.hipflat.co.th/en/house-for-sale/chiang-mai",
    ]

    def get_list_urls(self) -> list[str]:
        return self.LIST_URLS

    def parse_list(self, html: str) -> list[dict]:
        sel = Selector(text=html)
        snippets = sel.css("div.snippet")
        listings = []
        for snippet in snippets:
            href = snippet.css("a::attr(href)").get("")
            title = snippet.css("a::attr(title)").get("")
            url = urljoin(BASE_URL, href) if href else ""
            source_id_match = re.search(r"/ads/([a-z0-9]+)", url)
            source_id = source_id_match.group(1) if source_id_match else ""

            if not source_id:
                continue

            price_text = snippet.css(".snippet-price::text").get("")
            price = None
            if price_text and re.search(r"\d", price_text):
                digits = re.sub(r"[^\d]", "", price_text)
                price = float(digits) if digits else None

            loc = snippet.css(".snippet-address::text").get("").strip()
            summary_texts = snippet.css(".snippet-summary *::text").getall()
            summary = " ".join(summary_texts)

            bedrooms = None
            bed_match = re.search(r"(\d+)\s*(?:bed|bedroom|Bed)", summary, re.I)
            if bed_match:
                bedrooms = int(bed_match.group(1))

            bathrooms = None
            bath_match = re.search(r"(\d+)\s*(?:bath|bathroom|Bath)", summary, re.I)
            if bath_match:
                bathrooms = int(bath_match.group(1))

            floor_area = None
            area_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*m|m²|sqm)", summary, re.I)
            if area_match:
                floor_area = float(area_match.group(1))

            district = snippet.css(".snippet-address .district::text").get("") or ""
            if not district and loc:
                district = loc.split(",")[0].strip() if "," in loc else loc

            listing_type = "RENT" if "for-rent" in (href or "") else "SALE"

            desc = snippet.css("p::text").get("").strip()

            img_urls = snippet.css("img::attr(src)").getall()
            unique_images = []
            for img in img_urls:
                if img and "hipflat" in img and img not in unique_images:
                    if img.startswith("/"):
                        img = urljoin(BASE_URL, img)
                    unique_images.append(img)

            listings.append({
                "url": url,
                "source_id": source_id,
                "title": title,
                "price": price,
                "listing_type": listing_type,
                "location_name": loc,
                "district": district,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "floor_area": floor_area,
                "property_type": "condo" if "condo" in (url or "") else "house",
                "description": desc,
                "images": unique_images[:5],
                "source_url": url,
            })

        return listings

    def parse_detail(self, html: str, listing: dict) -> dict:
        return listing
