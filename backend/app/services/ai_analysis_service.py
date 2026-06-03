"""
AI 房源分析引擎 — 纯本地数据驱动，不依赖外部 API

功能：
1. 单房源 AI 分析（价格评估、评分、趋势、一句话总结）
2. 比价智能推荐
3. 自然语言搜索解析
"""

from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.models.property import Property, PriceType, PriceHistory


# ============================================================
# 工具函数
# ============================================================

def _get_price(prop: Property) -> Optional[float]:
    """取房源的主要价格（RENT取price_rent，其他取price_sale）"""
    if prop.price_type == PriceType.RENT:
        return prop.price_rent
    return prop.price_sale


def _format_thb(val: Optional[float]) -> str:
    """格式化泰铢显示"""
    if val is None:
        return "暂无"
    if val >= 10000:
        return f"฿{val/10000:.1f}万"
    return f"฿{val:,.0f}"


async def _get_district_stats(db: AsyncSession, district: str) -> dict:
    """获取同区域统计：均价中位数、房源数、面积中位数"""
    stmt = select(
        func.avg(Property.price_rent).label("avg_rent"),
        func.avg(Property.price_sale).label("avg_sale"),
        func.avg(Property.area_sqm).label("avg_area"),
        func.count(Property.id).label("count"),
    ).where(
        Property.is_active == True,
        Property.district == district,
    )
    result = await db.execute(stmt)
    row = result.one()
    return {
        "avg_price_rent": round(float(row.avg_rent), 2) if row.avg_rent else None,
        "avg_price_sale": round(float(row.avg_sale), 2) if row.avg_sale else None,
        "avg_area_sqm": round(float(row.avg_area), 2) if row.avg_area else None,
        "count": row.count,
    }


async def _get_global_stats(db: AsyncSession, price_type: PriceType) -> dict:
    """获取全平台统计（同类型）"""
    price_col = Property.price_rent if price_type == PriceType.RENT else Property.price_sale
    stmt = select(
        func.avg(price_col).label("avg_price"),
        func.min(price_col).label("min_price"),
        func.max(price_col).label("max_price"),
        func.count(Property.id).label("count"),
    ).where(
        Property.is_active == True,
        Property.price_type == price_type,
        price_col.isnot(None),
    )
    result = await db.execute(stmt)
    row = result.one()
    return {
        "avg_price": round(float(row.avg_price), 2) if row.avg_price else None,
        "min_price": round(float(row.min_price), 2) if row.min_price else None,
        "max_price": round(float(row.max_price), 2) if row.max_price else None,
        "count": row.count,
    }


# ============================================================
# 1. 单房源 AI 分析
# ============================================================

async def analyze_property(
    db: AsyncSession,
    property_id: int,
) -> dict:
    """
    生成单房源的结构化分析报告。
    """
    # 加载房源
    stmt = select(Property).where(Property.id == property_id)
    result = await db.execute(stmt)
    prop = result.scalar_one_or_none()
    if not prop:
        return {"error": "房源不存在"}

    price = _get_price(prop)
    price_type_label = "出租" if prop.price_type == PriceType.RENT else "出售"

    # 同区域统计
    district_stats = None
    if prop.district:
        district_stats = await _get_district_stats(db, prop.district)

    # 全平台统计
    global_stats = await _get_global_stats(db, prop.price_type)

    # --- 价格评估 ---
    price_assessment = _calc_price_assessment(prop, price, district_stats)

    # --- 性价比评分 ---
    value_score = _calc_value_score(prop, price, district_stats)

    # --- 价格趋势 ---
    trend = await _calc_price_trend(db, prop)

    # --- 一句话总结 ---
    summary = _generate_summary(prop, price, price_type_label, price_assessment, value_score, trend)

    return {
        "property_id": property_id,
        "property_title": prop.title,
        "price_type": price_type_label,
        "price": price,
        "district": prop.district,
        "price_assessment": price_assessment,
        "value_score": value_score,
        "trend": trend,
        "summary": summary,
        "analysis_time": datetime.utcnow().isoformat(),
    }


def _calc_price_assessment(
    prop: Property,
    price: Optional[float],
    district_stats: Optional[dict],
) -> dict:
    """计算价格评估：与同区均价对比"""
    if not price or not district_stats:
        return {"level": "unknown", "label": "数据不足，无法评估"}

    avg_price = None
    if prop.price_type == PriceType.RENT:
        avg_price = district_stats.get("avg_price_rent")
    else:
        avg_price = district_stats.get("avg_price_sale")

    if not avg_price or avg_price <= 0:
        return {"level": "unknown", "label": "同区参考数据不足"}

    diff_pct = (price - avg_price) / avg_price * 100

    if diff_pct < -15:
        level = "below_market"
        label = f"低于同区均价 {abs(diff_pct):.0f}%"
    elif diff_pct < 15:
        level = "market"
        label = f"与同区均价持平（差 {abs(diff_pct):.0f}%）"
    elif diff_pct < 30:
        level = "above_market"
        label = f"高于同区均价 {diff_pct:.0f}%"
    else:
        level = "premium"
        label = f"显著高于同区均价 {diff_pct:.0f}%"

    return {
        "level": level,
        "label": label,
        "diff_pct": round(diff_pct, 1),
        "avg_price": round(avg_price, 2),
        "same_district_count": district_stats.get("count", 0),
    }


def _calc_value_score(
    prop: Property,
    price: Optional[float],
    district_stats: Optional[dict],
) -> dict:
    """计算性价比评分（0-100）"""
    if not price or price <= 0:
        return {"score": None, "label": "数据不足", "details": {}}

    scores = []
    details = {}

    # 1. 面积性价比
    if prop.area_sqm and prop.area_sqm > 0:
        price_per_sqm = price / prop.area_sqm
        if district_stats and district_stats.get("avg_price_rent"):
            avg_per_sqm = district_stats["avg_price_rent"] / district_stats["avg_area_sqm"] \
                if district_stats.get("avg_area_sqm") and district_stats["avg_area_sqm"] > 0 else None
            if avg_per_sqm and avg_per_sqm > 0:
                sqm_ratio = price_per_sqm / avg_per_sqm
                sqm_score = max(0, min(100, 100 - (sqm_ratio - 1) * 100))
                scores.append(sqm_score)
                details["price_per_sqm"] = {
                    "value": round(price_per_sqm, 2),
                    "score": round(sqm_score, 1),
                }

    # 2. 位置评分（有坐标加分）
    loc_score = 60
    if prop.lat and prop.lng:
        loc_score = 80  # 有精确位置
    details["location"] = {
        "has_coords": bool(prop.lat and prop.lng),
        "score": loc_score,
    }
    scores.append(loc_score)

    # 3. 装修评分
    decor_score = 50
    if prop.furnished:
        decor_score = 80
    elif prop.furnished is False:
        decor_score = 40
    details["furnished"] = {
        "furnished": prop.furnished,
        "score": decor_score,
    }
    scores.append(decor_score)

    # 4. 楼层评分（中高层加分）
    floor_score = 50
    if prop.total_floors and prop.floor:
        ratio = prop.floor / prop.total_floors
        if ratio > 0.5:
            floor_score = 80
        elif ratio > 0.3:
            floor_score = 65
    details["floor"] = {
        "floor": prop.floor,
        "total_floors": prop.total_floors,
        "score": floor_score,
    }
    scores.append(floor_score)

    # 5. 图片评分
    img_score = 50
    if prop.images:
        img_count = len(prop.images)
        if img_count >= 5:
            img_score = 85
        elif img_count >= 3:
            img_score = 70
        elif img_count >= 1:
            img_score = 60
    details["images"] = {
        "count": len(prop.images) if prop.images else 0,
        "score": img_score,
    }
    scores.append(img_score)

    # 总分（加权平均）
    weights = [0.35, 0.20, 0.15, 0.15, 0.15]  # 面积性价比权重最高
    total = sum(s * w for s, w in zip(scores, weights[:len(scores)]))
    total = round(min(100, max(0, total)), 1)

    label = "极高" if total >= 85 else "良好" if total >= 70 else "一般" if total >= 50 else "较差"

    return {
        "score": total,
        "label": label,
        "details": details,
    }


async def _calc_price_trend(db: AsyncSession, prop: Property) -> dict:
    """计算价格趋势（基于 price_history）"""
    stmt = (
        select(PriceHistory)
        .where(PriceHistory.property_id == prop.id)
        .order_by(PriceHistory.scraped_at.asc())
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    if len(records) < 2:
        return {
            "has_trend": False,
            "label": "数据不足（少于2次记录）",
            "records_count": len(records),
            "direction": "stable",
        }

    first_price = _get_price(records[0])
    last_price = _get_price(records[-1])

    if not first_price or not last_price or first_price <= 0:
        return {"has_trend": False, "label": "价格数据不全", "records_count": len(records), "direction": "stable"}

    change_pct = (last_price - first_price) / first_price * 100

    # 计算变化天数
    first_date = records[0].scraped_at
    last_date = records[-1].scraped_at
    days_span = (last_date - first_date).days if last_date and first_date else 0

    if change_pct > 5:
        direction = "up"
        label = f"上涨 {change_pct:.1f}%（{days_span}天内）"
    elif change_pct < -5:
        direction = "down"
        label = f"下跌 {abs(change_pct):.1f}%（{days_span}天内）"
    else:
        direction = "stable"
        label = f"基本持平（变化 {abs(change_pct):.1f}%）"

    return {
        "has_trend": True,
        "direction": direction,
        "change_pct": round(change_pct, 1),
        "days_span": days_span,
        "records_count": len(records),
        "first_price": first_price,
        "last_price": last_price,
        "label": label,
    }


def _generate_summary(
    prop: Property,
    price: Optional[float],
    price_type_label: str,
    price_assessment: dict,
    value_score: dict,
    trend: dict,
) -> str:
    """生成一句话总结"""
    parts = []

    # 价格定位
    if price_assessment.get("level") == "below_market":
        parts.append(f"✅ 同区低价 — 比均价低 {abs(price_assessment['diff_pct']):.0f}%")
    elif price_assessment.get("level") == "market":
        parts.append(f"💰 价格合理 — 与同区均价持平")
    elif price_assessment.get("level") == "above_market":
        parts.append(f"⚠️ 略高于同区均价 {price_assessment['diff_pct']:.0f}%")
    elif price_assessment.get("level") == "premium":
        parts.append(f"💎 高端定位 — 显著高于同区均价 {price_assessment['diff_pct']:.0f}%")

    # 性价比
    score = value_score.get("score")
    if score is not None:
        if score >= 85:
            parts.append(f"⭐ 性价比极高（{score}分）")
        elif score >= 70:
            parts.append(f"👍 性价比良好（{score}分）")
        elif score >= 50:
            parts.append(f"📊 性价比一般（{score}分）")
        else:
            parts.append(f"👇 性价比偏低（{score}分）")

    # 趋势
    if trend.get("has_trend") and trend.get("direction") == "down":
        parts.append(f"📉 价格下行中（{trend['days_span']}天跌{abs(trend['change_pct']):.1f}%）")
    elif trend.get("has_trend") and trend.get("direction") == "up":
        parts.append(f"📈 价格上行中（{trend['days_span']}天涨{trend['change_pct']:.1f}%）")

    # 面积亮点
    if prop.area_sqm and prop.area_sqm > 80:
        parts.append(f"🏠 大面积（{prop.area_sqm}㎡）适合家庭")
    elif prop.area_sqm and prop.area_sqm < 30:
        parts.append(f"🔑 紧凑型（{prop.area_sqm}㎡）适合单人")

    if not parts:
        parts.append(f"数据有限，建议实地考察")

    return " | ".join(parts)


# ============================================================
# 2. 比价智能推荐
# ============================================================

async def compare_analysis(
    db: AsyncSession,
    property_ids: List[int],
) -> dict:
    """对比多个房源并给出推荐"""
    if not property_ids:
        return {"error": "请提供房源ID列表"}
    if len(property_ids) > 20:
        return {"error": "最多对比20个房源"}

    stmt = select(Property).where(Property.id.in_(property_ids), Property.is_active == True)
    result = await db.execute(stmt)
    properties = list(result.scalars().all())

    if not properties:
        return {"error": "未找到有效房源"}

    items = []
    for prop in properties:
        analysis = await analyze_property(db, prop.id)
        items.append(analysis)

    # 按综合评分排序
    items.sort(key=lambda x: (x.get("value_score", {}) or {}).get("score", 0) or 0, reverse=True)

    # 最佳推荐
    best = items[0] if items else None

    # 生成对比摘要
    summaries = []
    cheap = sorted(
        [i for i in items if i.get("price")],
        key=lambda x: x["price"],
    )
    if cheap:
        cheapest = cheap[0]
        summaries.append(f"🏆 最低价：{cheapest.get('property_title', 'N/A')} — {_format_thb(cheapest['price'])}")

    if best and best.get("value_score", {}).get("score"):
        summaries.append(f"⭐ 最佳性价比：{best.get('property_title', 'N/A')} — {best['value_score']['label']}（{best['value_score']['score']}分）")

    if any(i.get("trend", {}).get("direction") == "down" for i in items):
        down_items = [i for i in items if i.get("trend", {}).get("direction") == "down"]
        down_names = [i.get("property_title", "")[:15] for i in down_items[:3]]
        summaries.append(f"📉 价格在降：{', '.join(down_names)}")

    return {
        "recommendation": {
            "best_id": best.get("property_id") if best else None,
            "best_title": best.get("property_title") if best else None,
            "best_score": best.get("value_score", {}).get("score") if best else None,
        },
        "items": items,
        "summaries": summaries,
        "total_compared": len(items),
    }


# ============================================================
# 3. 自然语言搜索解析（轻量版）
# ============================================================

def parse_natural_search(query: str) -> dict:
    """
    解析自然语言搜索查询为结构化筛选条件。
    纯规则引擎，不依赖 LLM。

    支持模式：
    - 区域：XX区 / XX附近 / XX区域
    - 价格：1万以下 / 5000-10000 / 不超过2万 / 大于3万
    - 户型：两室/2室/3房/一居
    - 类型：公寓/别墅/condo/house
    - 楼层：不要一楼 / 高层 / 带电梯
    """
    if not query or not query.strip():
        return {}

    q = query.strip()
    filters = {}

    # 1. 提取区域
    # 模式：XX区、XX区域、XX附近
    import re
    district_pattern = re.compile(r'([\u4e00-\u9fff]{2,6})(?:区|区域|附近|片区)')
    m = district_pattern.search(q)
    if m:
        filters["district"] = m.group(1)

    # 2. 提取价格
    # 模式：1万以下 / 1万以上 / 5000-10000 / 不超过2万 / 大于3万 / 1万到2万
    # 先匹配"数字+万+以下/以上"这种结构
    compound_below = re.compile(r'(\d+(?:\.\d+)?)\s*[万千]\s*(?:以下|以内)')
    m = compound_below.search(q)
    if m:
        filters["max_price"] = float(m.group(1)) * 10000
    else:
        compound_above = re.compile(r'(\d+(?:\.\d+)?)\s*[万千]\s*(?:以上|以外)')
        m = compound_above.search(q)
        if m:
            filters["min_price"] = float(m.group(1)) * 10000

    # 区间模式：1万到2万 / 1万-2万 / 1万~2万
    price_range = re.compile(r'(\d+(?:\.\d+)?)\s*[万千]?\s*(?:到|至|-|~|～)\s*(\d+(?:\.\d+)?)\s*[万千]?')
    m = price_range.search(q)
    if m:
        filters["min_price"] = float(m.group(1)) * (10000 if "万" in q else 1)
        filters["max_price"] = float(m.group(2)) * (10000 if "万" in q else 1)
    else:
        # 前置词模式：不超过2万 / 低于1万 / 大于3万 / 不超过15000 / 不低于2万 / 不小于8000 / 不大于3万
        # 先匹配长的否定模式
        negation_pattern = re.compile(r'(?:不大于|不小于|不低于|不少于)\s*(\d+(?:\.\d+)?)\s*[万千]?')
        m_neg = negation_pattern.search(q)
        
        if m_neg:
            kw = m_neg.group(0)
            val = float(m_neg.group(1))
            if '不大于' in kw:
                filters["max_price"] = val * (10000 if '万' in q else 1)
            else:  # 不小于 / 不低于
                filters["min_price"] = val * (10000 if '万' in q else 1)
        else:
            # 上限词：不超过 / 低于 / 少于 / 小于（但不匹配"不低于""不少于"）
            below_pattern = re.compile(r'(?<!不)(?:超过?|低于?|少于|小于)\s*(\d+(?:\.\d+)?)\s*[万千]?')
            # 保留"不超过"的精确匹配
            not_exceed = re.compile(r'不超过\s*(\d+(?:\.\d+)?)\s*[万千]?')
            
            # 下限词：超过 / 高于 / 多于 / 大于（后面有"不"前缀的排除）
            above_pattern = re.compile(r'(?<!不)(?:超过?|高于?|多于|大于)\s*(\d+(?:\.\d+)?)\s*[万千]?')
            
            m_below = not_exceed.search(q)
            if m_below:
                v = float(m_below.group(1))
                unit = "万" if ("万" in m_below.group(0) or "万" in q) else ("千" if ("千" in m_below.group(0) or "千" in q) else None)
                if unit:
                    filters["max_price"] = v * (10000 if unit == "万" else 1000)
                else:
                    filters["max_price"] = v
            
            m_below2 = below_pattern.search(q)
            if m_below2:
                v = float(m_below2.group(1))
                unit = "万" if ("万" in m_below2.group(0) or "万" in q) else ("千" if ("千" in m_below2.group(0) or "千" in q) else None)
                if unit:
                    filters["max_price"] = v * (10000 if unit == "万" else 1000)
                else:
                    filters["max_price"] = v

            m_above = above_pattern.search(q)
            if m_above:
                v = float(m_above.group(1))
                unit = "万" if ("万" in m_above.group(0) or "万" in q) else ("千" if ("千" in m_above.group(0) or "千" in q) else None)
                if unit:
                    filters["min_price"] = v * (10000 if unit == "万" else 1000)
                else:
                    filters["min_price"] = v

    # 裸数字区间：5000-10000
    if "min_price" not in filters and "max_price" not in filters:
        bare_range = re.compile(r'(\d{4,6})\s*[-～~至到]\s*(\d{4,6})')
        m = bare_range.search(q)
        if m:
            filters["min_price"] = float(m.group(1))
            filters["max_price"] = float(m.group(2))

    # 3. 提取户型
    rooms_pattern = re.compile(r'(\d)\s*(?:室|房|居|卧|bed|br|beds)')
    m = rooms_pattern.search(q)
    if m:
        filters["bedrooms"] = int(m.group(1))

    # 4. 提取类型
    type_keywords = {
        "condo": "CONDO", "公寓": "CONDO",
        "house": "HOUSE", "别墅": "HOUSE", "独栋": "HOUSE",
        "townhouse": "TOWNHOUSE", "联排": "TOWNHOUSE",
        "apartment": "APARTMENT", "普通公寓": "APARTMENT",
    }
    for keyword, value in type_keywords.items():
        if keyword in q:
            filters["property_type"] = value
            break

    # 5. 价格类型识别
    if any(kw in q for kw in ["出租", "租", "月租", "rent"]):
        filters["price_type"] = "RENT"
    elif any(kw in q for kw in ["出售", "买", "卖", "购买", "sale", "buy"]):
        filters["price_type"] = "SALE"

    # 6. 排序
    if any(kw in q for kw in ["便宜", "低价", "最便宜", "性价比"]):
        filters["sort_by"] = "price_asc"
    elif any(kw in q for kw in ["最新", "新房源"]):
        filters["sort_by"] = "newest"

    # 7. 是否有"不要一楼"
    if "不要" in q and "一楼" in q:
        filters["exclude_first_floor"] = True

    return filters


async def smart_search(
    db: AsyncSession,
    query: str,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """自然语言搜索 → 结构化查询 → 召回结果"""
    filters = parse_natural_search(query)

    # 调用现存的服务层
    from app.services.property_service import get_properties
    from app.schemas.property import PropertyFilterParams

    params = PropertyFilterParams(
        keyword=query,  # 关键词依然是原始文本用于模糊匹配
        page=page,
        page_size=page_size,
    )

    # 应用解析出的筛选条件
    if "district" in filters:
        params.district = filters["district"]
    if "min_price" in filters:
        params.min_price = filters["min_price"]
    if "max_price" in filters:
        params.max_price = filters["max_price"]
    if "bedrooms" in filters:
        params.bedrooms = filters["bedrooms"]
    if "property_type" in filters:
        params.property_type = filters["property_type"]
    if "price_type" in filters:
        from app.schemas.property import PriceTypeEnum
        params.price_type = PriceTypeEnum(filters["price_type"].lower())
    if "sort_by" in filters:
        params.sort_by = filters["sort_by"]

    total, items = await get_properties(db, params)

    return {
        "parsed_query": filters,
        "total": total,
        "items": [
            {
                "id": p.id,
                "title": p.title,
                "price_rent": p.price_rent,
                "price_sale": p.price_sale,
                "price_type": p.price_type.value,
                "district": p.district,
                "bedrooms": p.bedrooms,
                "area_sqm": p.area_sqm,
                "property_type": p.property_type.value,
                "lat": p.lat,
                "lng": p.lng,
                "source": p.source,
                "images": p.images,
            }
            for p in items
        ],
    }
