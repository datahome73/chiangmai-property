"""
清迈房产比价平台 — 种子数据注入脚本
运行: python seed_data.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import random
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine, async_session_factory, Base
from app.models.property import Property, PriceHistory, User, Favorite, Comparison, PriceType, PropertyType

# 清迈区域数据
DISTRICTS = [
    ("古城", "Old City", 18.7883, 98.9853),
    ("宁曼路", "Nimman", 18.8000, 98.9680),
    ("长康路", "Chang Klan", 18.7800, 98.9980),
    ("杭东", "Hang Dong", 18.6870, 98.9190),
    ("讪赛", "San Sai", 18.8500, 99.0500),
    ("湄林", "Mae Rim", 18.9000, 98.9500),
    ("山甘烹", "San Kamphaeng", 18.7400, 99.1200),
    ("沙拉丕", "Saraphi", 18.7000, 99.0100),
    ("东岸", "Fa Ham", 18.8200, 99.0200),
    ("清迈大学附近", "CMU Area", 18.8050, 98.9550),
]

PROJECT_NAMES = [
    "Supalai Monte @Nimman", "The Astra Condo", "D Condo Sign",
    "Punna Oasis Town", "Hillside Plaza Condotel", "The Punna Classic",
    "Burasiri San Sai", "Hypo Central Suites", "The Shine Nimman",
    "The Unique at Nimman", "Supalai Oasis", "Green Hill Place",
    "Baan Tawai Wood", "The Bliss Condo", "Laguna Homes Hang Dong",
    "Punna Garden Home", "Baan Kachana", "Supalai Bella",
    "The Spring Condo", "My Hip Condo",
]

SOURCES = ["ddproperty", "hipflat", "fazwaz"]

RENT_PRICES = [5000, 8000, 10000, 12000, 15000, 18000, 22000, 28000, 35000, 45000]
SALE_PRICES = [1500000, 2000000, 2800000, 3500000, 4500000, 5500000, 7000000, 8900000, 12000000, 18000000]
SQM_VALUES = [25, 30, 35, 40, 45, 50, 60, 75, 90, 110, 140, 180]
BEDROOM_OPTIONS = [1, 1, 2, 2, 2, 3, 3, 4]
PROPERTY_TYPES = [PropertyType.CONDO, PropertyType.CONDO, PropertyType.HOUSE,
                  PropertyType.TOWNHOUSE, PropertyType.APARTMENT, PropertyType.CONDO]


async def seed():
    """注入种子数据"""
    # 清空旧数据
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Clear existing data
        for table in [PriceHistory, Favorite, Comparison, Property, User]:
            await db.execute(table.__table__.delete())

        # 创建 50 条房产数据
        properties = []
        for i in range(50):
            district_name, district_en, base_lat, base_lng = random.choice(DISTRICTS)
            is_rent = random.random() > 0.35
            bedrooms = random.choice(BEDROOM_OPTIONS)
            bathrooms = min(bedrooms + random.choice([0, 1, 1]), 5)
            area = random.choice(SQM_VALUES)
            rent_price = random.choice(RENT_PRICES) if is_rent else None
            sale_price = random.choice(SALE_PRICES) if not is_rent else None
            posted = datetime.utcnow() - timedelta(days=random.randint(0, 60))

            prop = Property(
                title=f"{district_name} — {random.choice(PROJECT_NAMES)}",
                description=f"{bedrooms}卧{bathrooms}卫，位于{district_name}核心区域，"
                           f"周边配套齐全，交通便利。步行可达7-11、大型超市和公交站。",
                price_rent=rent_price,
                price_sale=sale_price,
                currency="THB",
                price_type=PriceType.RENT if is_rent else PriceType.SALE,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                area_sqm=area,
                floor=random.randint(1, 15),
                total_floors=random.randint(5, 18),
                furnished=random.random() > 0.2,
                property_type=random.choice(PROPERTY_TYPES),
                address=f"{district_name}区，清迈",
                district=district_name,
                sub_district=random.choice(["Pa Tan", "Suthep", "Chang Phueak", "Hai Ya", "Pa Daet"]),
                lat=base_lat + (random.random() - 0.5) * 0.03,
                lng=base_lng + (random.random() - 0.5) * 0.03,
                source=random.choice(SOURCES),
                source_url=f"https://example.com/property/{i}",
                source_id=f"seed_{i}",
                images=[f"https://picsum.photos/seed/cm{i}{ch}/800/500" for ch in ['a', 'b', 'c']],
                is_active=True,
                posted_date=posted,
            )
            db.add(prop)
            properties.append(prop)

        await db.flush()
        print(f"✅ 已创建 {len(properties)} 条房产数据")

        # 为部分房源添加价格历史
        for prop in properties[:20]:
            for days_ago in [30, 15, 7]:
                old_price = (prop.price_rent or prop.price_sale or 10000) * (1 + (random.random() - 0.5) * 0.2)
                ph = PriceHistory(
                    property_id=prop.id,
                    price_rent=old_price if prop.price_type == PriceType.RENT else None,
                    price_sale=old_price if prop.price_type == PriceType.SALE else None,
                    price_type=prop.price_type,
                    source=prop.source,
                    scraped_at=datetime.utcnow() - timedelta(days=days_ago),
                )
                db.add(ph)

        # 创建测试用户
        test_user = User(
            nickname="测试用户",
            phone="0881234567",
            password_hash="$2b$12$dummy",
            preferred_language="zh",
        )
        db.add(test_user)

        await db.commit()
        print("✅ 种子数据注入完成！")
        print(f"   房产: 50 条")
        print(f"   价格历史: 60 条")
        print(f"   区域: {len(DISTRICTS)} 个")
        print(f"   测试用户: 测试用户 (phone: 0881234567)")


if __name__ == "__main__":
    asyncio.run(seed())
