# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import hashlib
import json
import logging
import re
from datetime import datetime, timezone

from itemadapter import ItemAdapter

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
                raise DropItem(f"Duplicate item found: {url}")
            self.seen_urls.add(url_hash)
            adapter["checksum"] = url_hash
        return item


class FieldNormalizerPipeline:
    """Normalize and clean scraped field values."""

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # --- Price normalization ---
        price = adapter.get("price")
        if price is not None:
            try:
                adapter["price"] = float(re.sub(r"[^\d.]", "", str(price)))
            except (ValueError, TypeError):
                adapter["price"] = None

        # --- Bedrooms / Bathrooms normalization ---
        for field in ("bedrooms", "bathrooms", "parking", "floor_number", "total_floors"):
            val = adapter.get(field)
            if val is not None:
                try:
                    adapter[field] = int(float(re.sub(r"[^\d.]", "", str(val))))
                except (ValueError, TypeError):
                    adapter[field] = None

        # --- Floor area / land area normalization ---
        for field in ("floor_area", "land_area"):
            val = adapter.get(field)
            if val is not None:
                try:
                    adapter[field] = float(re.sub(r"[^\d.]", "", str(val)))
                except (ValueError, TypeError):
                    adapter[field] = None

        # --- Timestamps ---
        adapter["crawled_at"] = datetime.now(timezone.utc).isoformat()

        # --- Title cleaning ---
        title = adapter.get("title")
        if title:
            adapter["title"] = title.strip()

        # --- Description cleaning ---
        desc = adapter.get("description")
        if desc:
            adapter["description"] = re.sub(r"\s+", " ", desc).strip()

        # --- Amenities dedup ---
        amenities = adapter.get("amenities")
        if amenities and isinstance(amenities, list):
            adapter["amenities"] = sorted(set(a.strip() for a in amenities if a.strip()))

        # --- Images dedup ---
        images = adapter.get("images")
        if images and isinstance(images, list):
            adapter["images"] = list(dict.fromkeys(images))  # preserve order, remove dupes

        # --- Defaults ---
        if not adapter.get("currency"):
            adapter["currency"] = "THB"
        if not adapter.get("listing_type"):
            adapter["listing_type"] = "sale"

        return item


class DatabasePipeline:
    """Persist cleaned items to the database.

    This is a stub — implement actual DB insertion logic here.
    """

    def __init__(self):
        pass

    def open_spider(self, spider):
        logger.info("DatabasePipeline: spider opened — ready to persist items.")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        logger.debug(
            "Item ready for DB: source=%s source_id=%s title=%s",
            adapter.get("source"),
            adapter.get("source_id"),
            adapter.get("title"),
        )
        # TODO: insert/update into database via SQLAlchemy session
        return item

    def close_spider(self, spider):
        logger.info("DatabasePipeline: spider closed — flushing items.")


class DropItem(Exception):
    """Signal to drop an item from the pipeline."""
