#!/usr/bin/env python3
"""HipFlat 列表页解析：直接从 snippet 提取数据，不抓详情页"""
import os, sys, json, re, logging, time
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("hipflat-list")

API_KEY = os.environ.get("SCRAPINGANT_API_KEY", "2aa031d84c9c4781996faa541366a0f6")
BASE_URL = "https://www.hipflat.co.th"

URLS = [
    "https://www.hipflat.co.th/en/condo-for-rent/chiang-mai",
    "https://www.hipflat.co.th/en/condo-for-sale/chiang-mai",
    "https://www.hipflat.co.th/en/house-for-rent/chiang-mai",
    "https://www.hipflat.co.th/en/house-for-sale/chiang-mai",
]

import httpx
from parsel import Selector
from urllib.parse import urlencode

def fetch(url):
    params = {"url": url}
    headers = {"x-api-key": API_KEY}
    request_url = f"https://api.scrapingant.com/v2/general?{urlencode(params)}"
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        resp = client.get(request_url, headers=headers)
        return resp.text

def parse_snippet(snippet, listing_type):
    """Extract property data from a snippet element"""
    href = snippet.css("a::attr(href)").get("")
    title = snippet.css("a::attr(title)").get("")
    url = urljoin(BASE_URL, href) if href else ""
    source_id = re.search(r"/ads/([a-z0-9]+)", url)
    source_id = source_id.group(1) if source_id else ""

    price_text = snippet.css(".snippet-price::text").get("")
    price = None
    if price_text and re.search(r"\d", price_text):
        digits = re.sub(r"[^\d]", "", price_text)
        price = float(digits) if digits else None

    loc = snippet.css(".snippet-address::text").get("").strip()

    summary_texts = snippet.css(".snippet-summary *::text").getall()
    summary = " ".join(summary_texts)

    bedrooms = None
    bed = re.search(r"(\d+)\s*(?:bed|bedroom|Bed)", summary, re.I)
    if bed: bedrooms = int(bed.group(1))

    bathrooms = None
    bath = re.search(r"(\d+)\s*(?:bath|bathroom|Bath)", summary, re.I)
    if bath: bathrooms = int(bath.group(1))

    floor_area = None
    area = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*m|m²|sqm)", summary, re.I)
    if area: floor_area = float(area.group(1))

    prop_type = snippet.css(".snippet-info::text").get("").strip().lower()
    if "condo" in prop_type or "apartment" in prop_type: prop_type = "condo"
    elif "house" in prop_type or "villa" in prop_type: prop_type = "house"
    elif "townhouse" in prop_type: prop_type = "townhouse"
    else: prop_type = "condo"

    desc1 = snippet.css(".snippet-description-1 *::text").getall()
    desc2 = snippet.css(".snippet-description-2 *::text").getall()
    desc = " ".join(desc1 or desc2)
    desc = re.sub(r"\s+", " ", desc).strip() if desc else ""

    images = snippet.css(".snippet-images img::attr(src)").getall()
    og_image = snippet.css("meta[property='og:image']::attr(content)").get("")
    if not images and og_image:
        images = [og_image]

    district = loc.replace("Chiang Mai", "").replace(",", "").strip()
    if not district and "Mueang" in loc:
        district = "Mueang Chiang Mai"

    return {
        "source": "hipflat",
        "source_id": source_id,
        "source_url": url,
        "title": title or "",
        "price": price,
        "original_price_text": price_text.strip() if price_text else "",
        "listing_type": listing_type,
        "location_name": loc,
        "province": "Chiang Mai",
        "district": district,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "floor_area": floor_area,
        "property_type": prop_type,
        "description": desc,
        "images": images[:5],
        "crawled_at": datetime.utcnow().isoformat(),
    }

from urllib.parse import urljoin

def crawl():
    all_properties = []
    seen_ids = set()

    for url in URLS:
        listing_type = "sale" if "for-sale" in url else "rent"
        logger.info(f"\n=== {url} ===")
        html = fetch(url)
        sel = Selector(text=html)

        snippets = sel.css("div.snippet")
        logger.info(f"  找到 {len(snippets)} 个 snippets")

        for snippet in snippets:
            href = snippet.css("a::attr(href)").get("")
            sid = re.search(r"/ads/([a-z0-9]+)", href or "")
            if not sid or sid.group(1) in seen_ids:
                continue
            seen_ids.add(sid.group(1))

            prop = parse_snippet(snippet, listing_type)
            all_properties.append(prop)

        time.sleep(1)

    logger.info(f"\n✅ 共提取 {len(all_properties)} 条 HipFlat 房源")
    return all_properties

def save_to_db(properties):
    """Write to SQLite database"""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from crawlers.settings import DATABASE_URL

    engine = create_engine(DATABASE_URL)
    session = sessionmaker(bind=engine)()
    saved = 0

    for prop in properties:
        try:
            existing = session.execute(
                text("SELECT id FROM properties WHERE source = :s AND source_id = :sid"),
                {"s": "hipflat", "sid": prop["source_id"]},
            ).fetchone()

            if existing:
                session.execute(
                    text("""UPDATE properties SET
                        title=:title, price_rent=:price_rent, price_sale=:price_sale,
                        bedrooms=:beds, bathrooms=:baths, area_sqm=:area,
                        property_type=:ptype, address=:addr, district=:district,
                        images=:images, description=:desc, updated_at=:now
                        WHERE source='hipflat' AND source_id=:sid"""),
                    {
                        "title": prop.get("title", ""),
                        "price_rent": prop["price"] if prop.get("listing_type") == "rent" else None,
                        "price_sale": prop["price"] if prop.get("listing_type") == "sale" else None,
                        "beds": prop.get("bedrooms"), "baths": prop.get("bathrooms"),
                        "area": prop.get("floor_area"), "ptype": prop.get("property_type", "condo"),
                        "addr": prop.get("location_name", ""), "district": prop.get("district", ""),
                        "images": json.dumps(prop.get("images", [])),
                        "desc": prop.get("description", ""),
                        "now": datetime.utcnow(), "sid": prop.get("source_id", ""),
                    },
                )
                logger.debug(f"  🔄 更新: {prop.get('title', '')[:30]}")
            else:
                session.execute(
                    text("""INSERT INTO properties
                        (title, description, price_rent, price_sale, currency, price_type,
                         bedrooms, bathrooms, area_sqm, furnished, property_type,
                         address, district, lat, lng, source, source_url, source_id,
                         images, is_active, posted_date, scraped_at, updated_at)
                        VALUES (:title, :desc, :price_rent, :price_sale, 'USD', :price_type,
                         :beds, :baths, :area, 0, :ptype,
                         :addr, :district, NULL, NULL, 'hipflat', :url, :sid,
                         :images, 1, :now, :scraped, :now)"""),
                    {
                        "title": prop.get("title", ""),
                        "desc": prop.get("description", ""),
                        "price_rent": prop["price"] if prop.get("listing_type") == "rent" else None,
                        "price_sale": prop["price"] if prop.get("listing_type") == "sale" else None,
                        "price_type": prop.get("listing_type", "rent"),
                        "beds": prop.get("bedrooms"), "baths": prop.get("bathrooms"),
                        "area": prop.get("floor_area"), "ptype": prop.get("property_type", "condo"),
                        "addr": prop.get("location_name", ""), "district": prop.get("district", ""),
                        "url": prop.get("source_url", ""), "sid": prop.get("source_id", ""),
                        "images": json.dumps(prop.get("images", [])),
                        "now": datetime.utcnow(), "scraped": datetime.utcnow(),
                    },
                )
                logger.debug(f"  ✅ 新增: {prop.get('title', '')[:30]}")
            saved += 1
        except Exception as e:
            session.rollback()
            logger.error(f"  ❌ 失败: {e}")

    session.commit()
    session.close()
    logger.info(f"📦 数据库写入: {saved}/{len(properties)} 条")

if __name__ == "__main__":
    props = crawl()
    if props:
        save_to_db(props)
        # Also save JSON backup
        backup = f"/tmp/hipflat_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 JSON: {backup}")
    logger.info("✅ 全部完成")
