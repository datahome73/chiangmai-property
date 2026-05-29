#!/usr/bin/env python3
"""
清迈房产比价平台 — 爬虫运行脚本

一键运行所有爬虫，或指定特定爬虫。
支持 Playwright 渲染和数据库写入。

用法:
    python run_crawlers.py                          # 运行全部爬虫
    python run_crawlers.py --spider ddproperty      # 仅运行 ddproperty
    python run_crawlers.py --spider hipflat,fazwaz  # 仅运行 hipflat + fazwaz
    python run_crawlers.py --pages 5                # 每站只抓5页
    python run_crawlers.py --sale                   # 仅抓出售
    python run_crawlers.py --rent                   # 仅抓出租（默认）
    python run_crawlers.py --both                   # 抓出租+出售
"""

import argparse
import logging
import os
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("crawler-runner")


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
    args = parser.parse_args()

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
    logger.info("=" * 60)
    logger.info("🏠 清迈房产爬虫启动")
    logger.info(f"   爬虫: {', '.join(spider_names)}")
    logger.info(f"   类型: {', '.join(listing_types)}")
    logger.info(f"   最大页数: {args.pages}")
    logger.info(f"   Playwright: {'✅' if args.playwright else '❌'}")
    logger.info(f"   输出: {'数据库' if not args.output else args.output}")
    logger.info("=" * 60)

    # Verify Playwright availability
    if args.playwright:
        try:
            from playwright.sync_api import sync_playwright
            p = sync_playwright().start()
            browser = p.chromium.launch(headless=True)
            browser.close()
            p.stop()
            logger.info("✅ Playwright Chromium 可用")
        except Exception as e:
            logger.warning("⚠️  Playwright 不可用 (%s)，将尝试 HTTP 模式", e)

    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    # Build Scrapy settings
    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "crawlers.settings")

    process = CrawlerProcess(get_project_settings())

    # Import spider classes
    from crawlers.spiders.ddproperty import DdpropertySpider
    from crawlers.spiders.hipflat import HipflatSpider
    from crawlers.spiders.fazwaz import FazwazSpider

    spider_map = {
        "ddproperty": DdpropertySpider,
        "hipflat": HipflatSpider,
        "fazwaz": FazwazSpider,
    }

    for name in spider_names:
        if name not in spider_map:
            logger.warning("⚠️  未知爬虫: %s (可选: %s)", name, ", ".join(spider_map.keys()))
            continue

        logger.info(f"🚀 启动爬虫: {name}")
        if args.output:
            process.crawl(
                spider_map[name],
                rent="rent" in listing_types,
                sale="sale" in listing_types,
                max_pages=args.pages,
            )
        else:
            process.crawl(
                spider_map[name],
                rent="rent" in listing_types,
                sale="sale" in listing_types,
                max_pages=args.pages,
            )

    process.start()

    logger.info("=" * 60)
    logger.info("✅ 爬虫运行完毕!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
