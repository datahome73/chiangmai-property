"""
清迈房产比价平台 — 各站点 HTML 解析器

每个解析器接受 HTML 字符串，返回符合数据库模型的字典列表。
解析器基于真实的泰国房产网站 HTML 结构编写。
"""

import json
import logging
import re
from urllib.parse import urljoin
from datetime import datetime
from typing import List, Dict, Optional

from parsel import Selector

logger = logging.getLogger("parsers")


class BaseParser:
    """解析器基类"""

    SOURCE = ""       # 站点标识 (ddproperty/hipflat/fazwaz)
    BASE_URL = ""     # 站点基础 URL

    def parse_listing(self, html: str, url: str) -> Optional[Dict]:
        """解析详情页 HTML，返回一条房产数据"""
        raise NotImplementedError

    def parse_list_urls(self, html: str, base_url: str) -> List[str]:
        """解析列表页 HTML，提取所有房源详情页 URL"""
        raise NotImplementedError

    def parse_next_page(self, html: str, base_url: str) -> Optional[str]:
        """解析列表页 HTML，提取下一页 URL"""
        raise NotImplementedError

    def _clean_price(self, text: str) -> Optional[float]:
        """从价格文本中提取数字"""
        if not text:
            return None
        digits = re.sub(r"[^\d]", "", text)
        return float(digits) if digits else None

    def _clean_int(self, text: str) -> Optional[int]:
        if not text:
            return None
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits else None

    def _clean_float(self, text: str) -> Optional[float]:
        if not text:
            return None
        digits = re.sub(r"[^\d.]", "", text)
        return float(digits) if digits else None


class DdpropertyParser(BaseParser):
    """DD Property Thailand 解析器"""

    SOURCE = "ddproperty"
    BASE_URL = "https://www.ddproperty.com"

    # ── List page patterns ────────────────────────────────
    LISTING_CARD_SELECTORS = [
        "div[data-test='listing-card'] a::attr(href)",
        "div.listing-card a::attr(href)",
        "a[class*='listing-card']::attr(href)",
        "div[class*='listing-card'] a[href*='/detail/']::attr(href)",
    ]
    NEXT_PAGE_SELECTORS = [
        "a[rel='next']::attr(href)",
        "a.pagination__next::attr(href)",
        "a.pagination-next::attr(href)",
        "li.next a::attr(href)",
    ]

    def parse_list_urls(self, html: str, base_url: str) -> List[str]:
        sel = Selector(text=html)
        urls = set()
        for selector in self.LISTING_CARD_SELECTORS:
            for href in sel.css(selector).getall():
                full_url = urljoin(self.BASE_URL, href)
                if full_url and "ddproperty.com" in full_url and "detail" in full_url.lower():
                    urls.add(full_url)
        logger.info(f"  📋 找到 {len(urls)} 个房源链接")
        return list(urls)

    def parse_next_page(self, html: str, base_url: str) -> Optional[str]:
        sel = Selector(text=html)
        for selector in self.NEXT_PAGE_SELECTORS:
            href = sel.css(selector).get()
            if href:
                return urljoin(self.BASE_URL, href)
        return None

    def parse_listing(self, html: str, url: str) -> Optional[Dict]:
        sel = Selector(text=html)
        data = {
            "source": self.SOURCE,
            "source_url": url,
            "crawled_at": datetime.utcnow().isoformat(),
        }

        # Source ID from URL
        id_match = re.search(r"[/.](\d+)(?:/|$)", url)
        data["source_id"] = id_match.group(1) if id_match else url.rstrip("/").split("/")[-1]

        # Listing type
        if "ให้เช่า" in url or "/rent/" in url.lower():
            data["listing_type"] = "rent"
        elif "ขาย" in url or "/sale/" in url.lower():
            data["listing_type"] = "sale"
        else:
            data["listing_type"] = "rent"

        # Title
        for sel_title in ["h1::text", "[data-test='listing-title']::text", "h1[class*='title']::text"]:
            title = sel.css(sel_title).get("").strip()
            if title:
                data["title"] = title
                break

        # Price
        for sel_price in [
            "[data-test='price']::text",
            "[class*='listing-price']::text",
            "[class*='price'] span::text",
            "meta[property='product:price:amount']::attr(content)",
        ]:
            price_text = sel.css(sel_price).get("")
            if price_text and re.search(r"\d", price_text):
                data["original_price_text"] = price_text.strip()
                data["price"] = self._clean_price(price_text)
                break

        # Location
        for sel_loc in [
            "[data-test='location']::text",
            "[class*='location']::text",
            "meta[name='geo.placename']::attr(content)",
        ]:
            loc = sel.css(sel_loc).get("")
            if loc:
                data["location_name"] = loc.strip()
                parts = [p.strip() for p in loc.split(",")]
                if len(parts) >= 1:
                    data["province"] = "Chiang Mai"
                if len(parts) >= 2:
                    data["district"] = parts[-2].strip()
                if len(parts) >= 3:
                    data["subdistrict"] = parts[-3].strip()
                break

        # Details from spec table / features list
        all_text = " ".join(sel.css("[class*='detail'] *, [class*='feature'] *, li::text, td::text, dt::text, dd::text").getall()).lower()

        # Bedrooms
        bed = re.search(r"(\d+)\s*(?:bed|bedroom|ห้องนอน)", all_text, re.I)
        if bed:
            data["bedrooms"] = int(bed.group(1))

        # Bathrooms
        bath = re.search(r"(\d+)\s*(?:bath|bathroom|ห้องน้ำ)", all_text, re.I)
        if bath:
            data["bathrooms"] = int(bath.group(1))

        # Floor area
        area = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*m|m²|sqm|ตารางเมตร)", all_text, re.I)
        if area:
            data["floor_area"] = float(area.group(1))

        # Floor
        floor = re.search(r"(?:ชั้น|floor|level)\s*(\d+)", all_text, re.I)
        if floor:
            data["floor_number"] = int(floor.group(1))

        # Total floors
        total = re.search(r"(\d+)\s*(?:ชั้น|floor|level)s?\s*(?:total|all|building)", all_text, re.I)
        if total:
            data["total_floors"] = int(total.group(1))

        # Property type
        if "condo" in all_text or "คอนโด" in all_text:
            data["property_type"] = "CONDO"
        elif "house" in all_text or "บ้าน" in all_text or "villa" in all_text:
            data["property_type"] = "HOUSE"
        elif "townhouse" in all_text or "ทาวน์เฮาส์" in all_text:
            data["property_type"] = "TOWNHOUSE"
        elif "apartment" in all_text:
            data["property_type"] = "APARTMENT"
        else:
            data["property_type"] = "CONDO"

        # Furnishing
        if "fully furnished" in all_text or "fully-furnished" in all_text or "เฟอร์นิเจอร์ครบ" in all_text:
            data["furnishing"] = "Fully Furnished"
        elif "unfurnished" in all_text or "ไม่ furnished" in all_text:
            data["furnishing"] = "Unfurnished"
        elif "semi" in all_text:
            data["furnishing"] = "Semi-Furnished"

        # Description
        desc = sel.css("[class*='description'] *::text").get("") or sel.css("meta[name='description']::attr(content)").get("")
        if desc:
            data["description"] = re.sub(r"\s+", " ", desc).strip()

        # Images
        images = sel.css("[class*='gallery'] img::attr(src), [data-test='gallery'] img::attr(src), img[class*='photo']::attr(src)").getall()
        if not images:
            images = [sel.css("meta[property='og:image']::attr(content)").get("")]
        data["images"] = [urljoin(self.BASE_URL, u) for u in images if u and "thumb" not in u.lower()][:20]

        # Agent
        data["agent_name"] = sel.css("[class*='agent'] [class*='name']::text, [data-test='agent-name']::text").get("").strip()

        # Coordinates (from meta or embedded JSON)
        lat = sel.css("meta[name='geo.position']::attr(content)").get("")
        if lat and ";" in lat:
            data["latitude"], data["longitude"] = [float(x.strip()) for x in lat.split(";")]

        logger.info(f"  ✅ 解析完成: {data.get('title', 'N/A')[:40]}")
        return data


class HipflatParser(BaseParser):
    """Hipflat Thailand 解析器"""

    SOURCE = "hipflat"
    BASE_URL = "https://www.hipflat.co.th"

    def parse_list_urls(self, html: str, base_url: str) -> List[str]:
        sel = Selector(text=html)
        urls = set()
        # Each listing is in a div.snippet with an <a> link
        for snippet in sel.css("div.snippet"):
            href = snippet.css("a::attr(href)").get("")
            title = snippet.css("a::attr(title)").get("")
            if href and "chiang" in (title + href).lower():
                full_url = urljoin(self.BASE_URL, href)
                urls.add(full_url)
        logger.info(f"  📋 找到 {len(urls)} 个清迈房源链接")
        return list(urls)

    def parse_next_page(self, html: str, base_url: str) -> Optional[str]:
        sel = Selector(text=html)
        # Pagination: <li class="page" data-value="N"> — get current, then next
        current = sel.css("li.page-current::attr(data-value)").get("")
        if not current:
            current = sel.css("li.page.current::attr(data-value)").get("")
            if not current:
                current = sel.css("li.page.active::attr(data-value)").get("")
        if current:
            try:
                next_page = int(current) + 1
                # Build next page URL from base (removing any existing page param)
                clean_url = re.sub(r"\?page=\d+", "", base_url)
                return f"{clean_url}?page={next_page}"
            except ValueError:
                pass
        return None

    def parse_listing(self, html: str, url: str) -> Optional[Dict]:
        """解析 HipFlat 详情页 HTML"""
        sel = Selector(text=html)
        data = {
            "source": self.SOURCE,
            "source_url": url,
            "crawled_at": datetime.utcnow().isoformat(),
        }

        # Source ID from /en/ads/CODE
        id_match = re.search(r"/ads/([a-z0-9]+)", url)
        data["source_id"] = id_match.group(1) if id_match else url.rstrip("/").split("/")[-1]

        data["listing_type"] = "rent" if "for-rent" in url else "sale"

        all_text = " ".join(sel.css("*::text").getall()).lower()
        data["all_text"] = all_text

        # Title from <h1> or og:title
        title = sel.css("h1::text").get("").strip()
        if not title:
            title = sel.css("meta[property='og:title']::attr(content)").get("")
        data["title"] = title

        # Price — look for snippet-price or any price text
        price_text = sel.css(".snippet-price::text").get("")
        if not price_text:
            price_text = sel.css("[class*='price']::text, [data-test='price']::text").get("")
        if price_text and re.search(r"\d", price_text):
            data["original_price_text"] = price_text.strip()
            # Strip currency prefix
            clean = re.sub(r"^[A-Z]{3}\s*", "", price_text)
            data["price"] = self._clean_price(clean)

        # Location from snippet-address or detail page
        loc = sel.css(".snippet-address::text").get("")
        if not loc:
            loc = sel.css("[class*='address']::text, [class*='location']::text").get("")
        if loc:
            data["location_name"] = loc.strip()
            parts = [p.strip() for p in loc.split(",")]
            data["province"] = "Chiang Mai"
            if len(parts) >= 1:
                data["district"] = parts[0] if "Mueang" in parts[0] or "Chiang" not in parts[0] else ""
            if len(parts) >= 2:
                data["subdistrict"] = parts[-2].strip()

        # Bedrooms, Bathrooms, Area from summary classes
        summary_texts = sel.css(".snippet-summary *::text").getall()
        summary = " ".join(summary_texts)

        bed = re.search(r"(\d+)\s*(?:bed|bedroom|Bed)", summary, re.I)
        if bed:
            data["bedrooms"] = int(bed.group(1))

        bath = re.search(r"(\d+)\s*(?:bath|bathroom|Bath)", summary, re.I)
        if bath:
            data["bathrooms"] = int(bath.group(1))

        area = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*m|m²|sqm|Sq\.?\s*[Mm])", summary, re.I)
        if area:
            data["floor_area"] = float(area.group(1))

        # Property type from snippet-info
        prop_type = sel.css(".snippet-info::text").get("").strip().lower()
        if "condo" in prop_type or "apartment" in prop_type:
            data["property_type"] = "CONDO"
        elif "house" in prop_type or "villa" in prop_type:
            data["property_type"] = "HOUSE"
        elif "townhouse" in prop_type:
            data["property_type"] = "TOWNHOUSE"
        else:
            data["property_type"] = prop_type or "CONDO"

        # Furnishing
        if "fully furnished" in all_text:
            data["furnishing"] = "Fully Furnished"
        elif "unfurnished" in all_text:
            data["furnishing"] = "Unfurnished"

        # Description from snippet-description
        desc1 = sel.css(".snippet-description-1 *::text, .snippet-description-2 *::text").getall()
        desc2 = sel.css("[class*='description'] *::text").getall()
        desc_text = " ".join(desc1 or desc2)
        if not desc_text:
            desc_text = sel.css("meta[name='description']::attr(content)").get("")
        if desc_text:
            data["description"] = re.sub(r"\s+", " ", desc_text).strip()

        # Images
        images = sel.css(
            ".snippet-images img::attr(src), "
            "[class*='gallery'] img::attr(src), "
            "img.snippet-image::attr(src)"
        ).getall()
        if not images:
            images = sel.css("meta[property='og:image']::attr(content)").getall()
        data["images"] = [urljoin(self.BASE_URL, u) for u in images if u and "thumb" not in u.lower()][:10]

        logger.info(f"  ✅ 解析完成: {data.get('title', 'N/A')[:40]}")
        return data


class FazwazParser(BaseParser):
    """FazWaz Thailand 解析器"""

    SOURCE = "fazwaz"
    BASE_URL = "https://www.fazwaz.com"

    LISTING_URL_SELECTORS = [
        "div[data-section] a.unit__item__link::attr(href)",
        "a[class*='unit__item__link']::attr(href)",
        "a[href*='/property-sales/']::attr(href)",
        "a[href*='/property-rentals/']::attr(href)",
    ]
    NEXT_PAGE_SELECTORS = [
        "a[rel='next']::attr(href)",
        "a.pagination__next::attr(href)",
        "a.next::attr(href)",
        "li.next a::attr(href)",
    ]

    def parse_list_urls(self, html: str, base_url: str) -> List[str]:
        sel = Selector(text=html)
        urls = set()

        # 1. From <a> tags in listing cards
        for selector in self.LISTING_URL_SELECTORS:
            for href in sel.css(selector).getall():
                full_url = urljoin(self.BASE_URL, href)
                if full_url and self.BASE_URL in full_url and "chiang-mai" in full_url.lower():
                    urls.add(full_url)

        # 2. From embedded JSON-LD in each card - filter by Chiang Mai location
        for script in sel.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and "url" in item:
                        url = item["url"]
                        # Check if Chiang Mai from address
                        addr = item.get("address", {}) or {}
                        region = addr.get("addressRegion", "") if isinstance(addr, dict) else ""
                        if isinstance(addr, str):
                            region = addr
                        if "chiang mai" in url.lower() or "chiang mai" in str(region).lower():
                            urls.add(url)
            except (json.JSONDecodeError, Exception):
                pass

        logger.info(f"  📋 找到 {len(urls)} 个清迈房源链接")
        return list(urls)

    def _extract_urls_from_json(self, data, urls: set):
        """递归从嵌入 JSON 中提取房源 URL"""
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, (dict, list)):
                    self._extract_urls_from_json(val, urls)
                if key in ("url", "slug", "seo_url") and isinstance(val, str):
                    if val.startswith("/") or "fazwaz.com" in val:
                        urls.add(urljoin(self.BASE_URL, val))
        elif isinstance(data, list):
            for item in data:
                self._extract_urls_from_json(item, urls)

    def parse_next_page(self, html: str, base_url: str) -> Optional[str]:
        sel = Selector(text=html)
        for selector in self.NEXT_PAGE_SELECTORS:
            href = sel.css(selector).get()
            if href:
                return urljoin(self.BASE_URL, href)
        return None

    def parse_listing(self, html: str, url: str) -> Optional[Dict]:
        sel = Selector(text=html)
        data = {
            "source": self.SOURCE,
            "source_url": url,
            "crawled_at": datetime.utcnow().isoformat(),
        }

        id_match = re.search(r"/(\d+)(?:/|$)", url)
        data["source_id"] = id_match.group(1) if id_match else url.rstrip("/").split("/")[-1]

        data["listing_type"] = "rent" if "for-rent" in url else "sale"

        # Title
        for s in ["h1::text", "[class*='title'] h1::text", "[data-test='title']::text"]:
            t = sel.css(s).get("").strip()
            if t:
                data["title"] = t
                break

        # Price
        for s in [
            "[class*='price'] span::text",
            "[class*='listing-price']::text",
            "[data-test='price'] span::text",
            "meta[property='product:price:amount']::attr(content)",
        ]:
            p = sel.css(s).get("")
            if p and re.search(r"\d", p):
                data["original_price_text"] = p.strip()
                data["price"] = self._clean_price(p)
                break

        # Location
        for s in ["[class*='location']::text", "[data-test='location'] span::text", "[itemprop='address']::attr(content)"]:
            loc = sel.css(s).get("")
            if loc:
                data["location_name"] = loc.strip()
                break

        # Specs from table rows
        specs = {}
        for row in sel.css("table[class*='spec'] tr, [class*='spec-item'], .prop-detail"):
            key = row.css("th::text, [class*='label']::text, dt::text").get("").strip().lower()
            val = row.css("td::text, [class*='value']::text, dd::text, span::text").get("").strip()
            if key and val:
                specs[key] = val

        # Parse specs
        for k, v in specs.items():
            if "bed" in k:
                data["bedrooms"] = self._clean_int(v)
            elif "bath" in k:
                data["bathrooms"] = self._clean_int(v)
            elif "size" in k or "area" in k or "sqm" in k:
                data["floor_area"] = self._clean_float(v)
            elif "floor" in k and "total" not in k:
                data["floor_number"] = self._clean_int(v)
            elif "total" in k and "floor" in k:
                data["total_floors"] = self._clean_int(v)
            elif "park" in k:
                data["parking"] = self._clean_int(v)
            elif "furn" in k:
                data["furnishing"] = v
            elif "year" in k or "built" in k:
                data["year_built"] = self._clean_int(v)
            elif "type" in k or "property" in k:
                pt = v.lower()
                if "condo" in pt or "apartment" in pt:
                    data["property_type"] = "CONDO"
                elif "house" in pt or "villa" in pt:
                    data["property_type"] = "HOUSE"
                elif "townhouse" in pt:
                    data["property_type"] = "TOWNHOUSE"

        all_text = " ".join(sel.css("*::text").getall()).lower()
        if "property_type" not in data:
            if "condo" in all_text: data["property_type"] = "CONDO"
            elif "house" in all_text or "villa" in all_text: data["property_type"] = "HOUSE"
            elif "townhouse" in all_text: data["property_type"] = "TOWNHOUSE"
            else: data["property_type"] = "CONDO"

        desc = sel.css("[class*='description'] *::text").get("") or sel.css("meta[name='description']::attr(content)").get("")
        if desc:
            data["description"] = re.sub(r"\s+", " ", desc).strip()

        images = sel.css("[class*='gallery'] img::attr(src), [class*='gallery'] img::attr(data-src), img[class*='photo']::attr(src)").getall()
        if not images:
            images = sel.css("meta[property='og:image']::attr(content)").getall()
        data["images"] = [urljoin(self.BASE_URL, u) for u in images if u][:20]

        data["agent_name"] = sel.css("[class*='agent'] [class*='name']::text, [data-test='agent-name']::text").get("").strip()

        # Coordinates from meta
        lat = sel.css("[data-test='latitude']::attr(content), meta[name='geo.position']::attr(content)").get("")
        if ";" in lat:
            data["latitude"], data["longitude"] = [float(x.strip()) for x in lat.split(";")]

        logger.info(f"  ✅ 解析完成: {data.get('title', 'N/A')[:40]}")
        return data


class DotpropertyParser(BaseParser):
    """Dot Property Thailand 解析器 (Next.js SSR + JSON-LD)"""

    SOURCE = "dotproperty"
    BASE_URL = "https://www.dotproperty.co.th"

    def parse_list_urls(self, html: str, base_url: str) -> List[str]:
        sel = Selector(text=html)
        urls = set()
        # Detail page links: /en/ads/...
        for href in sel.css('a[href*="/en/ads/"]::attr(href)').getall():
            full_url = urljoin(self.BASE_URL, href)
            if full_url:
                urls.add(full_url)
        logger.info(f"  📋 找到 {len(urls)} 个房源链接")
        return list(urls)

    def parse_next_page(self, html: str, base_url: str) -> Optional[str]:
        sel = Selector(text=html)
        # Pagination: ?page=N links
        current_page = 1
        # Find current page from active pagination link
        for a in sel.css('a[href*="page="]'):
            href = a.attrib.get("href", "")
            txt = a.css("::text").get("")
            # Find the largest page number that's not the current/active one
            page_match = re.search(r"page=(\d+)", href)
            if page_match:
                p = int(page_match.group(1))
                if p > current_page:
                    # Check if it's a "next" link - href without text content usually means next
                    if not txt.strip():
                        # Clean base_url of any existing page param
                        clean_url = re.sub(r"\?page=\d+", "", base_url)
                        return f"{clean_url}?page={p}"
        return None

    def parse_listing(self, html: str, url: str) -> Optional[Dict]:
        """解析 Dot Property 详情页，主要从 JSON-LD 提取数据"""
        sel = Selector(text=html)

        # Find the RealEstateListing JSON-LD
        listing_json = None
        for script in sel.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
                if isinstance(data, dict) and data.get("@type") == "RealEstateListing":
                    listing_json = data
                    break
            except (json.JSONDecodeError, Exception):
                continue

        if not listing_json:
            logger.warning("  ⚠️  未找到 JSON-LD 数据，页面可能无内容")
            return None

        main_entity = listing_json.get("mainEntity", {})
        offers = main_entity.get("offers", {})
        address = main_entity.get("address", {})
        geo = main_entity.get("geo", {})
        floor_size = main_entity.get("floorSize", {})

        listing_type = "rent"
        unit_text = offers.get("priceSpecification", {}).get("unitText", "")
        if "month" in unit_text.lower():
            listing_type = "rent"
        else:
            # Could be sale - check URL for hints
            listing_type = "rent" if "/for-rent/" in url.lower() or "/rent/" in url.lower() else "sale"

        data = {
            "source": self.SOURCE,
            "source_url": url,
            "crawled_at": datetime.utcnow().isoformat(),
            "source_id": url.rstrip("/").split("/")[-1].split("_")[-1] if "_" in url else url.rstrip("/").split("/")[-1],
            "listing_type": listing_type,
            "title": main_entity.get("name", listing_json.get("name", "")),
            "price": self._clean_price(str(offers.get("price", "0"))),
            "original_price_text": f"{offers.get('price', '')} THB",
            "currency": "THB",
            "bedrooms": main_entity.get("numberOfBedrooms"),
            "bathrooms": main_entity.get("numberOfBathroomsTotal"),
            "floor_area": floor_size.get("value"),
            "description": main_entity.get("description", ""),
            "location_name": address.get("streetAddress", ""),
            "district": address.get("addressLocality", ""),
            "province": address.get("addressRegion", "Chiang Mai"),
            "latitude": geo.get("latitude"),
            "longitude": geo.get("longitude"),
            "images": main_entity.get("image", []),
            "date_posted": listing_json.get("datePosted", ""),
        }

        # Property type
        types = main_entity.get("@type", [])
        if isinstance(types, list):
            if "Apartment" in types:
                data["property_type"] = "APARTMENT"
            else:
                data["property_type"] = "CONDO"
        elif isinstance(types, str):
            data["property_type"] = "CONDO"

        # Amenities
        amenities = main_entity.get("amenityFeature", [])
        if amenities:
            data["amenities"] = [a.get("name", "") for a in amenities if isinstance(a, dict)]

        # Furnishing from description
        all_text = (data.get("description", "") + " ").lower()
        if "fully furnished" in all_text or "fully-furnished" in all_text:
            data["furnishing"] = "Fully Furnished"
        elif "unfurnished" in all_text:
            data["furnishing"] = "Unfurnished"
        elif "semi" in all_text:
            data["furnishing"] = "Semi-Furnished"

        # Agent from URL pattern (Dot Property uses FazWaz's CDN for images)
        data["agent_name"] = "Dot Property"

        logger.info(f"  ✅ 解析完成: {data.get('title', 'N/A')[:40]}")
        return data


class PropertyhubParser(BaseParser):
    """PropertyHub Thailand 解析器 (Next.js SSR + JSON埋点)"""

    SOURCE = "propertyhub"
    BASE_URL = "https://propertyhub.in.th"

    def parse_list_urls(self, html: str, base_url: str) -> List[str]:
        sel = Selector(text=html)
        urls = set()
        for href in sel.css('a[href*="/en/listings/"]::attr(href)').getall():
            full_url = urljoin(self.BASE_URL, href)
            if full_url:
                urls.add(full_url)
        logger.info(f"  📋 找到 {len(urls)} 个房源链接")
        return list(urls)

    def parse_next_page(self, html: str, base_url: str) -> Optional[str]:
        sel = Selector(text=html)
        for a in sel.css('a[href*="/en/condo-for-rent/chiang-mai/"]'):
            href = a.attrib.get("href", "")
            txt = a.css("::text").get("")
            if txt and ("next" in txt.lower() or "ถัดไป" in txt):
                return urljoin(self.BASE_URL, href)
        return None

    def parse_listing(self, html: str, url: str) -> Optional[Dict]:
        """解析 PropertyHub 详情页，从 JSON props 提取数据"""
        sel = Selector(text=html)

        # Find application/json script with listing data
        listing_json = None
        for script in sel.css('script[type="application/json"]::text').getall():
            try:
                data = json.loads(script)
                listing = data.get("props", {}).get("pageProps", {}).get("listing")
                if listing:
                    listing_json = listing
                    break
            except (json.JSONDecodeError, Exception):
                continue

        if not listing_json:
            logger.warning("  ⚠️  未找到 listing JSON 数据")
            return None

        # Extract fields
        price_data = listing_json.get("price", {})
        for_rent = price_data.get("forRent", {})
        for_sale = price_data.get("forSale", {})

        monthly_rent = for_rent.get("monthly", {})
        sale_price = for_sale.get("price")

        room_info = listing_json.get("roomInformation", {}) or {}
        land_info = listing_json.get("landAndHouseInformation", {}) or {}
        proj = listing_json.get("project", {}) or {}
        loc = listing_json.get("location", {}) or {}

        post_type = listing_json.get("postType", "FOR_RENT")
        listing_type = "rent" if "RENT" in post_type else "sale"

        # Price
        price_val = None
        if listing_type == "rent":
            price_val = monthly_rent.get("price")
        elif sale_price:
            price_val = sale_price

        # Room details
        beds = room_info.get("numberOfBed") or land_info.get("numberOfBed")
        baths = room_info.get("numberOfBath") or land_info.get("numberOfBath")
        area = room_info.get("roomArea") or land_info.get("usableArea") or land_info.get("landSize")
        floor = room_info.get("onFloor")

        # Images
        images_raw = listing_json.get("images", [])
        images = []
        for img in images_raw:
            url_path = img.get("pictureUrl", "")
            if url_path and not url_path.startswith("http"):
                url_path = urljoin("https://propertyhub.in.th", url_path)
            if url_path:
                images.append(url_path)

        # Property type
        prop_type_raw = listing_json.get("propertyType", "CONDO")
        prop_type = "CONDO"
        if "HOUSE" in prop_type_raw or "HOME" in prop_type_raw:
            prop_type = "HOUSE"
        elif "TOWNHOUSE" in prop_type_raw or "TOWNHOME" in prop_type_raw:
            prop_type = "TOWNHOUSE"
        elif "APARTMENT" in prop_type_raw:
            prop_type = "APARTMENT"
        elif "LAND" in prop_type_raw:
            prop_type = "OTHER"

        # Furnishing
        amenities = listing_json.get("amenities", {}) or {}
        has_furniture = amenities.get("hasFurniture", False)
        furnishing = "Fully Furnished" if has_furniture else None

        # Description
        detail_html = listing_json.get("detail", "")
        desc = re.sub(r"<[^>]+>", "", detail_html).strip() if detail_html else ""

        data = {
            "source": self.SOURCE,
            "source_url": url,
            "crawled_at": datetime.utcnow().isoformat(),
            "source_id": str(listing_json.get("id", "")),
            "listing_type": listing_type,
            "title": listing_json.get("title", ""),
            "price": self._clean_price(str(price_val)) if price_val else None,
            "original_price_text": f"{price_val:,} THB" if price_val else None,
            "currency": "THB",
            "bedrooms": beds,
            "bathrooms": baths,
            "floor_area": float(area) if area else None,
            "floor_number": int(floor) if floor else None,
            "description": desc[:2000] if desc else "",
            "location_name": proj.get("address", listing_json.get("address", "")),
            "district": "",
            "province": "Chiang Mai",
            "latitude": loc.get("lat") or (proj.get("location", {}) or {}).get("lat"),
            "longitude": loc.get("lng") or (proj.get("location", {}) or {}).get("lng"),
            "images": images[:20],
            "property_type": prop_type,
            "furnishing": furnishing,
            "date_posted": listing_json.get("createdAt", ""),
        }

        # Source ID from URL as fallback
        if not data["source_id"]:
            slug = listing_json.get("slug", "")
            id_match = re.search(r"id-(\d+)", url)
            data["source_id"] = id_match.group(1) if id_match else slug.split("--")[-1] if "--" in slug else slug

        logger.info(f"  ✅ 解析完成: {data.get('title', 'N/A')[:40]}")
        return data


# ── Parser registry ───────────────────────────────────────

PARSERS = {
    "ddproperty": DdpropertyParser(),
    "hipflat": HipflatParser(),
    "fazwaz": FazwazParser(),
    "dotproperty": DotpropertyParser(),
    "propertyhub": PropertyhubParser(),
}
