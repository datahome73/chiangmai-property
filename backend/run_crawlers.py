#!/usr/bin/env python3
"""
清迈房产比价平台 — 爬虫运行脚本

一键运行所有爬虫，或指定特定爬虫。
支持 Playwright 渲染和数据库写入。

用法:
    python run_crawlers.py                              # 运行全部爬虫
    python run_crawlers.py --spider ddproperty          # 仅运行 ddproperty
    python run_crawlers.py --spider hipflat,fazwaz      # 仅运行 hipflat + fazwaz
    python run_crawlers.py --pages 5                    # 每站只抓5页
    python run_crawlers.py --sale                       # 仅抓出售
    python run_crawlers.py --rent                       # 仅抓出租（默认）
    python run_crawlers.py --both                       # 抓出租+出售
"""

import argparse
import logging
import os
import sys
import time
import traceback
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("crawler-runner")


def check_database_connection():
    """Verify database is accessible before starting."""
    try:
        from crawlers.settings import DATABASE_URL as db_url
        from sqlalchemy import create_engine, text

        if not db_url:
            logger.warning("⚠️  DATABASE_URL 未设置，跳过数据库检查")
            return True

        # Use psycopg2 for sync connection check
        check_url = db_url
        if check_url.startswith("postgresql+asyncpg://"):
            check_url = check_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

        engine = create_engine(check_url, echo=False)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        logger.info("✅ 数据库连接正常")
        return True
    except Exception as e:
        logger.error("❌ 数据库连接失败: %s", e)
        logger.warning("   爬虫将继续运行，但数据可能无法写入数据库")
        return False


def verify_dependencies():
    """Check required packages and tools."""
    missing = []

    try:
        import scrapy  # noqa
    except ImportError:
        missing.append("scrapy")

    try:
        import sqlalchemy  # noqa
    except ImportError:
        missing.append("sqlalchemy")

    try:
        import httpx  # noqa
    except ImportError:
        missing.append("httpx")

    if missing:
        logger.error("❌ 缺少依赖包: %s", ", ".join(missing))
        logger.error("   请运行: pip install %s", " ".join(missing))
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="运行清迈房产爬虫")
    parser.add_argument("--spider", "-s", default="all",
                        help="爬虫名称: ddproperty, hipflat, fazwaz, 或 all (默认)")
    parser.add_argument("--pages", "-p", type=int, default=5,
                        help="每站最大抓取页数 (默认: 5)")
    parser.add_argument("--rent", action="store_true", default=True,
                        help="抓取出租房源")
    parser.add_argument("--sale", action="store_true", default=False,
                        help="抓取出售房源")
    parser.add_argument("--both", action="store_true", default=False,
                        help="抓取出租+出售")
    parser.add_argument("--output", "-o", default=None,
                        help="输出文件 (JSON/CSV)，默认写入数据库")
    parser.add_argument("--playwright", action="store_true", default=True,
                        help="使用 Playwright 渲染 JS (默认开启)")
    parser.add_argument("--skip-db-check", action="store_true", default=False,
                        help="跳过数据库连接检查")
    parser.add_argument("--timeout", type=int, default=600,
                        help="爬虫超时时间（秒，默认: 600）")
    args = parser.parse_args()

    # ── Pre-flight checks ──────────────────────────────
    logger.info("=" * 60)
    logger.info("🏠 清迈房产爬虫启动")
    logger.info(f"   时间: {datetime.now().isoformat()}")

    if not verify_dependencies():
        sys.exit(1)

    if not args.skip_db_check and not args.output:
        check_database_connection()

    # Resolve listing types
    listing_types = ["rent"]
    if args.sale:
        listing_types = ["sale"]
    if args.both:
        listing_types = ["rent", "sale"]

    # Determine spiders to run
    if args.spider == "all":
        spider_names = ["ddproperty", "hipflat", "fazwaz"]
    else:
        spider_names = [s.strip() for s in args.spider.split(",")]

    # Log summary
    logger.info(f"   爬虫: {', '.join(spider_names)}")
    logger.info(f"   类型: {', '.join(listing_types)}")
    logger.info(f"   最大页数: {args.pages}")
    logger.info(f"   Playwright: {'✅' if args.playwright else '❌'}")
    logger.info(f"   超时: {args.timeout}s")
    logger.info(f"   输出: {'数据库' if not args.output else args.output}")
    logger.info("=" * 60)

    # Verify Playwright availability
    playwright_ok = False
    if args.playwright:
        try:
            from playwright.sync_api import sync_playwright
            p = sync_playwright().start()
            browser = p.chromium.launch(headless=True, timeout=10000)
            browser.close()
            p.stop()
            playwright_ok = True
            logger.info("✅ Playwright Chromium 可用")
        except Exception as e:
            logger.warning("⚠️  Playwright 不可用 (%s)，将尝试 HTTP 模式", e)

    # ── Run spiders ───────────────────────────────────
    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "crawlers.settings")

    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    settings = get_project_settings()

    # Apply runtime overrides
    if args.timeout:
        settings.set("DOWNLOAD_TIMEOUT", min(args.timeout, 120))

    process = CrawlerProcess(settings)

    # Import spider classes
    from crawlers.spiders.ddproperty import DdpropertySpider
    from crawlers.spiders.hipflat import HipflatSpider
    from crawlers.spiders.fazwaz import FazwazSpider

    spider_map = {
        "ddproperty": DdpropertySpider,
        "hipflat": HipflatSpider,
        "fazwaz": FazwazSpider,
    }

    results = {}
    start_time = time.time()

    for name in spider_names:
        if name not in spider_map:
            logger.warning("⚠️  未知爬虫: %s (可选: %s)", name, ", ".join(spider_map.keys()))
            continue

        spider_start = time.time()
        logger.info("🚀 启动爬虫: %s", name)
        try:
            process.crawl(
                spider_map[name],
                rent="rent" in listing_types,
                sale="sale" in listing_types,
                max_pages=args.pages,
            )
            duration = time.time() - spider_start
            results[name] = {"status": "crawled", "duration": f"{duration:.1f}s"}
        except Exception as e:
            logger.error("❌ 爬虫 %s 启动失败: %s", name, e)
            logger.debug(traceback.format_exc())
            results[name] = {"status": f"failed: {e}", "duration": "0s"}

    # Execute all queued spiders
    try:
        process.start()
    except Exception as e:
        logger.error("❌ 爬虫执行异常: %s", e)
        logger.debug(traceback.format_exc())
        for name in spider_names:
            if name not in results:
                results[name] = {"status": "crashed", "duration": "0s"}
            elif results[name]["status"] == "crawled":
                results[name]["status"] = "crashed during execution"
    finally:
        total_duration = time.time() - start_time

    # ── Summary ───────────────────────────────────────
    logger.info("=" * 60)
    logger.info("📊 爬虫运行报告")
    logger.info(f"   总耗时: {total_duration:.1f}s")
    for name, result in results.items():
        status_icon = "✅" if "crawled" in result["status"] else "❌"
        logger.info(f"   {status_icon} {name}: {result['status']} ({result.get('duration', '?')})")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
