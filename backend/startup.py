"""
清迈房产比价平台 — 启动脚本（适用于 Railway 生产环境）
在启动 uvicorn 前，创建数据库表结构
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from sqlalchemy import text

from app.core.database import engine, Base


async def init_db():
    """创建表结构"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        result = await conn.execute(text("SELECT COUNT(*) FROM properties"))
        count = result.scalar()

    print(f"✅ 数据库就绪 ({count} 条房源数据)")


if __name__ == "__main__":
    asyncio.run(init_db())
