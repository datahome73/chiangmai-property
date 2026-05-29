from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.property import Property, PriceType, PropertyType
from app.schemas.property import PropertyFilterParams


async def get_properties(
    db: AsyncSession,
    filters: PropertyFilterParams,
) -> Tuple[int, List[Property]]:
    """
    多条件查询房源列表。
    返回 (total_count, items)。
    """
    query = select(Property).where(Property.is_active == True)

    # --- Keyword filter on title ---
    if filters.keyword:
        query = query.where(Property.title.ilike(f'%{filters.keyword}%'))

    # --- Price type filter ---
    if filters.price_type:
        query = query.where(Property.price_type == PriceType(filters.price_type.value))

    # --- Property type filter ---
    if filters.property_type:
        query = query.where(Property.property_type == PropertyType(filters.property_type.value))

    # --- District filter ---
    if filters.district:
        query = query.where(Property.district.ilike(f'%{filters.district}%'))

    # --- Bedrooms filter ---
    if filters.bedrooms is not None:
        query = query.where(Property.bedrooms == int(filters.bedrooms))

    # --- Price range filter ---
    price_type_val = filters.price_type.value if filters.price_type else None
    if filters.min_price is not None or filters.max_price is not None:
        if price_type_val == "rent" or price_type_val is None:
            # Determine price column to filter
            price_col = Property.price_rent
            if filters.min_price is not None:
                query = query.where(price_col >= filters.min_price)
            if filters.max_price is not None:
                query = query.where(price_col <= filters.max_price)
        elif price_type_val == "sale":
            price_col = Property.price_sale
            if filters.min_price is not None:
                query = query.where(price_col >= filters.min_price)
            if filters.max_price is not None:
                query = query.where(price_col <= filters.max_price)
    # Note: when price_type is "both", the min/max price applies loosely — handled above by
    # falling through to price_rent as a reasonable default for the both case.

    # --- Sorting ---
    sort_col = Property.scraped_at  # default
    sort_asc = False  # default desc

    if filters.sort_by:
        if filters.sort_by == "price_asc":
            if price_type_val == "sale":
                sort_col = Property.price_sale
            else:
                sort_col = Property.price_rent
            sort_asc = True
        elif filters.sort_by == "price_desc":
            if price_type_val == "sale":
                sort_col = Property.price_sale
            else:
                sort_col = Property.price_rent
            sort_asc = False
        elif filters.sort_by == "newest":
            sort_col = Property.posted_date
            sort_asc = False

    if sort_asc:
        query = query.order_by(sort_col.asc().nullslast())
    else:
        query = query.order_by(sort_col.desc().nullslast())

    # --- Count (separate query) ---
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # --- Pagination ---
    offset_val = (filters.page - 1) * filters.page_size
    query = query.offset(offset_val).limit(filters.page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    # --- Compute price_per_sqm ---
    for item in items:
        if item.price_rent is not None and item.area_sqm and item.area_sqm > 0:
            item.price_per_sqm = round(item.price_rent / item.area_sqm, 2)
        elif item.price_sale is not None and item.area_sqm and item.area_sqm > 0:
            item.price_per_sqm = round(item.price_sale / item.area_sqm, 2)
        else:
            item.price_per_sqm = None

    return total, items


async def get_property_detail(db: AsyncSession, property_id: int) -> Optional[Property]:
    """查询单条房源详情。"""
    query = select(Property).where(Property.id == property_id)
    result = await db.execute(query)
    prop = result.scalar_one_or_none()
    if prop:
        # Compute price_per_sqm
        if prop.price_rent is not None and prop.area_sqm and prop.area_sqm > 0:
            prop.price_per_sqm = round(prop.price_rent / prop.area_sqm, 2)
        elif prop.price_sale is not None and prop.area_sqm and prop.area_sqm > 0:
            prop.price_per_sqm = round(prop.price_sale / prop.area_sqm, 2)
    return prop


async def get_properties_for_compare(
    db: AsyncSession,
    ids: List[int],
) -> List[Property]:
    """批量查询房源用于比价。"""
    query = select(Property).where(Property.id.in_(ids), Property.is_active == True)
    result = await db.execute(query)
    items = list(result.scalars().all())
    # Compute price_per_sqm for each
    for item in items:
        if item.price_rent is not None and item.area_sqm and item.area_sqm > 0:
            item.price_per_sqm = round(item.price_rent / item.area_sqm, 2)
        elif item.price_sale is not None and item.area_sqm and item.area_sqm > 0:
            item.price_per_sqm = round(item.price_sale / item.area_sqm, 2)
    return items


async def get_markers(
    db: AsyncSession,
    lat_min: Optional[float] = None,
    lat_max: Optional[float] = None,
    lng_min: Optional[float] = None,
    lng_max: Optional[float] = None,
) -> List[Property]:
    """
    轻量级坐标查询，只返回地图标记所需字段。
    bounds 通过 lat/lng 范围定义。
    """
    query = select(Property).where(
        Property.is_active == True,
        Property.lat.isnot(None),
        Property.lng.isnot(None),
    )

    if lat_min is not None:
        query = query.where(Property.lat >= lat_min)
    if lat_max is not None:
        query = query.where(Property.lat <= lat_max)
    if lng_min is not None:
        query = query.where(Property.lng >= lng_min)
    if lng_max is not None:
        query = query.where(Property.lng <= lng_max)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_districts(
    db: AsyncSession,
) -> List[dict]:
    """
    区域统计：用 group_by district 查询 count, avg_price_rent, avg_price_sale。
    """
    query = select(
        Property.district,
        func.count(Property.id).label("count"),
        func.avg(Property.price_rent).label("avg_price_rent"),
        func.avg(Property.price_sale).label("avg_price_sale"),
    ).where(
        Property.is_active == True,
        Property.district.isnot(None),
    ).group_by(
        Property.district
    ).order_by(
        func.count(Property.id).desc()
    )

    result = await db.execute(query)
    rows = result.all()
    districts = []
    for row in rows:
        districts.append({
            "name": row.district,
            "name_en": None,
            "count": row.count,
            "avg_price_rent": round(float(row.avg_price_rent), 2) if row.avg_price_rent else None,
            "avg_price_sale": round(float(row.avg_price_sale), 2) if row.avg_price_sale else None,
        })
    return districts
