#!/usr/bin/env python3
"""
清迈房产比价平台 — 代理 API 爬取系统

通过代理 API（ScrapingAnt 等）获取真实网站 HTML，解析并写入数据库。
不需要 Playwright 或系统依赖。

用法:
    # 1. 先注册 ScrapingAnt 获取免费 API Key
    #    https://scrapingant.com  → 注册 → 获取 API Key
    
    # 2. 设置 API Key
    export SCRAPINGANT_API_KEY=your_key_here

    # 3. 运行爬取
    python proxy_crawl.py                          # 爬取全部站点
    python proxy_crawl.py --spider fazwaz          # 仅爬取 FazWaz
    python proxy_crawl.py --spider ddproperty,hipflat
    python proxy_crawl.py --pages 3                # 每站爬 3 页
    python proxy_crawl.py --discover               # 发现模式（查看页面结构）
    python proxy_crawl.py --spider fazwaz --service scrapingbee
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("proxy-crawl")


def setup_django_path():
    """确保可以导入 backend 模块"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def discover(spider_name: str, adapter, parser, pages: int = 1):
    """发现模式：获取页面并分析 HTML 结构"""
    from proxy_crawler.parsers import PARSERS

    p = PARSERS[spider_name]
    logger.info(f"🔍 发现模式: {spider_name}")

    site_configs = {
        "ddproperty": {
            "list_urls": [
                "https://www.ddproperty.com/ให้เช่า/เชียงใหม่",
                "https://www.ddproperty.com/ขาย/เชียงใหม่",
            ],
            "detail_url": None,
        },
        "hipflat": {
            "list_urls": [
                "https://www.hipflat.co.th/en/condo-for-rent/chiang-mai",
                "https://www.hipflat.co.th/en/condo-for-sale/chiang-mai",
                "https://www.hipflat.co.th/en/house-for-rent/chiang-mai",
                "https://www.hipflat.co.th/en/house-for-sale/chiang-mai",
            ],
            "detail_url": None,
        },
        "fazwaz": {
            "list_urls": [
                "https://www.fazwaz.com/property-for-rent/chiang-mai",
                "https://www.fazwaz.com/property-for-sale/chiang-mai",
            ],
            "detail_url": None,
        },
        "dotproperty": {
            "list_urls": [
                "https://www.dotproperty.co.th/en/condos-for-rent/chiang-mai",
                "https://www.dotproperty.co.th/en/houses-for-rent/chiang-mai",
                "https://www.dotproperty.co.th/en/condos-for-sale/chiang-mai",
                "https://www.dotproperty.co.th/en/houses-for-sale/chiang-mai",
                "https://www.dotproperty.co.th/en/apartments-for-rent/chiang-mai",
                "https://www.dotproperty.co.th/en/townhouses-for-rent/chiang-mai",
                "https://www.dotproperty.co.th/en/villas-for-rent/chiang-mai",
            ],
            "detail_url": None,
        },
        "propertyhub": {
            "list_urls": [
                "https://propertyhub.in.th/en/condo-for-rent/chiang-mai",
                "https://propertyhub.in.th/en/condo-for-sale/chiang-mai",
            ],
            "detail_url": None,
        },
    }

    config = site_configs.get(spider_name, {"list_urls": [], "detail_url": None})

    for url in config["list_urls"]:
        logger.info(f"\n📡 获取: {url}")
        html = adapter.fetch(url)

        if not html:
            logger.warning("  ⚠️  获取失败，跳过")
            continue

        # 保存 HTML 样本供分析
        sample_file = f"/tmp/{spider_name}_sample_{datetime.utcnow().strftime('%H%M%S')}.html"
        with open(sample_file, "w") as f:
            f.write(html)
        logger.info(f"  💾 HTML 样本已保存: {sample_file} ({len(html)} bytes)")

        # 尝试提取列表
        urls = p.parse_list_urls(html, url)
        if urls:
            logger.info(f"  📋 提取到 {len(urls)} 个房源链接:")
            for u in urls[:5]:
                logger.info(f"    - {u}")
        else:
            logger.warning("  ⚠️  未提取到房源链接，可能需要调整选择器")
            # 打印页面前 2000 字符帮助调试
            logger.info("  📄 页面开头: %s...", html[:500].replace("\n", " "))

        # 翻页
        next_page = p.parse_next_page(html, url)
        if next_page:
            logger.info(f"  ➡️ 下一页: {next_page}")
        else:
            logger.info("  ⏹️  无下一页")


def crawl(spider_name: str, adapter, parser, pages: int = 5, db_session=None):
    """爬取模式：获取页面 → 解析 → 写入数据库"""
    from proxy_crawler.parsers import PARSERS

    p = PARSERS[spider_name]
    logger.info(f"🚀 爬取模式: {spider_name}, 最多 {pages} 页")

    # Site-specific start URLs
    start_urls = {
        "ddproperty": [
            "https://www.ddproperty.com/ให้เช่า/เชียงใหม่",
            "https://www.ddproperty.com/ขาย/เชียงใหม่",
        ],
        "hipflat": [
            "https://www.hipflat.co.th/en/condo-for-rent/chiang-mai",
            "https://www.hipflat.co.th/en/condo-for-sale/chiang-mai",
            "https://www.hipflat.co.th/en/house-for-rent/chiang-mai",
            "https://www.hipflat.co.th/en/house-for-sale/chiang-mai",
        ],
        "fazwaz": [
            "https://www.fazwaz.com/property-for-rent/chiang-mai",
            "https://www.fazwaz.com/property-for-sale/chiang-mai",
        ],
        "dotproperty": [
            "https://www.dotproperty.co.th/en/condos-for-rent/chiang-mai",
            "https://www.dotproperty.co.th/en/houses-for-rent/chiang-mai",
            "https://www.dotproperty.co.th/en/condos-for-sale/chiang-mai",
            "https://www.dotproperty.co.th/en/houses-for-sale/chiang-mai",
            "https://www.dotproperty.co.th/en/apartments-for-rent/chiang-mai",
            "https://www.dotproperty.co.th/en/townhouses-for-rent/chiang-mai",
            "https://www.dotproperty.co.th/en/villas-for-rent/chiang-mai",
        ],
        "propertyhub": [
            "https://propertyhub.in.th/en/condo-for-rent/chiang-mai",
            "https://propertyhub.in.th/en/condo-for-sale/chiang-mai",
        ],
    }

    all_properties = []
    processed_urls = set()

    for start_url in start_urls.get(spider_name, []):
        current_url = start_url
        page_num = 0

        while current_url and page_num < pages:
            page_num += 1
            logger.info(f"\n📄 第 {page_num} 页: {current_url}")

            html = adapter.fetch(current_url)
            if not html:
                logger.warning("  ⚠️  获取失败，跳到下一 URL")
                break

            # Extract listing URLs from list page
            listing_urls = p.parse_list_urls(html, current_url)

            if not listing_urls:
                logger.warning("  ⚠️  未找到房源链接，可能页面结构有变")
                break

            # Crawl each listing detail
            for idx, listing_url in enumerate(listing_urls):
                if listing_url in processed_urls:
                    continue
                processed_urls.add(listing_url)

                logger.info(f"  [{idx+1}/{len(listing_urls)}] 获取详情: {listing_url[:60]}...")

                detail_html = adapter.fetch(listing_url, wait_for_selector="h1")
                if not detail_html:
                    continue

                property_data = p.parse_listing(detail_html, listing_url)
                if property_data:
                    all_properties.append(property_data)

                # Rate limit between listings
                import time
                time.sleep(2.0)

            # Next page
            current_url = p.parse_next_page(html, current_url)
            if current_url:
                import time
                time.sleep(1)

    # Save to database
    if db_session and all_properties:
        _save_to_db(db_session, all_properties, spider_name)

    # Save to JSON backup
    if all_properties:
        backup_file = f"/tmp/{spider_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(all_properties, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 JSON 备份: {backup_file} ({len(all_properties)} 条)")

    logger.info(f"\n✅ {spider_name}: 共获取 {len(all_properties)} 条房源")
    return all_properties


def _save_to_db(session, properties: list, source: str):
    """将数据写入数据库"""
    from sqlalchemy import text

    saved = 0
    for prop in properties:
        try:
            existing = session.execute(
                text("SELECT id FROM properties WHERE source = :s AND source_id = :sid"),
                {"s": source, "sid": prop.get("source_id", "")},
            ).fetchone()

            if existing:
                # Update
                session.execute(
                    text("""
                        UPDATE properties SET
                            title = :title, description = :desc,
                            price_rent = :price_rent, price_sale = :price_sale,
                            bedrooms = :beds, bathrooms = :baths,
                            area_sqm = :area, floor = :floor,
                            total_floors = :tfloors, furnished = :furnished,
                            property_type = :ptype, address = :addr,
                            district = :district, lat = :lat, lng = :lng,
                            images = :images, updated_at = :now
                        WHERE source = :source AND source_id = :source_id
                    """),
                    {
                        "title": prop.get("title", ""),
                        "desc": prop.get("description", ""),
                        "price_rent": prop.get("price") if prop.get("listing_type", "").upper() == "RENT" else None,
                        "price_sale": prop.get("price") if prop.get("listing_type", "").upper() == "SALE" else None,
                        "beds": prop.get("bedrooms"),
                        "baths": prop.get("bathrooms"),
                        "area": prop.get("floor_area"),
                        "floor": prop.get("floor_number"),
                        "tfloors": prop.get("total_floors"),
                        "furnished": prop.get("furnishing") and "Fully" in str(prop.get("furnishing", "")),
                        "ptype": prop.get("property_type", "CONDO"),
                        "addr": prop.get("location_name", ""),
                        "district": prop.get("district", ""),
                        "lat": prop.get("latitude"),
                        "lng": prop.get("longitude"),
                        "images": json.dumps(prop.get("images", [])),
                        "source": source,
                        "source_id": prop.get("source_id", ""),
                        "now": datetime.utcnow(),
                    },
                )
                logger.debug(f"  🔄 更新: {prop.get('title', '')[:30]}")
            else:
                # Insert
                session.execute(
                    text("""
                        INSERT INTO properties (
                            title, description, price_rent, price_sale, currency,
                            price_type, bedrooms, bathrooms, area_sqm, floor,
                            total_floors, furnished, property_type, address,
                            district, lat, lng, source, source_url, source_id,
                            images, is_active, posted_date, scraped_at, updated_at
                        ) VALUES (
                            :title, :desc, :price_rent, :price_sale, 'THB',
                            :price_type, :beds, :baths, :area, :floor,
                            :tfloors, :furnished, :ptype, :addr,
                            :district, :lat, :lng, :source, :url, :source_id,
                            :images, 1, :now, :scraped, :now
                        )
                    """),
                    {
                        "title": prop.get("title", ""),
                        "desc": prop.get("description", ""),
                        "price_rent": prop.get("price") if prop.get("listing_type", "").upper() == "RENT" else None,
                        "price_sale": prop.get("price") if prop.get("listing_type", "").upper() == "SALE" else None,
                        "price_type": prop.get("listing_type", "SALE"),
                        "beds": prop.get("bedrooms"),
                        "baths": prop.get("bathrooms"),
                        "area": prop.get("floor_area"),
                        "floor": prop.get("floor_number"),
                        "tfloors": prop.get("total_floors"),
                        "furnished": prop.get("furnishing") and "Fully" in str(prop.get("furnishing", "")),
                        "ptype": prop.get("property_type", "CONDO"),
                        "addr": prop.get("location_name", ""),
                        "district": prop.get("district", ""),
                        "lat": prop.get("latitude"),
                        "lng": prop.get("longitude"),
                        "source": source,
                        "url": prop.get("source_url", ""),
                        "source_id": prop.get("source_id", ""),
                        "images": json.dumps(prop.get("images", [])),
                        "now": datetime.utcnow(),
                        "scraped": datetime.utcnow(),
                    },
                )
                logger.debug(f"  ✅ 新增: {prop.get('title', '')[:30]}")
            saved += 1
        except Exception as e:
            session.rollback()
            logger.error(f"  ❌ 数据库写入失败: {e}")

    session.commit()
    logger.info(f"📦 数据库写入完成: {saved}/{len(properties)} 条")


def main():
    parser = argparse.ArgumentParser(description="代理 API 爬取系统")
    parser.add_argument("--spider", "-s", default="all",
                        help="爬虫: ddproperty, hipflat, fazwaz, all (默认)")
    parser.add_argument("--pages", "-p", type=int, default=2,
                        help="每站最大页数 (默认: 2)")
    parser.add_argument("--service", default="scrapingant",
                        help="代理服务: scrapingant (默认), scrapingbee, scrapingfish, zenrows, crawlbase")
    parser.add_argument("--discover", action="store_true",
                        help="发现模式: 获取页面结构，不写入数据库")
    parser.add_argument("--api-key", default=None,
                        help="API Key (默认从环境变量读取)")
    args = parser.parse_args()

    # Setup
    setup_django_path()
    from proxy_crawler.proxy_adapter import ProxyAdapter
    from proxy_crawler.parsers import PARSERS

    adapter = ProxyAdapter(service=args.service, api_key=args.api_key)

    if args.spider == "all":
        spider_names = ["ddproperty", "hipflat", "fazwaz"]
    else:
        spider_names = [s.strip() for s in args.spider.split(",")]

    logger.info("=" * 60)
    logger.info(f"🏠 清迈房产代理爬取系统")
    logger.info(f"   爬虫: {', '.join(spider_names)}")
    logger.info(f"   代理服务: {args.service}")
    logger.info(f"   模式: {'发现' if args.discover else '爬取'}")
    logger.info(f"   最大页数: {args.pages}")
    logger.info("=" * 60)

    # Database connection for crawl mode
    db_session = None
    if not args.discover:
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from crawlers.settings import DATABASE_URL

            engine = create_engine(DATABASE_URL)
            db_session = sessionmaker(bind=engine)()
            logger.info(f"✅ 数据库已连接: {DATABASE_URL.split('://')[0]}://...")
        except Exception as e:
            logger.warning(f"⚠️  数据库连接失败: {e}，将仅保存 JSON")

    # Run
    for name in spider_names:
        if name not in PARSERS:
            logger.warning(f"⚠️  跳过未知爬虫: {name}")
            continue

        if args.discover:
            discover(name, adapter, PARSERS[name], args.pages)
        else:
            crawl(name, adapter, PARSERS[name], args.pages, db_session)

    if db_session:
        db_session.close()

    logger.info("\n✅ 全部完成！")


if __name__ == "__main__":
    main()
