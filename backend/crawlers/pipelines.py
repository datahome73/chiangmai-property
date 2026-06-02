import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone

from itemadapter import ItemAdapter
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from crawlers.items import PropertyItem

logger = logging.getLogger(__name__)


class DuplicateFilterPipeline:
    """Drop duplicate items based on URL checksum."""

    def __init__(self):
        self.seen_urls = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        url = adapter.get("url")
        if url:
            url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
            if url_hash in self.seen_urls:
                from scrapy.exceptions import DropItem
                raise DropItem(f"Duplicate item found: {url}")
            self.seen_urls.add(url_hash)
            adapter["checksum"] = url_hash
        return item


class FieldNormalizerPipeline:
    """Normalize and clean scraped field values."""

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Price normalization
        price = adapter.get("price")
        if price is not None:
            try:
                adapter["price"] = float(re.sub(r"[^\d.]", "", str(price)))
            except (ValueError, TypeError):
                adapter["price"] = None

        # Integer fields
        for field in ("bedrooms", "bathrooms", "parking", "floor_number", "total_floors"):
            val = adapter.get(field)
            if val is not None:
                try:
                    adapter[field] = int(float(re.sub(r"[^\d.]", "", str(val))))
                except (ValueError, TypeError):
                    adapter[field] = None

        # Float fields
        for field in ("floor_area", "land_area", "latitude", "longitude"):
            val = adapter.get(field)
            if val is not None:
                try:
                    adapter[field] = float(re.sub(r"[^\d.]", "", str(val)))
                except (ValueError, TypeError):
                    adapter[field] = None

        # Timestamps
        adapter["crawled_at"] = datetime.now(timezone.utc).isoformat()

        # Title/description cleaning
        title = adapter.get("title")
        if title:
            adapter["title"] = title.strip()
        desc = adapter.get("description")
        if desc:
            adapter["description"] = re.sub(r"\s+", " ", desc).strip()

        # Amenities dedup
        amenities = adapter.get("amenities")
        if amenities and isinstance(amenities, list):
            adapter["amenities"] = sorted(set(a.strip() for a in amenities if a.strip()))

        # Images dedup
        images = adapter.get("images")
        if images and isinstance(images, list):
            adapter["images"] = list(dict.fromkeys(images))

        # Defaults
        if not adapter.get("currency"):
            adapter["currency"] = "THB"
        if not adapter.get("listing_type"):
            adapter["listing_type"] = "sale"

        # Set crawling timestamp
        adapter["crawled_at"] = datetime.now(timezone.utc).isoformat()

        return item


class DatabasePipeline:
    """Persist cleaned items to the application database.

    Features:
      - Connection health check before each batch
      - Auto-reconnect on stale/broken connections
      - Retry logic for transient DB errors
      - Graceful degradation: log error + continue on DB failure
    """

    def __init__(self):
        self.engine = None
        self.SessionLocal = None

    def open_spider(self, spider):
        """Connect to the database at spider start."""
        from crawlers.settings import DATABASE_URL as db_url

        logger.info("🔌 DatabasePipeline connecting to: %s", db_url)
        if not self._connect(db_url):
            logger.error("❌ DatabasePipeline: initial connection failed, will retry per item")

    def _connect(self, db_url):
        """Establish database connection with proper settings."""
        try:
            if db_url.startswith("sqlite"):
                self.engine = create_engine(
                    db_url,
                    echo=False,
                    connect_args={"check_same_thread": False},
                )
            else:
                self.engine = create_engine(
                    db_url,
                    echo=False,
                    pool_pre_ping=True,       # Check connection before use
                    pool_recycle=3600,         # Recycle connections after 1 hour
                    pool_size=5,
                    max_overflow=2,
                )
            # Test the connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.SessionLocal = sessionmaker(bind=self.engine)
            logger.info("✅ DatabasePipeline connected")
            return True
        except Exception as e:
            logger.error("❌ DatabasePipeline connection failed: %s", e)
            self.engine = None
            self.SessionLocal = None
            return False

    def _ensure_connection(self):
        """Verify connection is alive and re-establish if stale."""
        if not self.engine:
            return False
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning("⚠️  DB connection stale, reconnecting... (%s)", e)
            from crawlers.settings import DATABASE_URL as db_url
            return self._connect(db_url)

    def close_spider(self, spider):
        if self.engine:
            self.engine.dispose()
            logger.info("DatabasePipeline: connection closed")

    def process_item(self, item, spider):
        if not self.SessionLocal:
            logger.warning("DatabasePipeline: no DB session, skipping item")
            return item

        # Ensure connection is alive before processing
        self._ensure_connection()

        adapter = ItemAdapter(item)
        source = adapter.get("source", "")
        source_id = adapter.get("source_id", "")
        url = adapter.get("url", "")

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            session = self.SessionLocal()
            try:
                # Check if property already exists by source + source_id
                existing = session.execute(
                    text("SELECT id FROM properties WHERE source = :s AND source_id = :sid"),
                    {"s": source, "sid": source_id},
                ).fetchone()

                if existing:
                    # Update existing
                    prop_id = existing[0]
                    session.execute(
                        text("""
                            UPDATE properties SET
                                title = :title, description = :desc,
                                price_rent = :price_rent, price_sale = :price_sale,
                                bedrooms = :beds, bathrooms = :baths,
                                area_sqm = :area, floor = :floor,
                                total_floors = :tfloors, furnished = :furnished,
                                property_type = :ptype, address = :addr,
                                district = :district, sub_district = :sub_district,
                                lat = :lat, lng = :lng,
                                images = :images, updated_at = :now
                            WHERE id = :id
                        """),
                        {
                            "id": prop_id,
                            "title": adapter.get("title", ""),
                            "desc": adapter.get("description", ""),
                            "price_rent": adapter.get("price") if adapter.get("listing_type") == "rent" else None,
                            "price_sale": adapter.get("price") if adapter.get("listing_type") == "sale" else None,
                            "beds": adapter.get("bedrooms"),
                            "baths": adapter.get("bathrooms"),
                            "area": adapter.get("floor_area"),
                            "floor": adapter.get("floor_number"),
                            "tfloors": adapter.get("total_floors"),
                            "furnished": adapter.get("furnishing") and "Fully" in str(adapter.get("furnishing", "")),
                            "ptype": adapter.get("property_type", "condo"),
                            "addr": adapter.get("location_name", ""),
                            "district": adapter.get("district", ""),
                            "sub_district": adapter.get("subdistrict", ""),
                            "lat": adapter.get("latitude"),
                            "lng": adapter.get("longitude"),
                            "images": json.dumps(adapter.get("images", [])),
                            "now": datetime.utcnow(),
                        },
                    )
                    logger.info("🔄 Updated property %s/%s (id=%s)", source, source_id, prop_id)
                else:
                    # Insert new
                    session.execute(
                        text("""
                            INSERT INTO properties (
                                title, description, price_rent, price_sale, currency,
                                price_type, bedrooms, bathrooms, area_sqm, floor,
                                total_floors, furnished, property_type, address,
                                district, sub_district, lat, lng,
                                source, source_url, source_id, images,
                                is_active, posted_date, scraped_at, updated_at
                            ) VALUES (
                                :title, :desc, :price_rent, :price_sale, :currency,
                                :price_type, :beds, :baths, :area, :floor,
                                :tfloors, :furnished, :ptype, :addr,
                                :district, :sub_district, :lat, :lng,
                                :source, :url, :source_id, :images,
                                1, :posted, :scraped, :now
                            )
                        """),
                        {
                            "title": adapter.get("title", ""),
                            "desc": adapter.get("description", ""),
                            "price_rent": adapter.get("price") if adapter.get("listing_type") == "rent" else None,
                            "price_sale": adapter.get("price") if adapter.get("listing_type") == "sale" else None,
                            "currency": adapter.get("currency", "THB"),
                            "price_type": adapter.get("listing_type", "sale"),
                            "beds": adapter.get("bedrooms"),
                            "baths": adapter.get("bathrooms"),
                            "area": adapter.get("floor_area"),
                            "floor": adapter.get("floor_number"),
                            "tfloors": adapter.get("total_floors"),
                            "furnished": bool(adapter.get("furnishing") and "Fully" in str(adapter.get("furnishing", ""))),
                            "ptype": adapter.get("property_type", "condo"),
                            "addr": adapter.get("location_name", ""),
                            "district": adapter.get("district", ""),
                            "sub_district": adapter.get("subdistrict", ""),
                            "lat": adapter.get("latitude"),
                            "lng": adapter.get("longitude"),
                            "source": source,
                            "url": url,
                            "source_id": source_id,
                            "images": json.dumps(adapter.get("images", [])),
                            "posted": datetime.utcnow(),
                            "scraped": datetime.utcnow(),
                            "now": datetime.utcnow(),
                        },
                    )
                    logger.info("✅ Inserted new property %s/%s", source, source_id)

                session.commit()

                # Also insert price history if price changed
                if existing:
                    self._record_price_history(session, existing[0], adapter)

                break  # Success — exit retry loop

            except Exception as e:
                session.rollback()
                logger.error("❌ DB error (attempt %d/%d) for %s: %s", attempt, max_attempts, url, e)
                if attempt < max_attempts:
                    logger.info("   Retrying DB write...")
                    from crawlers.settings import DATABASE_URL as db_url
                    self._ensure_connection()
                    continue
                # Last attempt failed — still return item to prevent pipeline break
            finally:
                session.close()

        return item

    def _record_price_history(self, session, prop_id, adapter):
        """Record to price_history if price seems to have changed."""
        pass  # TODO: compare old price, insert if different
