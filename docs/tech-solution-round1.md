# 清迈房产比价平台 — 技术方案 v1（P0-P1）

> **基于**: docs/project-audit-report.md (调研报告) + docs/improvement-plan.md (小谷改进方案)
> **作者**: 小开 (虾蟹联军)
> **日期**: 2026-06-16
> **分支**: dev

---

## 目录

1. [设计原则](#1-设计原则)
2. [P0 — 数据源扩充与爬虫重构](#2-p0--数据源扩充与爬虫重构)
3. [P1 — 爬虫架构升级与定时调度](#3-p1--爬虫架构升级与定时调度)
4. [P1 — 部署优化](#4-p1--部署优化)
5. [P1 — 前端体验提升](#5-p1--前端体验提升)
6. [紧急修复项](#6-紧急修复项)
7. [实施排期与依赖关系](#7-实施排期与依赖关系)
8. [风险与回退方案](#8-风险与回退方案)

---

## 1. 设计原则

| 原则 | 说明 |
|------|------|
| **增量改动** | 每次 PR 只改一个模块，零重构溢出 |
| **向后兼容** | 所有 API 保持现有响应格式，新字段 optional |
| **可回退** | 每个改动有明确的回退步骤（git revert + 配置恢复） |
| **可验证** | 每个 PR 后运行 seed_data 验证功能正常 |

---

## 2. P0 — 数据源扩充与爬虫重构

### 2.1 目标

从 1 个数据源（HipFlat，~148条）→ 3 个数据源，房源量 148 → 1500+

### 2.2 爬虫基类（base_crawler.py）— 前置条件

新建 `backend/proxy_crawler/base_crawler.py`，抽取所有爬虫的公共逻辑。

```python
# 核心接口
class BaseCrawler(ABC):
    SOURCE: str = ""
    BASE_URL: str = ""
    RATE_LIMIT: float = 2.0
    MAX_RETRIES: int = 3

    @abstractmethod
    def parse_list(self, html: str) -> list[dict]:
        """解析列表页 → [{url, title, price_text, source_id, ...}]"""
        # 子类覆盖，返回要爬取的房源基本信息

    @abstractmethod
    def parse_detail(self, html: str, listing: dict) -> dict:
        """解析详情页 → 完整财产字典"""

    def validate(self, data: dict) -> list[str]:
        """数据校验，返回警告列表"""
        warnings = []
        if not data.get("title"): warnings.append("缺少标题")
        if not (data.get("price_rent") or data.get("price_sale") or data.get("price")):
            warnings.append("缺少价格")
        return warnings

    def fetch(self, url: str) -> str:
        """通过 ProxyAdapter 获取 HTML（带重试+限速）"""
        ...

    async def crawl(self) -> dict:
        """统一的爬取入口：
           返回 {"new": N, "updated": M, "errors": [...], "total": N+M}
           1. 列表页 → 提取 URL + 基本信息
           2. 去重（对比 DB source + source_id）
           3. 新 URL → 详情页 → 入库
           4. 已有 URL → 更新价格/active 状态
        """
        ...

    def to_property_dict(self, raw: dict) -> dict:
        """将爬虫原始输出转换为 ORM 字段名（price → price_rent/price_sale 等）"""
        ...
```

**文件清单:**
- `backend/proxy_crawler/base_crawler.py` — 新建
- `backend/proxy_crawler/parsers.py` — 改造三个 Parser 继承 BaseCrawler
- `backend/run_crawlers.py` — 重写为统一入口

**回退方案:** 删除 base_crawler.py，恢复 parsers.py 旧版本，删掉 import

### 2.3 HipFlat 爬虫适配（改）

现有 `run_hipflat_list.py` 改造为继承 BaseCrawler。

**改动要点:**
- 抽取 HipflatCrawler(BaseCrawler)，SOURCE="hipflat"
- `parse_list()` 直接复用现有 `parse_snippet()` 逻辑
- 去掉直接写 SQL，改为通过 ORM 入库
- 修复已知 bug：currency 从 `"USD"` → `"THB"`（第 189 行）
- 不再需要单独的 `save_to_db()`

**文件变更:**
- `backend/proxy_crawler/parsers.py` — HipflatParser → HipflatCrawler
- `backend/run_hipflat_list.py` — 保留为 CLI 兼容入口，调用 HipflatCrawler

**验证标准:** 运行 `python backend/run_hipflat_list.py` 能正常爬取并入库

### 2.4 FazWaz 爬虫修复

**当前问题:** 详情页价格是 JS 动态渲染，ScrapingAnt 拿不到。

**修复方案:** 从 **列表页 JSON-LD** 提前提取价格，避免依赖详情页。

**文件变更:**
- `backend/proxy_crawler/parsers.py` — FazwazParser → FazwazCrawler(BaseCrawler)
- 核心改动: `crawl()` 流程改成"列表页 JSON-LD 提取价格 → 详情页只补描述/图片"

```python
class FazwazCrawler(BaseCrawler):
    SOURCE = "fazwaz"
    BASE_URL = "https://www.fazwaz.com"

    def parse_list(self, html: str) -> list[dict]:
        # 从 JSON-LD 提取：url, price, title, bedrooms, location
        listings = []
        for script in sel.css('script[type="application/ld+json"]::text').getall():
            data = json.loads(script)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Product":
                    url = item.get("url", "")
                    offers = item.get("offers", {})
                    price = float(offers.get("price", 0)) if offers.get("price") else None
                    if url and price and "chiang-mai" in url.lower():
                        listings.append({
                            "url": url,
                            "source_id": re.search(r"/(\d+)(?:/|$)", url).group(1) if re.search(r"/(\d+)(?:/|$)", url) else "",
                            "title": item.get("name", ""),
                            "price": price,
                            "location": ...,
                        })
        return listings
```

**验证标准:** 爬取 50+ 条 FazWaz 清迈房源，90%+ 有价格

### 2.5 LivingStock 爬虫（新增）

**文件:**
- `backend/proxy_crawler/parsers.py` — 新增 `LivingstockCrawler(BaseCrawler)`
- 爬取 `https://www.livingstock.com/property-for-rent/chiang-mai` 和 `.../chiang-mai/sale`

**特点:**
- 服务端渲染，HTML 结构稳定
- 列表页直接包含价格/卧室/面积，暂不爬详情页

**验证标准:** 成功爬取 100+ 条 LivingStock 清迈房源

### 2.6 数据去重与入库统一

**核心逻辑**（统一在 BaseCrawler.crawl() 中）：

```python
async def upsert_property(db, source: str, source_id: str, data: dict) -> str:
    """返回 "new" / "updated" / "skipped" """
    existing = await db.execute(
        select(Property).where(
            Property.source == source,
            Property.source_id == str(source_id),
        )
    )
    prop = existing.scalar_one_or_none()
    if prop:
        # 记录旧价格到 PriceHistory
        if _price_changed(prop, data):
            db.add(PriceHistory(
                property_id=prop.id,
                price_rent=data.get("price_rent"),
                price_sale=data.get("price_sale"),
                price_type=...,
                source=source,
            ))
        # 更新字段
        for key, val in data.items():
            setattr(prop, key, val)
        prop.updated_at = datetime.utcnow()
        return "updated"
    else:
        db.add(Property(**data))
        return "new"
```

---

## 3. P1 — 爬虫架构升级与定时调度

### 3.1 增量爬取机制

在 Property 模型新增字段（可选，基类手动维护也可）：

```python
# Property 模型新增
checked_at = Column(DateTime, nullable=True)  # 最近一次爬虫检查时间
```

**增量爬取策略:**
- **新数据源:** 全量爬取，`scraped_at = now`
- **已有数据:** 检查 `scraped_at > now - 6h` → 跳过
- **每日 03:00:** 全量刷新所有数据源

### 3.2 定时调度

使用 Hermes Agent cronjob 管理（更灵活，不用改 Dockerfile）：

```bash
# 每 6 小时增量
hermes cron create \
  --name "chiangmai-crawl-incremental" \
  --schedule "0 */6 * * *" \
  --prompt "运行 chiangmai-property 增量爬虫：cd /opt/data/chiangmai-property && python backend/run_crawlers.py --incremental" \
  --deliver "local"

# 每日 03:00 全量
hermes cron create \
  --name "chiangmai-crawl-full" \
  --schedule "0 3 * * *" \
  --prompt "运行 chiangmai-property 全量爬虫：cd /opt/data/chiangmai-property && python backend/run_crawlers.py --full" \
  --deliver "local"
```

**回退方案:** 移除 cronjob，手动 `python run_crawlers.py` 运行

### 3.3 数据校验拦截器

BaseCrawler.validate() 返回警告列表，爬虫运行时记录到日志并统计：

```python
stats = {
    "source": "fazwaz",
    "total": 200,
    "new": 45,
    "updated": 150,
    "errors": [
        {"url": "https://...", "warnings": ["缺少价格", "缺少面积"]},
    ],
    "duration_seconds": 120,
}
```

日志文件: `data/crawl_stats_YYYYMMDD.json`

---

## 4. P1 — 部署优化

### 4.1 startup.sh 统一入口

新建 `docker/startup.sh`：

```bash
#!/bin/bash
set -e

echo "=== Startup ==="

# 检查前端 dist
if [ -d "/app/frontend-react/dist" ]; then
    echo "✅ Frontend dist found at /app/frontend-react/dist"
else
    echo "⚠️ Frontend dist not found"
fi

# 运行数据库迁移
cd /app/backend
echo "Running startup..."
python startup.py

# 启动后端
echo "Starting uvicorn on 0.0.0.0:${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### 4.2 Dockerfile 简化

CMD 改为：

```dockerfile
COPY docker/startup.sh /startup.sh
RUN chmod +x /startup.sh
CMD ["/startup.sh"]
```

### 4.3 修复 docker-compose.yml REDIS_URL

**当前（错误）:**
```
REDIS_URL: redis://redis:***@db:5432
```

**修复后:**
```
REDIS_URL: redis://redis:6379/0
```

### 4.4 新增 .env.template

```ini
# 数据库
DATABASE_URL=sqlite+aiosqlite:///./cmproperty.db
# 生产用：DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=change-me-to-a-random-string
JWT_SECRET=change-me-too

# 代理（爬虫用）
PROXY_ENABLED=false
SCRAPINGANT_API_KEY=your-key-here

# 环境
ENV=development
DEBUG=true
```

**文件变更:** 新增 `.env.template`（根目录）

---

## 5. P1 — 前端体验提升

### 5.1 骨架屏（PropertyCardSkeleton）

新建 `frontend-react/src/components/PropertyCardSkeleton.jsx`：

```jsx
export default function PropertyCardSkeleton() {
  return (
    <div className="property-card skeleton">
      <div className="skeleton-img" style={{ height: 120, background: '#eee', borderRadius: 8 }} />
      <div className="skeleton-body" style={{ padding: 8 }}>
        <div className="skeleton-line" style={{ height: 14, width: '60%', background: '#eee', marginBottom: 6 }} />
        <div className="skeleton-line" style={{ height: 12, width: '40%', background: '#eee' }} />
      </div>
    </div>
  )
}
```

HomePage 加载时显示 6 个 Skeleton 替换 DotLoading。

### 5.2 搜索防抖

SearchPage 添加 300ms debounce：

```jsx
// frontend-react/src/pages/SearchPage.jsx
import { useDebounce } from 'ahooks'  // 或自实现

const [keyword, setKeyword] = useState('')
const debouncedKeyword = useDebounce(keyword, { wait: 300 })

useEffect(() => {
  if (debouncedKeyword) loadProperties(1)
}, [debouncedKeyword])
```

### 5.3 价格输入优化

在价格输入框右侧加单位提示：

```jsx
<Input
  placeholder={t('minPrice')}
  suffix={t('priceUnit')}  // "万THB/月"
/>
```

### 5.4 地图 Marker 聚集

```bash
npm install leaflet.markercluster
```

MapPage 使用 `L.markerClusterGroup()` 管理 markers，100m 半径聚合。

---

## 6. 紧急修复项

| # | 问题 | 文件 | 修复 |
|---|------|------|------|
| 1 | currency 误写 `USD` → `THB` | `run_hipflat_list.py:189` | `'USD'` → `'THB'` |
| 2 | docker-compose REDIS_URL 错误 | `docker-compose.yml:72` | `redis://redis:***@db:5432` → `redis://redis:6379/0` |
| 3 | healthcheck 命令 | `Dockerfile:32` | `python3 -c "..."` → `curl -f` |

---

## 7. 实施排期与依赖关系

```
Phase 1 (2天) — P0 数据源
  ├─ Task 1.1: BaseCrawler 基类 (deps: 无)
  ├─ Task 1.2: HipFlat 适配基类 + 修复 currency (deps: 1.1)
  ├─ Task 1.3: FazWaz 价格修复 (deps: 1.1)
  └─ Task 1.4: LivingStock 爬虫 (deps: 1.1)

Phase 2 (2天) — P1 爬虫架构
  ├─ Task 2.1: 增量爬取 + 去重统一 (deps: 1.1)
  ├─ Task 2.2: 定时调度 cronjob (deps: 2.1)
  ├─ Task 2.3: 数据校验 + 日志 (deps: 1.1)
  └─ Task 2.4: 紧急修复 (deps: 无)

Phase 3 (1天) — P1 部署
  ├─ Task 3.1: startup.sh + Dockerfile 简化 (deps: 无)
  ├─ Task 3.2: .env.template (deps: 无)
  └─ Task 3.3: docker-compose 修复 (deps: 无)

Phase 4 (1天) — P1 前端
  ├─ Task 4.1: 骨架屏 (deps: 无)
  ├─ Task 4.2: 搜索防抖 (deps: 无)
  ├─ Task 4.3: 价格输入优化 (deps: 无)
  └─ Task 4.4: 地图 Cluster (deps: 无)
```

**总计估算:** 6 个工作日（无并行阻塞时）

**建议执行顺序:** Phase 3.3 + 2.4（紧急修复）→ Phase 1 → Phase 2 → Phase 3 → Phase 4

---

## 8. 风险与回退方案

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| ScrapingAnt 免费额度耗尽 | 中 | 爬虫停摆 | 切换 ZenRows/Crawlbase（adapter 已支持） |
| LivingStock 网站改版 | 低 | 爬虫失效 | 爬虫基类的 parse_list 封装备选选择器 |
| 爬虫基类重构破坏 HipFlat | 低 | 核心功能不可用 | `run_hipflat_list.py` 保留为独立 CLI 入口 |
| Railway 不支持 Hermes cron | 中 | 定时爬虫无法部署 | 用 Railway Cron Job + curl 触发 |
| 前端骨架屏改动影响首页 | 低 | 首页样式错乱 | CSS 独立加 `.skeleton` class，无侵入 |

---

> 本文档由小开基于小谷审计报告 + 原始调研报告整合编写
> 存放路径: `docs/tech-solution-round1.md`（dev 分支）
