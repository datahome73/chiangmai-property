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
# 3. 自然语言搜索解析（加强版）
# ============================================================

# ── 清迈常见区域别名表 ──
_DISTRICT_ALIASES = {
    # 古城/市中心
    "古城": "古城", "old city": "古城", "老城": "古城",
    "市中心": "市中心", "downtown": "市中心", "city center": "市中心",
    # 宁曼路
    "宁曼": "宁曼", "尼曼": "宁曼", "尼曼路": "宁曼",
    "nimman": "宁曼", "尼曼翰明": "宁曼",
    # 长康路/夜市
    "长康": "长康", "夜市": "长康", "night bazaar": "长康", "长康路": "长康",
    # 杭东
    "杭东": "杭东", "hang dong": "杭东",
    # 山甘烹
    "山甘烹": "山甘烹", "san kamphaeng": "山甘烹",
    # 讪赛
    "讪赛": "讪赛", "san sai": "讪赛",
    # 湄林
    "湄林": "湄林", "mae rim": "湄林",
    # 湄登
    "湄登": "湄登", "mae tang": "湄登",
    # 沙拉丕
    "沙拉丕": "沙拉丕", "saraphi": "沙拉丕",
    # 南奔
    "南奔": "南奔", "lamphun": "南奔",
    # 尚泰/central festival 周边
    "central": "尚泰", "central festival": "尚泰", "尚泰": "尚泰",
    # 清迈大学
    "清迈大学": "清迈大学", "cmu": "清迈大学", "大学": "清迈大学",
    # 湄夏
    "湄夏": "湄夏", "mae hia": "湄夏",
    # 帕坦/界遥
    "帕坦": "帕坦", "界遥": "帕坦", "jed yod": "帕坦",
    # 三王广场/昌莫伊
    "三王广场": "三王广场", "昌莫伊": "昌莫伊", "chang moi": "昌莫伊",
    # 瓦洛洛市场
    "瓦洛洛": "瓦洛洛", "warorot": "瓦洛洛",
    # 清迈门
    "清迈门": "清迈门", "chiang mai gate": "清迈门", "南门": "清迈门",
    # 塔佩门
    "塔佩": "塔佩", "tha pae": "塔佩", "东门": "塔佩",
    # 湄萍河
    "萍河": "萍河", "ping river": "萍河", "河边": "萍河", "河畔": "萍河",
    # 二环/outer ring
    "二环": "二环", "outer ring": "二环", "外环": "二环",
    # 清迈机场
    "机场": "机场", "airport": "机场",
    # 圣巴
    "圣巴": "圣巴", "san pa tong": "圣巴",
    # Doi Saket
    "doi saket": "堆沙革", "堆沙革": "堆沙革",
    # 猜巴干
    "chai prakan": "猜巴干", "猜巴干": "猜巴干",
    # 方县
    "fang": "方县", "方县": "方县",
}

# ── 中文数字映射 ──
_CN_NUM = {
    "零": 0, "一": 1, "二": 2, "两": 2, "俩": 2,
    "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "百": 100, "千": 1000,
}
_CN_NUM_UNIT = {"十": 10, "百": 100, "千": 1000, "万": 10000}

# ── 物业设施关键词 ──
_AMENITY_KEYWORDS = {
    "泳池": "pool", "游泳池": "pool", "swimming pool": "pool",
    "健身房": "gym", "gym": "gym",
    "停车": "parking", "parking": "parking", "车位": "parking",
    "电梯": "elevator", "elevator": "elevator", "lift": "elevator",
    "保安": "security", "security": "security", "24小时": "security",
    "花园": "garden", "garden": "garden", "院子": "garden",
    "阳台": "balcony", "balcony": "balcony", "露台": "balcony",
}


def _parse_cn_number(text: str) -> Optional[float]:
    """解析中文数字：'二百五'→250, '三千'→3000, '两万五'→25000, '十二'→12"""
    if not text:
        return None
    # 纯阿拉伯数字直接返回
    try:
        return float(text)
    except ValueError:
        pass
    total = 0
    current = 0
    for ch in text:
        if ch in _CN_NUM:
            v = _CN_NUM[ch]
            if v >= 10:  # 十百千万是单位
                if current == 0:
                    current = v  # '十'开头 = 10, '百'开头 = 100
                else:
                    current *= v
            else:
                current += v
        else:
            # 遇到非中文数字字符，flush
            total += current
            current = 0
    total += current
    return float(total) if total > 0 else None


def parse_natural_search(query: str) -> dict:
    """
    解析自然语言搜索查询为结构化筛选条件。
    纯规则引擎，不依赖 LLM。

    支持扩展模式：
    - 区域：古城、尼曼、杭东、central、清迈大学附近...
    - 价格：1万以下、5000-10000、不超过2万、大于3万
            两万以内、฿15000、一千五、三百多
    - 户型：一房一厅、开间、两室、3室、studio
    - 类型：公寓、condo、别墅、house、联排
    - 设施：带泳池、要电梯、不要一楼、要阳台
    - 排序：最便宜、离古城近、性价比
    - 排除：不要顶楼、不要路边
    """
    if not query or not query.strip():
        return {}

    q = query.strip().lower()
    filters = {}

    # ═══════════════════════════════════════════
    # 1. 区域提取（别名映射）
    # ═══════════════════════════════════════════
    import re
    # 先尝试精确匹配别名表
    matched_districts = []
    for alias, canonical in _DISTRICT_ALIASES.items():
        if alias in q:
            matched_districts.append(canonical)
    if matched_districts:
        # 取最长匹配（最具体）
        filters["district"] = max(set(matched_districts), key=len)

    # 区域后缀模式：XX区 / XX附近 / XX区域 / XX片区 / XX周边
    if "district" not in filters:
        for suffix in ["区", "附近", "区域", "片区", "周边", "板块", "地段"]:
            pat = re.compile(rf"([\u4e00-\u9fff]{{2,6}}){re.escape(suffix)}")
            m = pat.search(q)
            if m:
                filters["district"] = m.group(1)
                break

    # ═══════════════════════════════════════════
    # 2. 价格提取（全面覆盖）
    # ═══════════════════════════════════════════
    # 先检测是否包含泰铢符号
    has_thb = "฿" in q or "thb" in q

    def _resolve_unit(q_local: str, default=1) -> int:
        """判断价格是 '万' '千' 还是原始数字"""
        if "万" in q_local:
            return 10000
        if "千" in q_local or "k" in q_local.replace("฿", ""):
            return 1000
        if "百" in q_local:
            return 100
        return default

    # ── 在价格提取前，先移除已确定的户型关键词，避免干扰 ──
    rooms_removed = re.sub(
        r"([一两三四五六七八九十\d])\s*(?:室|房|卧|居|bed|br|beds?)\s*(?:一[厅]?)?",
        "", q
    )

    # ---- 2a. 先检查是否是面积区间而不是价格区间
    area_range_check = re.compile(r"(\d{3,8})\s*(?:[-～~至到]|to)\s*(\d{3,8})\s*(?:平|㎡|sqm|平方米|平米)")
    if not area_range_check.search(q.replace(",", "")):
        bare_range = re.compile(
            r"(?:฿)?(\d{3,8})\s*(?:[-～~至到]|to)\s*(?:฿)?(\d{3,8})"
        )
        m = bare_range.search(rooms_removed.replace(",", "") or q.replace(",", ""))
    if m:
        unit = _resolve_unit(q)
        # 如果数字明显是"月"价级别(低于1000视为错误)
        v1, v2 = float(m.group(1)), float(m.group(2))
        if v1 < 100:
            unit = 1  # 小数字不做万/千换算
        filters["min_price"] = v1 * unit
        filters["max_price"] = v2 * unit

    # ---- 2b. 中文数字区间: "五千到一万" / "两千~三千"
    if "min_price" not in filters:
        cn_range = re.compile(
            r"([\u4e00-\u9fff十百千万\d]{1,8})\s*(?:[-～~至到]|到|至)\s*([\u4e00-\u9fff十百千万\d]{1,8})"
        )
        m = cn_range.search(rooms_removed or q)
        if m:
            v1 = _parse_cn_number(m.group(1))
            v2 = _parse_cn_number(m.group(2))
            if v1 and v2:
                unit = _resolve_unit(q)
                filters["min_price"] = v1 * unit
                filters["max_price"] = v2 * unit

    # ---- 2c. 上限表达: "XX以下/以内/不超过/不超/低于.../少于/预算XX"
    # 先处理"每月/月租+数字"模式 — 数字前有中文前缀
    m_monthly = re.search(r"(?:每月|月租|月)\s*(\d{3,8})", q)
    if m_monthly:
        filters["max_price"] = float(m_monthly.group(1))
    if "max_price" not in filters:
        cap_keywords = r"(?:不超过?|不超|预算|控制在|低于?|少于|小于|不大于|最多)"
        m = re.search(rf"{cap_keywords}\s*(\S+)", rooms_removed or q)
        if m:
            raw = m.group(1)
            val = _parse_cn_number(raw)
            if val is None:
                try:
                    val = float(raw.replace(",", ""))
                except ValueError:
                    val = None
            if val is not None:
                if val <= 1000 and "万" not in q and "千" not in q:
                    unit_val = val
                elif val <= 100 and ("百" in q or "百" in raw):
                    unit_val = val * 100
                else:
                    unit_val = val * _resolve_unit(q)
                filters["max_price"] = unit_val

    # 后缀式上限: "XX以下/以内"
    if "max_price" not in filters:
        m = re.search(r"(\S+)\s*(?:以下|以内|以内吧)", rooms_removed or q)
        if m:
            raw = m.group(1)
            val = _parse_cn_number(raw)
            if val is None:
                try:
                    val = float(raw.replace(",", ""))
                except ValueError:
                    val = None
            if val is not None:
                if val <= 1000 and "万" not in q and "千" not in q:
                    unit_val = val
                elif val <= 100 and ("百" in q or "百" in raw):
                    unit_val = val * 100
                else:
                    unit_val = val * _resolve_unit(q)
                filters["max_price"] = unit_val

    # ---- 2d. 下限表达: "XX以上/超过/高于/不少于..."
    if "min_price" not in filters:
        floor_keywords = r"(?:不少于|不低于|超过?|高于?|多于|大于|至少|最少)"
        m = re.search(rf"{floor_keywords}\s*(\S+)", rooms_removed or q)
        if m:
            raw = m.group(1)
            val = _parse_cn_number(raw)
            if val is None:
                try:
                    val = float(raw.replace(",", ""))
                except ValueError:
                    val = None
            if val is not None:
                if val <= 1000 and "万" not in q and "千" not in q:
                    unit_val = val
                elif val <= 100 and ("百" in q or "百" in raw):
                    unit_val = val * 100
                else:
                    unit_val = val * _resolve_unit(q)
                filters["min_price"] = unit_val

    # 后缀式下限: "XX以上"
    if "min_price" not in filters:
        m = re.search(r"(\S+)\s*(?:以上)", rooms_removed or q)
        if m:
            raw = m.group(1)
            val = _parse_cn_number(raw)
            if val is None:
                try:
                    val = float(raw.replace(",", ""))
                except ValueError:
                    val = None
            if val is not None:
                if val <= 1000 and "万" not in q and "千" not in q:
                    unit_val = val
                elif val <= 100 and ("百" in q or "百" in raw):
                    unit_val = val * 100
                else:
                    unit_val = val * _resolve_unit(q)
                filters["min_price"] = unit_val

    # ---- 2e. 裸数字（单个大数如 "一万五" "25000"）
    if "min_price" not in filters and "max_price" not in filters:
        # 匹配"数字+万/千"结构（如 "一万五""25000"）
        # 用 rooms_removed 避免 "两室" 被当作价格
        search_q = (rooms_removed or q).strip()
        standalone_pat = re.compile(r"(?:(\d[\d,.万万千千百百]*|[\u4e00-\u9fff十百千万\d]+))\s*(?:的|左右|以内)?$")
        m = standalone_pat.search(search_q)
        if m:
            raw = m.group(1)
            # 泰铢数字直接按原值处理
            if has_thb:
                try:
                    filters["max_price"] = float(raw.replace(",", ""))
                except ValueError:
                    pass
            else:
                val = _parse_cn_number(raw)
                if val:
                    unit = _resolve_unit(q)
                    filters["max_price"] = val * unit

    # ═══════════════════════════════════════════
    # 3. 户型提取
    # ═══════════════════════════════════════════
    # --- 3a. 数字+室/房/卧/居
    rooms_digit = re.compile(r"(\d)\s*(?:室|房|卧|居|bed|br|beds?|卧室|房间)")
    m = rooms_digit.search(q)
    if m:
        filters["bedrooms"] = int(m.group(1))
    else:
        # --- 3b. 中文数字户型: "一室""两房""三居""两室一厅"
        cn_rooms = re.compile(r"([一两三四五六七八九])\s*(?:室|房|卧|居)")
        m = cn_rooms.search(q)
        if m:
            filters["bedrooms"] = int(_CN_NUM.get(m.group(1), 0))
        else:
            # --- 3c. "一房一厅" → 至少1房
            if re.search(r"[一]房", q):
                filters["bedrooms"] = 1
            elif re.search(r"(开间|studio|一居|单间|大开间)", q):
                filters["bedrooms"] = 0
                filters["property_subtype"] = "studio"

    # ═══════════════════════════════════════════
    # 4. 物业类型
    # ═══════════════════════════════════════════
    type_map = {
        "condo": "CONDO", "公寓": "CONDO",
        "house": "HOUSE", "别墅": "HOUSE", "独栋": "HOUSE", "独院": "HOUSE",
        "townhouse": "TOWNHOUSE", "联排": "TOWNHOUSE", "联排别墅": "TOWNHOUSE",
        "apartment": "APARTMENT", "普通公寓": "APARTMENT", "apart": "APARTMENT",
        "店面": "SHOPHOUSE", "shophouse": "SHOPHOUSE", "shop house": "SHOPHOUSE",
        "土地": "LAND", "地皮": "LAND", "land": "LAND", "地块": "LAND",
    }
    for keyword, value in type_map.items():
        if keyword in q:
            filters["property_type"] = value
            break

    # ═══════════════════════════════════════════
    # 5. 价格类型（出租/出售）
    # ═══════════════════════════════════════════
    if any(kw in q for kw in ["出租", "租", "月租", "rent", "lease", "for rent", "短租", "长租"]):
        filters["price_type"] = "RENT"
    elif any(kw in q for kw in ["出售", "买", "卖", "购买", "sale", "buy", "for sale", "置业"]):
        filters["price_type"] = "SALE"

    # ═══════════════════════════════════════════
    # 6. 排序
    # ═══════════════════════════════════════════
    if any(kw in q for kw in ["便宜", "低价", "最便宜", "性价比", "捡漏", "划算", "最低价"]):
        filters["sort_by"] = "price_asc"
    elif any(kw in q for kw in ["最新", "新房源", "刚上", "新上"]):
        filters["sort_by"] = "newest"
    elif any(kw in q for kw in ["最近", "离我近"]):
        filters["sort_by"] = "distance"
    elif "附近" in q and "区域" not in q and "片区" not in q and "周边" not in q:
        filters["sort_by"] = "distance"

    # ═══════════════════════════════════════════
    # 7. 楼层排除/偏好
    # ═══════════════════════════════════════════
    if re.search(r"(不要|别|避免|避开|排除)\s*(一楼|底层)", q):
        filters["exclude_first_floor"] = True
    if re.search(r"(不要|别|避免|避开|排除)\s*(顶楼|顶层|天台)", q):
        filters["exclude_top_floor"] = True
    if "高层" in q or "高楼层" in q or ("楼层" in q and "高" in q):
        filters["prefer_high_floor"] = True

    # ═══════════════════════════════════════════
    # 8. 设施偏好
    # ═══════════════════════════════════════════
    amenities = []
    for keyword, canonical in _AMENITY_KEYWORDS.items():
        if keyword in q:
            if "不要" in q and keyword in q[q.index("不要") if "不要" in q else 0:]:
                # "不要带泳池" → 排除
                filters.setdefault("exclude_amenities", []).append(canonical)
            else:
                amenities.append(canonical)
    if amenities:
        filters["amenities"] = list(set(amenities))

    # ═══════════════════════════════════════════
    # 9. 面积提取
    # ═══════════════════════════════════════════
    area_pat = re.compile(r"(\d+)\s*(?:平|㎡|sqm|sq m|平方米|平米)")
    m = area_pat.search(q)
    if m:
        area_val = float(m.group(1))
        # 判断是下限还是上限
        if any(kw in q for kw in ["以上", "大于", "至少", "以上", "起步"]):
            filters["min_area"] = area_val
        elif any(kw in q for kw in ["以下", "以内", "小于", "不超"]):
            filters["max_area"] = area_val
        elif any(kw in q for kw in ["左右", "大概"]):
            filters["min_area"] = area_val * 0.8
            filters["max_area"] = area_val * 1.2
        elif any(kw in q for kw in ["到", "至", "-"]):
            # 应该已经被区间模式匹配了
            pass
        else:
            filters["max_area"] = area_val  # 默认作为上限

    # ═══════════════════════════════════════════
    # 10. 面积范围: "50-80平"
    # ═══════════════════════════════════════════
    area_range = re.compile(r"(\d+)\s*(?:[-～~至到]|to)\s*(\d+)\s*(?:平|㎡|sqm|平方米)")
    m = area_range.search(q)
    if m:
        filters["min_area"] = float(m.group(1))
        filters["max_area"] = float(m.group(2))

    # ═══════════════════════════════════════════
    # 11. 卧室+面积组合: "两室一厅80平"
    # ═══════════════════════════════════════════
    room_area = re.compile(r"([一两三四五六七八九十\d])[室房](?:一[厅]?)?[约约]?(\d+)[平㎡]")
    m = room_area.search(q)
    if m:
        room_val = _parse_cn_number(m.group(1))
        if room_val:
            filters["bedrooms"] = int(room_val)
        filters.setdefault("min_area", float(m.group(2)) * 0.8)
        filters.setdefault("max_area", float(m.group(2)) * 1.2)

    return filters


async def smart_search(
    db: AsyncSession,
    query: str,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """自然语言搜索 → 结构化查询 → 召回结果"""
    filters = parse_natural_search(query)

    # 从原始查询中提取纯关键词（去掉已被解析的部分）
    extracted_keywords = query
    if "district" in filters:
        extracted_keywords = extracted_keywords.replace(filters["district"], "")
    if "price_type" in filters:
        for kw in ["出租", "租", "月租", "出售", "买", "卖", "购买"]:
            extracted_keywords = extracted_keywords.replace(kw, "")
    extracted_keywords = extracted_keywords.strip().strip("，,，.")

    # 调用现存的服务层
    from app.services.property_service import get_properties
    from app.schemas.property import PropertyFilterParams

    params = PropertyFilterParams(
        keyword=extracted_keywords if extracted_keywords else None,
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
