"""FazWaz Thailand — https://www.fazwaz.com

东南亚房产平台，覆盖泰国全境。清迈房源爬虫。
该站点使用 Cloudflare，建议使用 Playwright。
"""

import scrapy
import json
import re
from urllib.parse import urlencode, urljoin
from datetime import datetime

from crawlers.items import PropertyItem


class FazwazSpider(scrapy.Spider):
    name = "fazwaz"
    allowed_domains = ["fazwaz.com"]
    base_url = "https://www.fazwaz.com"

    use_playwright = True
    max_pages = 50

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 4.0,
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [429, 500, 502, 503, 504, 403],
    }

    def __init__(self, rent=True, sale=False, max_pages=50, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.start_urls = []
        if rent:
            self.start_urls.append("https://www.fazwaz.com/property-for-rent/chiang-mai")
        if sale:
            self.start_urls.append("https://www.fazwaz.com/property-for-sale/chiang-mai")

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse,
            )

    async def parse(self, response):
        """Parse search/listings grid page."""
        self.logger.info("📄 FazWaz page: %s", response.url)

        # ── Max pages safety ────────────────────────────────
        if self.max_pages <= 0:
            self.logger.info("⏹️  Max pages reached, stopping pagination")
            return

        # ── Extract listing URLs ───────────────────────────
        # FazWaz uses <a> tags with specific href patterns
        links = response.css(
            "a[href*='/property-for-rent/']:not([href*='/thailand']):not([href*='/chiang-mai']), "
            "a[href*='/property-for-sale/']:not([href*='/thailand']):not([href*='/chiang-mai']), "
            "a[class*='listing-item'], "
            "a[class*='property-item'], "
            "article a[href*='/']"
        )

        urls = set()
        for link in links:
            href = link.css("::attr(href)").get()
            if not href:
                continue
            # Filter: must be a property detail page (has ID or slug)
            if re.match(r"/(?:property-for-(?:rent|sale)/[^/]+(?:/\d+)?$)", href):
                urls.add(urljoin(self.base_url, href))

        # Also try JSON data embedded in the page
        json_data = response.css("script#__NEXT_DATA__::text").get() or response.css(
            "script[type='application/json']::text"
        ).get()
        if json_data:
            try:
                data = json.loads(json_data)
                props = self._extract_from_json(data)
                for p in props:
                    url = p.get("url", "")
                    if url:
                        urls.add(urljoin(self.base_url, url))
            except (json.JSONDecodeError, KeyError):
                pass

        for url in urls:
            yield scrapy.Request(
                url,
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse_listing,
            )

        # ── Pagination ─────────────────────────────────────
        next_link = (
            response.css('a[rel="next"]::attr(href)').get()
            or response.css("a.pagination__next::attr(href)").get()
            or response.css("a.next::attr(href)").get()
            or response.css("li.next a::attr(href)").get()
        )
        if next_link and self.max_pages > 0:
            self.max_pages -= 1
            yield scrapy.Request(
                urljoin(self.base_url, next_link),
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse,
            )

    def _extract_from_json(self, data):
        """Recursively extract listing data from embedded JSON."""
        items = []
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, (dict, list)):
                    items.extend(self._extract_from_json(val))
                if key in ("listing", "property", "properties", "listings") and isinstance(val, (dict, list)):
                    if isinstance(val, dict):
                        val = [val]
                    for item in val:
                        if isinstance(item, dict) and "url" in item:
                            items.append(item)
        elif isinstance(data, list):
            for item in data:
                items.extend(self._extract_from_json(item))
        return items

    async def parse_listing(self, response):
        """Parse property detail page."""
        self.logger.info("🏠 FazWaz listing: %s", response.url)

        item = PropertyItem()
        item["source"] = "fazwaz"
        item["url"] = response.url
        item["crawled_at"] = datetime.utcnow().isoformat()

        # Source ID
        id_match = re.search(r"/(\d+)(?:/|$)", response.url)
        item["source_id"] = id_match.group(1) if id_match else response.url.rstrip("/").split("/")[-1]

        # Listing type
        item["listing_type"] = "rent" if "for-rent" in response.url else "sale"

        # ── Title ──────────────────────────────────────────
        item["title"] = (
            response.css("h1::text").get("").strip()
            or response.css("[class*='title'] h1::text").get("").strip()
            or response.css("[data-test='title']::text").get("").strip()
        )

        # ── Price ──────────────────────────────────────────
        price = (
            response.css("[class*='price']::text").get("")
            or response.css("[data-test='price'] span::text").get("")
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
            or response.css("[data-test='location'] span::text").get("")
            or response.css("[itemprop='address']::attr(content)").get("")
        )
        if location:
            item["location_name"] = location.strip()

        # ── Details from spec table ────────────────────────
        specs = {}
        for row in response.css("table[class*='spec'] tr, [class*='spec'] [class*='row'], .spec-item"):
            key = row.css("th::text, [class*='label']::text").get("").strip()
            val = row.css("td::text, [class*='value']::text, span::text").get("").strip()
            if key and val:
                specs[key.lower()] = val

        # Also extract from dl/dt/dd
        for dt, dd in zip(
            response.css("dt::text, [class*='term']::text").getall(),
            response.css("dd::text, [class*='desc']::text").getall(),
        ):
            specs[dt.strip().lower()] = dd.strip()

        details_text = " ".join(response.css("*::text").getall()).lower()

        # ── Parse specs ────────────────────────────────────
        item["bedrooms"] = self._get_int(specs, ["bedroom", "bed", "bedrooms"])
        item["bathrooms"] = self._get_int(specs, ["bathroom", "bath", "bathrooms"])
        item["floor_area"] = self._get_float(specs, ["size", "living area", "floor area", "area"])
        item["land_area"] = self._get_float(specs, ["land area", "land size"])
        item["total_floors"] = self._get_int(specs, ["total floor", "floors", "number of floors"])
        item["parking"] = self._get_int(specs, ["parking", "parking spaces"])

        # Floor number
        floor_match = re.search(r"(?:floor|level)\s*(\d+)", details_text)
        if floor_match:
            item["floor_number"] = int(floor_match.group(1))

        # Furnishing
        furn_text = self._get_str(specs, ["furnishing", "furniture", "furnished"])
        if furn_text:
            item["furnishing"] = furn_text
        elif "fully furnished" in details_text:
            item["furnishing"] = "Fully Furnished"

        # Year built
        year = self._get_int(specs, ["year built", "built year", "construction year"])
        if year:
            item["year_built"] = year

        # ── Property type ──────────────────────────────────
        ptype = self._get_str(specs, ["property type", "type"])
        if ptype:
            item["property_type"] = ptype.lower()
        elif "condo" in details_text:
            item["property_type"] = "condo"
        elif "house" in details_text or "villa" in details_text:
            item["property_type"] = "house"
        elif "townhouse" in details_text:
            item["property_type"] = "townhouse"
        elif "apartment" in details_text:
            item["property_type"] = "apartment"
        else:
            item["property_type"] = "condo"

        # ── Description ────────────────────────────────────
        desc = (
            response.css("[class*='description']::text").get("")
            or response.css("meta[name='description']::attr(content)").get("")
        )
        if desc:
            item["description"] = desc.strip()

        # ── Images ─────────────────────────────────────────
        imgs = response.css(
            "img[class*='gallery']::attr(data-src), "
            "img[class*='gallery']::attr(src), "
            "div[class*='gallery'] img::attr(src), "
            ".property-gallery img::attr(src)"
        ).getall()
        if not imgs:
            imgs = response.css("meta[property='og:image']::attr(content)").getall()
        if imgs:
            item["images"] = [urljoin(self.base_url, u) for u in imgs[:20]]

        # ── Agent ──────────────────────────────────────────
        item["agent_name"] = (
            response.css("[class*='agent'] [class*='name']::text").get("")
            or response.css("[data-test='agent-name']::text").get("")
        )
        item["agent_phone"] = (
            response.css("[class*='agent'] [class*='phone']::text").get("")
            or response.css("[data-test='agent-phone']::text").get("")
        )

        yield item

    def _get_int(self, specs, keys):
        for k in keys:
            v = specs.get(k)
            if v:
                return int(float(re.sub(r"[^\d.]", "", str(v))))
        return None

    def _get_float(self, specs, keys):
        for k in keys:
            v = specs.get(k)
            if v:
                return float(re.sub(r"[^\d.]", "", str(v)))
        return None

    def _get_str(self, specs, keys):
        for k in keys:
            v = specs.get(k)
            if v:
                return v.strip()
        return None
