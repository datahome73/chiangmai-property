from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_

from app.models.property import Favorite, Comparison, Property


# ---- Favorites ----

async def get_user_favorites(
    db: AsyncSession,
    user_id: int,
) -> List[Favorite]:
    """查询用户的收藏列表（join property 表）。"""
    query = (
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def add_favorite(
    db: AsyncSession,
    user_id: int,
    property_id: int,
) -> Optional[Favorite]:
    """添加收藏，防止重复。返回 Favorite 对象或 None（已存在时返回已有的）。"""
    # Check if already favorited
    existing_result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.property_id == property_id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return existing

    fav = Favorite(user_id=user_id, property_id=property_id)
    db.add(fav)
    await db.flush()
    await db.refresh(fav)
    return fav


async def remove_favorite(
    db: AsyncSession,
    user_id: int,
    property_id: int,
) -> bool:
    """取消收藏。返回 True 如果成功删除，False 如果不存在。"""
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.property_id == property_id,
        )
    )
    fav = result.scalar_one_or_none()
    if not fav:
        return False

    await db.delete(fav)
    await db.flush()
    return True


# ---- Comparisons ----

async def get_user_comparisons(
    db: AsyncSession,
    user_id: int,
) -> List[Comparison]:
    """查询用户的比价集列表。"""
    query = (
        select(Comparison)
        .where(Comparison.user_id == user_id)
        .order_by(Comparison.created_at.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def save_comparison(
    db: AsyncSession,
    user_id: int,
    name: Optional[str],
    property_ids: List[int],
) -> Comparison:
    """保存比价集。"""
    comparison = Comparison(
        user_id=user_id,
        name=name,
        property_ids=property_ids,
    )
    db.add(comparison)
    await db.flush()
    await db.refresh(comparison)
    return comparison


async def delete_comparison(
    db: AsyncSession,
    user_id: int,
    comparison_id: int,
) -> bool:
    """删除比价集。返回 True 如果成功删除，False 如果不存在或不属于该用户。"""
    result = await db.execute(
        select(Comparison).where(
            Comparison.id == comparison_id,
            Comparison.user_id == user_id,
        )
    )
    comparison = result.scalar_one_or_none()
    if not comparison:
        return False

    await db.delete(comparison)
    await db.flush()
    return True
