# 清迈房产比价平台 — 第一轮技术方案

> 基于小谷改进方案 (`docs/improvement-plan.md`) 的详细实现设计
> 日期: 2026-06-16 | 作者: 小开

---

## 目录

1. [本轮目标](#1-本轮目标)
2. [数据源优先级](#2-数据源优先级)
3. [Phase 1 详细设计 — 数据源扩充 + Bug 修复](#3-phase-1-详细设计--数据源扩充--bug-修复)
4. [Phase 2 详细设计 — 爬虫架构升级](#4-phase-2-详细设计--爬虫架构升级)
5. [Phase 3 详细设计 — 更多数据源 + 数据校验](#5-phase-3-详细设计--更多数据源--数据校验)
6. [紧急 Bug 修复](#6-紧急-bug-修复)
7. [分支策略与提交顺序](#7-分支策略与提交顺序)
8. [架构变更示意](#8-架构变更示意)

---

## 1. 本轮目标

将清迈房源量从 **~148 条（仅 HipFlat）提升至 2000+ 条**，同时修复现有问题。

| 指标 | 当前 | 目标 |
|------|------|------|
| 活跃数据源 | 1（HipFlat） | 4 |
| 房源总量 | ~148 | 2000+ |
| 爬虫架构 | 无基类/重复代码 | 基类+增量 |
| Bug 存量 | 3 个已知 | 全部修复 |
| 定时爬取 | 无 | 每 6h 增量 |

---

## 2. 数据源优先级

基于小谷的调研评估：

| 优先级 | 平台 | 清迈房源估量 | 爬取难度 | 实现方式 | 状态 |
|--------|------|-------------|----------|----------|------|
| P0 | **FazWaz** | ~800 | 中 — 详情页 JS 渲染, 需改列表页 JSON-LD | 修复现有 `FazwazParser` | ⚠️ 半残需修 |
| P0 | **LivingStock** | ~500 | 低 — API 友好 | 新增爬虫 | ❌ 未接入 |
| P1 | **Renthub** | ~1000 | 低 — 全泰最大租房 | 新增爬虫 | ❌ 未接入 |
| P2 | **BaanFinder** | ~300 | 低 — 清迈本地 | 新增爬虫 | ❌ 延后 |
| P3 | **DDProperty** | ~2000 | 高 — CF 封锁 | ZenRows/Playwright 验证后 | ❌ 延后 |

---

## 3. Phase 1 详细设计 — 数据源扩充 + Bug 修复

### 3.1 紧急 Bug 修复（立即执行）

详见 [§6 紧急 Bug 修复](#6-紧急-bug-修复)。

### 3.2 FazWaz 爬虫修复

**问题：** `FazwazParser.parse_listing()` 从详情页 `<span>` 提取价格，但详情页 JS 动态渲染，ScrapingAnt 拿不到。

**方案：** 改从列表页 JSON-LD 提取价格。

```python
# proxy_crawler/parsers.py — 新增函数

def extract_fazwaz_prices_from_list(html: str) -> dict[str, float]:
    """从 FazWaz 列表页 JSON-LD 提取每条房源的价格"""
    sel = Selector(text=html)
    results = {}
    for script in sel.css('script[type="application/ld+json"]::text').getall():
        try:
            data = json.loads(script)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "Product":
                    url = item.get("url", "")
                    offers = item.get("offers", {})
                    price = offers.get("price")
                    if url and price:
                        results[url] = float(price)
        except json.JSONDecodeError:
            continue
    return results
```

**修改文件：** `proxy_crawler/parsers.py`
**改动量：** ~30 行新增

### 3.3 LivingStock 爬虫（新增）

**平台特征：** 泰国活跃中介房源平台，HTTP 友好，无需 JS 渲染。

**爬取策略：**

```python
# proxy_crawler/livingstock_crawler.py

class LivingStockCrawler(BaseCrawler):
    SOURCE = "livingstock"
    BASE_URL = "https://www.livingstock.co.th"
    RATE_LIMIT = 1.5
    MAX_RETRIES = 3

    def parse_list(self, html: str) -> list[dict]:
        """
        列表页 div.card 结构:
        - h2 → 标题
        - div.price → 价格文本
        - a → 详情链接
        - img → 图片
        """
        sel = Selector(text=html)
        listings = []
        for card in sel.css("div.card"):
            listings.append({
                "url": card.css("a::attr(href)").get(),
                "title": card.css("h2::text").get(),
                "price_text": card.css("div.price::text").get(),
                "img": card.css("img::attr(src)").get(),
            })
        return listings

    def parse_detail(self, html: str, listing: dict) -> dict:
        """详情页提取完整房源信息"""
        sel = Selector(text=html)
        return {
            "source_id": listing["url"].split("/")[-1],
            "title": listing["title"],
            # ... 从详情页提取更多字段
        }
```

**新增文件：** `proxy_crawler/livingstock_crawler.py`
**改动量：** ~100 行

### 3.4 注册新数据源

```python
# proxy_crawler/registry.py（新增）

SOURCES = {
    "hipflat": HipFlatCrawler,
    "fazwaz": FazWazCrawler,
    "livingstock": LivingStockCrawler,
}

async def crawl_all():
    """遍历所有注册的数据源执行增量爬取"""
    total = 0
    for name, cls in SOURCES.items():
        try:
            crawler = cls()
            count = await crawler.crawl()
            print(f"{name}: {count} properties")
            total += count
        except Exception as e:
            print(f"{name}: FAILED — {e}")
    return total
```

**新增文件：** `proxy_crawler/registry.py`
**改动量：** ~40 行

---

## 4. Phase 2 详细设计 — 爬虫架构升级

### 4.1 BaseCrawler 基类

基于现有 `ProxyAdapter` 重构，抽取公共逻辑：

```python
# proxy_crawler/base_crawler.py

class BaseCrawler(ABC):
    SOURCE: str = ""
    BASE_URL: str = ""
    RATE_LIMIT: float = 2.0
    MAX_RETRIES: int = 3

    def __init__(self):
        self.adapter = ProxyAdapter()
        self.stats = {"new": 0, "updated": 0, "failed": 0}

    @abstractmethod
    def parse_list(self, html: str) -> list[dict]:
        """解析列表页 → [{url, title, price_text, ...}]"""
        ...

    @abstractmethod
    def parse_detail(self, html: str, listing: dict) -> dict:
        """解析详情页 → 完整 property dict"""
        ...

    def validate(self, data: dict) -> list[str]:
        """数据校验，返回警告列表"""
        warnings = []
        if not data.get("title"):
            warnings.append("缺少标题")
        if not (data.get("price_rent") or data.get("price_sale")):
            warnings.append("缺少价格")
        return warnings

    async def crawl(self) -> tuple[int, int]:
        """
        全流程：
        1. 列表页 → 提取 URL 列表
        2. 去重（对比 DB 已有 source_id）
        3. 新 URL → 爬详情 → 入库
        4. 已有 URL → 更新价格/状态
        返回 (new_count, updated_count)
        """
        ...
```

**新增文件：** `proxy_crawler/base_crawler.py`
**改动量：** ~80 行

### 4.2 增量爬取实现

**方案：** 利用 `Property.checked_at` 字段 + URL hash 去重。

```sql
-- 增量逻辑
SELECT source_id, checked_at FROM properties WHERE source = 'hipflat';

-- 爬取列表页后：
--   URL 在 DB 中且 checked_at < 24h → 跳过
--   URL 在 DB 中且 checked_at > 24h → 更新价格/状态
--   新 URL → 爬详情页 → INSERT
```

**改动文件：** `proxy_crawler/storage.py`（新增或复用 `models.py`）
**改动量：** ~50 行

### 4.3 定时爬虫

**方案一：Hermes cronjob**（推荐，更灵活）

```bash
hermes cron create \
  --name "chiangmai-crawl" \
  --schedule "0 */6 * * *" \
  --prompt "运行 chiangmai-property 增量爬虫" \
  --deliver "local"
```

**方案二：Railway Cron Job**

```python
# backend/cron_crawl.py
"""定时爬虫入口 — 每 6h 增量爬取"""
from proxy_crawler.registry import crawl_all

async def main():
    total = await crawl_all()
    print(f"本轮更新: {total} 条")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**新增文件：** `backend/cron_crawl.py`
**改动量：** ~20 行

---

## 5. Phase 3 详细设计 — 更多数据源 + 数据校验

### 5.1 Renthub 爬虫

**目标：** 全泰最大租房平台，清迈房源估量 ~1000 条。

**策略：** 按区域（Chiang Mai）分页爬取，重点关注：
- 月租房源（price_rent）
- 区域分布（Nimman, Old City, Santitham, Chang Phueak）
- 设施标签（furnished, pet-friendly）

### 5.2 数据校验拦截器

```python
# proxy_crawler/quality.py

VALIDATORS = {
    "price_rent": lambda v: v >= 500,          # <500 ฿ 异常
    "price_sale": lambda v: v >= 100000,       # <10万 ฿ 异常
    "area_sqm": lambda v: 10 <= v <= 10000,    # 面积范围
    "bedrooms": lambda v: 0 <= v <= 20,        # 卧室数范围
    "title": lambda v: len(str(v)) > 2,        # 标题太短
}

def validate_property(prop: dict) -> list[str]:
    """返回所有校验失败的消息"""
    warnings = []
    for field, validator in VALIDATORS.items():
        val = prop.get(field)
        if val is not None and not validator(val):
            warnings.append(f"{field}={val} 超出合理范围")
    if not prop.get("lat") or not prop.get("lng"):
        warnings.append("缺少坐标")
    return warnings
```

**新增文件：** `proxy_crawler/quality.py`
**改动量：** ~40 行

---

## 6. 紧急 Bug 修复

小谷审计发现的 3 个 Bug，**Phase 1 开始前必须修掉**：

### Bug 1: currency 字段写死 'USD'

**文件：** `backend/proxy_crawler/run_hipflat_list.py` 第 212 行

```diff
- "currency": "USD",
+ "currency": "THB",
```

**影响：** 所有 HipFlat 房源货币显示为 USD，影响前端价格展示。

### Bug 2: docker-compose REDIS_URL 拼写错误

**文件：** `docker-compose.yml` 第 72 行

```diff
- REDIS_URL: "redis://redis:***@db:5432"
+ REDIS_URL: "redis://redis:6379/0"
```

**影响：** docker-compose 本地开发环境 REDIS 连接失败。

### Bug 3: main.py 前端 dist 路径兜底过多

**文件：** `main.py` 中 4 个候选路径兜底

**方案：** 创建 `docker/startup.sh` 统一入口，设置环境变量 `FRONTEND_DIST_PATH`。

```bash
# docker/startup.sh
#!/bin/bash
set -e

# 统一前端 dist 路径
export FRONTEND_DIST_PATH="/app/frontend-react/dist"

if [ ! -d "$FRONTEND_DIST_PATH" ]; then
    echo "WARNING: Frontend dist not found, trying /app/frontend/dist"
    export FRONTEND_DIST_PATH="/app/frontend/dist"
fi

cd /app/backend
alembic upgrade head 2>/dev/null || echo "No pending migrations"
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

**新增文件：** `docker/startup.sh`
**修改文件：** `Dockerfile`（CMD 简化为 `["/startup.sh"]`）

---

## 7. 分支策略与提交顺序

```bash
dev                       # 开发分支
├── fix/currency-thb      # Bug 1: currency
├── fix/redis-url         # Bug 2: REDIS_URL
├── fix/startup-script    # Bug 3: dist 路径 + startup.sh
├── feat/fazwax-fix       # Phase 1: FazWaz 修复
├── feat/livingstock      # Phase 1: LivingStock 爬虫
├── feat/base-crawler     # Phase 2: 爬虫基类
├── feat/incremental      # Phase 2: 增量爬取
├── feat/cron-crawl       # Phase 2: 定时爬虫
└── feat/renthub          # Phase 3: Renthub 爬虫
```

**提交顺序：**
1. fix/ 分支（3 个 Bug）→ 合并到 dev
2. feat/fazwax-fix → 合并到 dev
3. feat/livingstock → 合并到 dev
4. **Phase 1 完成 → 验证**
5. feat/base-crawler → 合并到 dev
6. feat/incremental + feat/cron-crawl → 合并到 dev
7. **Phase 2 完成 → 验证**
8. feat/renthub → 合并到 dev

每次合并到 dev 后进行验证，确认不破坏现有功能。

---

## 8. 架构变更示意

```
当前:
  run_hipflat_list.py ──▶ ScrapingAnt ──▶ HipFlat ──▶ SQLite/PostgreSQL
                         (单点依赖, 无重试)

Phase 1 后:
  HipFlat ──▶ run_hipflat_list.py ──┐
  FazWaz ───▶ fazwax_crawler.py ────┤
  LivingStock ▶ livingstock_crawler.py ──▶ ProxyAdapter ──▶ PostgreSQL
                        (ScrapingAnt + 重试 + 限速)

Phase 2 后:
  registry.py ──▶ 遍历所有 BaseCrawler 子类
                    │
                    ├── HipFlatCrawler    (继承 base_crawler)
                    ├── FazWazCrawler     (继承 base_crawler)
                    ├── LivingStockCrawler (继承 base_crawler)
                    └── target: 2000+ 房源
                         │
                         ▼
                    PostgreSQL ──▶ FastAPI ──▶ React Frontend
                         │
                    cron_crawl.py (每 6h 增量)

Phase 3 后:
                    新增 RenthubCrawler + 数据校验拦截器
                    目标: 2500+ 房源
```

---

> 本方案基于小谷的 `docs/improvement-plan.md` 制定，优先实施 Phase 1-2。
> 爱泰按此方案编码，完成后提交 dev 分支，小周审查后合并到 main。
