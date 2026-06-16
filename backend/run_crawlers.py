#!/usr/bin/env python3
"""Unified crawler entry point — run all or specific crawlers.

Usage:
    python backend/run_crawlers.py                    # Run all crawlers (default: incremental)
    python backend/run_crawlers.py --incremental      # Skip recently crawled sources
    python backend/run_crawlers.py --full             # Full crawl of all sources
    python backend/run_crawlers.py --source hipflat   # Run single source
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("run-crawlers")

# ── Crawler registry ─────────────────────────────────────────────

CRAWLERS = []


def _register_crawlers():
    global CRAWLERS
    from proxy_crawler.hipflat_crawler import HipflatCrawler
    from proxy_crawler.fazwaz_crawler import FazwazCrawler
    from proxy_crawler.livingstock_crawler import LivingstockCrawler
    CRAWLERS = [
        HipflatCrawler(),
        FazwazCrawler(),
        LivingstockCrawler(),
    ]


# ── Stats ────────────────────────────────────────────────────────


def _save_stats(all_stats: list[dict]) -> None:
    """Save crawl stats to data/crawl_stats_YYYYMMDD.json"""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"crawl_stats_{datetime.utcnow().strftime('%Y%m%d')}.json")
    existing = []
    if os.path.exists(path):
        try:
            with open(path) as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.append({
        "timestamp": datetime.utcnow().isoformat(),
        "sources": all_stats,
    })
    with open(path, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    logger.info("Stats saved to %s", path)


def _should_skip(source: str, incremental: bool) -> bool:
    """Check if source was crawled recently (within 6 hours)."""
    if not incremental:
        return False
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    stats_path = os.path.join(data_dir, f"crawl_stats_{datetime.utcnow().strftime('%Y%m%d')}.json")
    if not os.path.exists(stats_path):
        return False
    try:
        with open(stats_path) as f:
            stats = json.load(f)
        for entry in reversed(stats):
            for s in entry.get("sources", []):
                if s.get("source") == source:
                    ts = datetime.fromisoformat(entry["timestamp"])
                    if datetime.utcnow() - ts < timedelta(hours=6):
                        logger.info("Skipping %s (crawled at %s)", source, ts.isoformat())
                        return True
    except Exception:
        pass
    return False


def main():
    parser = argparse.ArgumentParser(description="Run property crawlers")
    parser.add_argument("--incremental", action="store_true", help="Skip recently crawled")
    parser.add_argument("--full", action="store_true", help="Full crawl of all")
    parser.add_argument("--source", type=str, help="Run single source by name")
    args = parser.parse_args()

    _register_crawlers()
    incremental = args.incremental or not args.full
    all_stats = []

    for crawler in CRAWLERS:
        if args.source and crawler.SOURCE != args.source:
            continue
        if _should_skip(crawler.SOURCE, incremental):
            continue

        logger.info("=" * 50)
        logger.info("Starting crawl: %s", crawler.SOURCE)
        try:
            stats = crawler.crawl()
            all_stats.append(stats)
            logger.info(
                "Done: %s — new=%d updated=%d errors=%d (%.1fs)",
                stats["source"], stats["new"], stats["updated"],
                len(stats["errors"]), stats["duration_seconds"],
            )
        except Exception as e:
            logger.error("Crawl failed for %s: %s", crawler.SOURCE, e)
            all_stats.append({"source": crawler.SOURCE, "error": str(e)[:200]})

    if all_stats:
        _save_stats(all_stats)

    logger.info("All crawls complete.")


if __name__ == "__main__":
    main()
