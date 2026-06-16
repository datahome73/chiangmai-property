"""Base crawler class — common crawl workflow for all property sources."""
from abc import ABC, abstractmethod
import json
import logging
import time
import os
import re
from datetime import datetime
from typing import Optional, Any
from urllib.parse import urljoin

from proxy_crawler.proxy_adapter import ProxyAdapter

logger = logging.getLogger("base-crawler")


class BaseCrawler(ABC):
    """Abstract base crawler with unified crawl workflow.

    Subclasses implement:
      - parse_list(html) -> list of listing dicts (minimal data)
      - parse_detail(html, listing) -> full property dict
      - validate(data) -> list of warning strings (optional override)
    """

    SOURCE: str = ""
    BASE_URL: str = ""
    RATE_LIMIT: float = 2.0
    MAX_RETRIES: int = 3
    CRAWL_LIST_ONLY: bool = False  # If True, skip detail page parsing

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SCRAPINGANT_API_KEY", "")
        self.adapter = ProxyAdapter(service="scrapingant", api_key=self.api_key)
        self.stats: dict = {
            "source": self.SOURCE,
            "total": 0, "new": 0, "updated": 0,
            "skipped": 0, "errors": [],
            "duration_seconds": 0,
        }

    @abstractmethod
    def parse_list(self, html: str) -> list[dict]:
        """Parse listing page HTML into basic info: [{url, title, price_text, source_id, ...}]"""
        ...

    def parse_detail(self, html: str, listing: dict) -> dict:
        """Parse detail page HTML into complete property dict. Override if needed."""
        return listing

    def validate(self, data: dict) -> list[str]:
        """Validate scraped data. Return list of warning strings."""
        warnings = []
        if not data.get("title"):
            warnings.append("缺少标题")
        if not (data.get("price_rent") or data.get("price_sale") or data.get("price")):
            warnings.append("缺少价格")
        return warnings

    def to_property_dict(self, raw: dict) -> dict:
        """Convert raw scraped dict to ORM-compatible property dict."""
        price = raw.get("price")
        listing_type = raw.get("listing_type", "RENT")
        return {
            "title": raw.get("title", ""),
            "description": raw.get("description", ""),
            "price_rent": price if listing_type == "RENT" else None,
            "price_sale": price if listing_type == "SALE" else None,
            "currency": "THB",
            "price_type": listing_type,
            "bedrooms": raw.get("bedrooms"),
            "bathrooms": raw.get("bathrooms"),
            "area_sqm": raw.get("floor_area") or raw.get("area_sqm"),
            "floor": raw.get("floor"),
            "furnished": raw.get("furnished"),
            "property_type": raw.get("property_type", "condo"),
            "address": raw.get("location_name") or raw.get("address", ""),
            "district": raw.get("district", ""),
            "lat": raw.get("lat"),
            "lng": raw.get("lng"),
            "source": self.SOURCE,
            "source_url": raw.get("source_url", "") or raw.get("url", ""),
            "source_id": str(raw.get("source_id", "")),
            "images": json.dumps(raw.get("images", [])),
            "is_active": True,
            "posted_date": datetime.utcnow(),
            "scraped_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

    def _extract_source_id(self, url: str) -> str:
        """Extract source ID from URL. Override if source uses different pattern."""
        m = re.search(r"/([a-z0-9]+)(?:/|$)", url)
        return m.group(1) if m else ""

    def fetch(self, url: str) -> str:
        """Fetch HTML via ProxyAdapter with retry."""
        return self.adapter.fetch(url, max_retries=self.MAX_RETRIES)

    # ── Unified upsert via SQLAlchemy ORM ──────────────────────────

    def _upsert_property(self, session, prop_dict: dict) -> str:
        """Insert or update a property in the database. Returns 'new'/'updated'/'skipped'."""
        from sqlalchemy import text

        source_id = prop_dict.get("source_id", "")
        source = prop_dict.get("source", self.SOURCE)

        existing = session.execute(
            text("SELECT id, price_rent, price_sale FROM properties WHERE source = :s AND source_id = :sid"),
            {"s": source, "sid": source_id},
        ).fetchone()

        if existing:
            # Record price history on change
            old_rent, old_sale = existing[1], existing[2]
            new_rent = prop_dict.get("price_rent")
            new_sale = prop_dict.get("price_sale")
            if (old_rent != new_rent) or (old_sale != new_sale):
                session.execute(
                    text("""INSERT INTO price_history
                        (property_id, price_rent, price_sale, price_type, source, scraped_at)
                        VALUES (:pid, :rent, :sale, :ptype, :src, :now)"""),
                    {
                        "pid": existing[0],
                        "rent": old_rent, "sale": old_sale,
                        "ptype": prop_dict.get("price_type", "RENT"),
                        "src": source,
                        "now": datetime.utcnow(),
                    },
                )

            # Update
            session.execute(
                text("""UPDATE properties SET
                    title=:title, description=:desc, price_rent=:rent, price_sale=:sale,
                    currency=:cur, price_type=:ptype, bedrooms=:beds, bathrooms=:baths,
                    area_sqm=:area, floor=:floor, furnished=:furn, property_type=:prop_type,
                    address=:addr, district=:district, lat=:lat, lng=:lng,
                    images=:images, updated_at=:now
                    WHERE source=:src AND source_id=:sid"""),
                {
                    "title": prop_dict.get("title", ""), "desc": prop_dict.get("description", ""),
                    "rent": prop_dict.get("price_rent"), "sale": prop_dict.get("price_sale"),
                    "cur": "THB", "ptype": prop_dict.get("price_type", "RENT"),
                    "beds": prop_dict.get("bedrooms"), "baths": prop_dict.get("bathrooms"),
                    "area": prop_dict.get("area_sqm"), "floor": prop_dict.get("floor"),
                    "furn": prop_dict.get("furnished"), "prop_type": prop_dict.get("property_type", "condo"),
                    "addr": prop_dict.get("address", ""), "district": prop_dict.get("district", ""),
                    "lat": prop_dict.get("lat"), "lng": prop_dict.get("lng"),
                    "images": prop_dict.get("images", "[]"),
                    "now": datetime.utcnow(), "src": source, "sid": source_id,
                },
            )
            return "updated"
        else:
            # Insert
            session.execute(
                text("""INSERT INTO properties
                    (title, description, price_rent, price_sale, currency, price_type,
                     bedrooms, bathrooms, area_sqm, floor, furnished, property_type,
                     address, district, lat, lng, source, source_url, source_id,
                     images, is_active, posted_date, scraped_at, updated_at)
                    VALUES (:title, :desc, :rent, :sale, :cur, :ptype,
                     :beds, :baths, :area, :floor, :furn, :prop_type,
                     :addr, :district, :lat, :lng, :src, :url, :sid,
                     :images, 1, :now, :now, :now)"""),
                {**prop_dict, "url": prop_dict.get("source_url", ""), "now": datetime.utcnow()},
            )
            return "new"

    # ── Main crawl entry point ──────────────────────────────────────

    def crawl(self) -> dict:
        """Run the full crawl workflow. Returns stats dict."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from crawlers.settings import DATABASE_URL

        t0 = time.time()
        listings = []
        list_html = ""
        seen_ids = set()

        # 1. Fetch listing page
        list_urls = self.get_list_urls()
        for url in list_urls:
            logger.info("Fetching list: %s", url)
            html = self.fetch(url)
            if not html:
                self.stats["errors"].append({"url": url, "error": "Empty response"})
                continue
            list_html += html

            # 2. Parse listings
            for item in self.parse_list(html):
                sid = item.get("source_id", "")
                if sid and sid not in seen_ids:
                    seen_ids.add(sid)
                    listings.append(item)

        self.stats["total"] = len(listings)
        logger.info("Parsed %d listings from %s", len(listings), self.SOURCE)

        # 3. Fetch detail pages (if not CRAWL_LIST_ONLY)
        engine = create_engine(DATABASE_URL)
        session = sessionmaker(bind=engine)()
        results = {"new": 0, "updated": 0, "skipped": 0}

        for i, listing in enumerate(listings):
            try:
                if not self.CRAWL_LIST_ONLY:
                    detail_url = listing.get("url", "")
                    if detail_url and detail_url != listing.get("source_url", ""):
                        detail_html = self.fetch(detail_url)
                        full_data = self.parse_detail(detail_html, listing)
                    else:
                        full_data = listing
                else:
                    full_data = listing

                prop_dict = self.to_property_dict(full_data)

                # Validate
                warnings = self.validate(full_data)
                if warnings:
                    self.stats["errors"].append({
                        "url": listing.get("url", ""),
                        "warnings": warnings,
                    })

                # Upsert
                result = self._upsert_property(session, prop_dict)
                results[result] = results.get(result, 0) + 1

                if (i + 1) % 20 == 0:
                    session.commit()
                    logger.info("  Progress: %d/%d (%s)", i + 1, len(listings), results)

            except Exception as e:
                self.stats["errors"].append({
                    "url": listing.get("url", ""),
                    "error": str(e)[:200],
                })
                session.rollback()

        session.commit()
        session.close()

        self.stats["new"] = results.get("new", 0)
        self.stats["updated"] = results.get("updated", 0)
        self.stats["duration_seconds"] = round(time.time() - t0, 1)

        logger.info(
            "Crawl complete: %s — new=%d updated=%d errors=%d (%.1fs)",
            self.SOURCE, self.stats["new"], self.stats["updated"],
            len(self.stats["errors"]), self.stats["duration_seconds"],
        )
        return dict(self.stats)

    @abstractmethod
    def get_list_urls(self) -> list[str]:
        """Return list of listing page URLs to crawl."""
        ...
