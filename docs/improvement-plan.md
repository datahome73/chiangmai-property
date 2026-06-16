# 清迈房产比价平台 — 改进方案

> 基于完整代码审计后的系统改进路线图
> 审计日期: 2026-06-16
> 分支: dev

---

## 目录

1. [当前项目概况](#1-当前项目概况)
2. [深度审计发现的问题](#2-深度审计发现的问题)
3. [改进路线图（按优先级）](#3-改进路线图按优先级)
4. [各模块详细方案](#4-各模块详细方案)
5. [实施排期](#5-实施排期)

---

## 1. 当前项目概况

| 维度 | 状态 |
|------|------|
| **后端** | FastAPI + async SQLAlchemy + Alembic — ✅ 架构优秀 |
| **前端** | React 18 + Vite 6 + antd-mobile 5 — ✅ 结构完整 |
| **数据源** | 仅 HipFlat（~148条），FazWaz 半残，DDProperty 被封 |
| **爬虫** | 代理 API（ScrapingAnt）单点依赖，无重试框架 |
| **AI分析** | 纯本地规则引擎（强），可考虑接入LLM增强 |
| **i18n** | 中/英/泰三语 ✅ 已完整实现 |
| **部署** | Railway Docker，多阶段构建 ✅ |
| **测试** | ❌ 无单元测试/集成测试 |
| **CI/CD** | ❌ 无 GitHub Actions |
| **运营** | 无定时爬虫、数据校验、审核机制 |

---

## 2. 深度审计发现的问题

### 2.1 数据源单薄且不稳定

**严重程度：🟥 高**

- 仅 **HipFlat** 一个数据源稳定运行（~148条）
- FazWaz 爬虫存在但详情页价格缺失严重，前端无法使用
- DDProperty 被 Cloudflare 完全封锁，爬虫白费
- 单点依赖 ScrapingAnt，切换成本高
- **房源总量严重不足** — 清迈实际可租房源在各大平台合计超 5000+ 条

### 2.2 爬虫架构问题

**严重程度：🟧 中**

| 问题 | 说明 |
|------|------|
| `run_hipflat_list.py` 直接写 SQL | 绕过 ORM 和 Alembic 迁移 |
| 爬虫硬编码 API Key | `.env.railway` 中的 API key 代码里也有 Fallback |
| 无爬虫基类 | 每个爬虫自实现 fetch/parse，代码重复严重 |
| 无增量爬取 | 每次都全量重写，浪费额度 |
| 无数据校验 | 缺失字段无默认兜底，空价格/空标题直接入库 |

### 2.3 Docker 部署问题

**严重程度：🟧 中**

- **CMD 过长**（110字符），单行含多个 `&&`，可读性差
- 无 `startup.sh` 统一入口，不符合 Docker 最佳实践
- 前端 dist 路径在 `main.py` 中做了 4 个候选路径兜底，但仍可能在部分环境找不到
- `docker-compose.yml` 中 REDIS_URL 拼接错误（`redis://redis:***@db:5432`）

### 2.4 前端功能缺口

**严重程度：🟧 中**

| 缺口 | 说明 |
|------|------|
| 筛选弹窗 UX | 价格输入框无单位提示，用户可能误输 10000 而非 1 |
| 地图性能 | 每次 `moveend` 都请求后端，拖动时高频触发 |
| 首次加载 | 无骨架屏（Skeleton），白屏等待 |
| 搜索体验 | 搜索需点"搜索"按钮，无防抖自动搜索 |
| 详情页 | 无价格走势图、AI 分析按钮虽有但默认折叠 |
| 骨架屏 | 完全缺失，loading 只是 DotLoading 转圈 |

### 2.5 后端功能缺口

**严重程度：🟨 低**

| 功能 | 说明 |
|------|------|
| 无房源发布 API | 用户不能自行发布房源 |
| 无联系中介 | 详情页"联系中介"按钮无后端实现 |
| 无站内通知 | 无消息系统 |
| 无数据看板 | 无房源浏览量、收藏统计 |
| 无搜索日志 | 无法分析用户搜索行为 |

### 2.6 工程化缺失

**严重程度：🟨 低**

| 缺失 | 影响 |
|------|------|
| 单元测试 | 无法安全重构 |
| CI/CD | 合并到 main 无自动验证 |
| Code linting | 无 Ruff/ESLint 配置 |
| 代码格式化 | 无统一风格 |

---

## 3. 改进路线图（按优先级）

### P0 — 数据源扩充（🚀 最紧急）

```
Week 1-2 核心目标：从 1 个数据源 → 4 个数据源，房源量 148 → 2000+
```

1. **修复 FazWaz 爬虫** — 当前价格从详情页提取，改从列表页 JSON-LD 提取
2. **新增 LivingStock 爬虫** — 泰国 active 的中介房源平台
3. **新增 Renthub 爬虫** — 全泰最大租房平台
4. **新增 BaanFinder 爬虫** — 清迈本地房源丰富
5. DDProperty 绕 CF → 延后处理（ZenRows/Playwright 方案验证）

### P1 — 爬虫架构升级

1. 提取 `base_crawler.py` 基类（重试/限速/去重/校验）
2. 重构现有爬虫继承基类
3. 实现增量爬取机制（`checked_at` 字段 + URL hash 去重）
4. 配置定时爬虫（Railway Cron Job，每 6h 增量，每日全量）
5. 数据校验拦截器（字段缺失/价格异常/图片404检测）

### P2 — 部署优化

1. 创建 `docker/startup.sh` 统一启动入口
2. 简化 Dockerfile CMD
3. 修复 docker-compose REDIS_URL
4. 增加 `.env.template` 说明文档

### P3 — 前端体验提升

1. 添加骨架屏（Skeleton Screen）
2. 搜索防抖自动搜索（300ms debounce）
3. 价格输入框加单位提示（万泰铢/THB）
4. 地图 marker 聚集（Cluster） — 500+ 房源时性能关键
5. AI 分析结果显示优化（评分可视化条）

### P4 — 工程化

1. GitHub Actions CI （`dev` push 自动运行 lint + test）
2. 添加 `pytest` 测试框架 + 基础测试
3. Ruff lint 配置
4. 添加 `pre-commit` hooks

---

## 4. 各模块详细方案

### 4.1 爬虫基类（base_crawler.py）

```python
# backend/proxy_crawler/base_crawler.py
class BaseCrawler(ABC):
    SOURCE: str = ""
    BASE_URL: str = ""
    RATE_LIMIT: float = 2.0
    MAX_RETRIES: int = 3

    @abstractmethod
    def parse_list(self, html: str) -> list[dict]:
        """解析列表页，返回 [{url, title, price_text, ...}]"""
        ...

    @abstractmethod
    def parse_detail(self, html: str, listing: dict) -> dict:
        """解析详情页，返回完整财产字典"""
        ...

    def validate(self, data: dict) -> list[str]:
        """数据校验，返回警告列表"""
        warnings = []
        if not data.get("title"): warnings.append("缺少标题")
        if not (data.get("price_rent") or data.get("price_sale")): warnings.append("缺少价格")
        return warnings

    async def crawl(self) -> tuple[int, int]:
        """
        返回 (new_count, updated_count)
        1. 列表页 → 提取 URL 列表
        2. 去重（对比 DB 已有 source_id）
        3. 新 URL → 爬详情 → 入库
        4. 已有 URL → 更新价格/状态
        """
        ...
```

### 4.2 FazWaz 价格修复

**当前问题：** `FazWazParser.parse_listing()` 尝试从详情页 `<span>` 提取价格，但 FazWaz 的价格在详情页是 JS 动态渲染的，ScrapingAnt 拿不到。

**修复方案：** 从 **列表页** 的 JSON-LD 中提取价格：

```python
def extract_price_from_list_json(html: str) -> dict[str, float]:
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

### 4.3 新增数据源对比

| 平台 | 特点 | 清迈房源量（估） | 封锁难度 | 优先级 |
|------|------|----------------|----------|--------|
| **HipFlat** ✅ | 已有，稳定 | ~200 | 低（已通） | — |
| **FazWaz** ⚠️ | 需修复 | ~800 | 中 | P0 |
| **LivingStock** | 中介房源，API友好 | ~500 | 低 | P0 |
| **Renthub** | 全泰最大租房 | ~1000 | 低 | P0 |
| **BaanFinder** | 清迈本地多 | ~300 | 低 | P1 |
| **DDProperty** | 泰国最大（被封） | ~2000 | 高（CF） | P2 |

### 4.4 Dockerfile 优化

```dockerfile
# Dockerfile 简化方案
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend-react
COPY frontend-react/package.json frontend-react/package-lock.json* ./
RUN npm ci && npm run build

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend-react/dist/ /app/frontend-react/dist/

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

COPY docker/startup.sh /startup.sh
RUN chmod +x /startup.sh
CMD ["/startup.sh"]
```

### 4.5 定时爬虫方案

利用 Railway Cron Job 或 Hermes cronjob：

```python
# backend/cron_crawl.py
"""
每 6 小时增量爬取：
1. HipFlat — 全量快（列表页即可）
2. FazWaz — 更新活跃房源价格
3. LivingStock — 增量新增
"""
```

建议用 Hermes Agent 的 cronjob 管理，更灵活：

```bash
# Hermes cronjob 配置
hermes cron create \
  --name "chiangmai-crawl" \
  --schedule "0 */6 * * *" \
  --prompt "运行 chiangmai-property 增量爬虫" \
  --skills "chiangmai-property" \
  --deliver "local"
```

### 4.6 前端性能优化清单

```
1. 首页骨架屏
   - PropertyCardSkeleton 组件（灰色占位块）
   - 加载时显示 6 个骨架卡

2. 搜索防抖
   - SearchBar onInput → 300ms debounce → 自动搜索
   - 保留"搜索"按钮作为手动触发

3. 价格输入优化
   - 输入框右侧标注"万泰铢/月"或"THB/month"
   - 自动换算提示

4. Map marker clustering
   - 使用 leaflet.markercluster 插件
   - 100m 聚合阈值

5. AI 评分 UI
   - 进度条式评分显示
   - 颜色梯度（红<50, 黄50-70, 绿>70）
```

---

## 5. 实施排期

| 阶段 | 内容 | 估时 | 产出 |
|------|------|------|------|
| **Phase 1** | FazWaz 价格修复 + LivingStock 爬虫 | 2天 | 数据源增至 3 个，房源 ~1500+ |
| **Phase 2** | 爬虫基类抽取 + 增量爬取 + 定时任务 | 2天 | 爬虫可维护，每日自动更新 |
| **Phase 3** | Renthub 爬虫 + 数据校验 | 1天 | 数据源增至 4 个，房源 ~2500+ |
| **Phase 4** | Docker 部署优化 + 前端骨架屏/搜索防抖 | 1天 | 部署稳定，首屏体验提升 |
| **Phase 5** | 地图 Cluster + AI 评分 UI | 1天 | 500+ 房源地图不卡顿 |
| **Phase 6** | CI/CD + 测试框架 | 1天 | 安全重构的基础 |

**总计：8 个工作日**

---

## 附：紧急修复项（不影响主线）

- [ ] `docker-compose.yml` 第 72 行 REDIS_URL 拼写错误（`redis://redis:***@db:5432` → `redis://redis:6379/0`）
- [ ] `run_hipflat_list.py` 第 212 行 currency 错误写为 `'USD'`，应为 `'THB'`
- [ ] `main.py` 启动时前端 dist 路径兜底过多，应用 `startup.sh` 统一处理

---

> 本文档由小谷基于 2026-06-16 完整代码审计生成
> 存放路径: `docs/improvement-plan.md`（dev 分支）
