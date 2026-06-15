# 清迈房产比价平台 — 技术实施方案

> 基于小谷调研报告及代码审查，覆盖数据卷、Railway 部署、功能增强三大模块

## 1. 数据卷配置方案

### 1.1 生产环境（Railway）数据持久化

Railway 的 PostgreSQL 和 Redis 插件自带持久化，无需额外配置数据卷。

| 组件 | Railway 方案 | 说明 |
|------|-------------|------|
| PostgreSQL | Railway Postgres 插件 | 自动备份，每日快照 |
| Redis | Railway Redis 插件 | 可选，仅缓存不持重 |
| 爬虫图片 | Railway Volumes | 挂载 `$RAILWAY_VOLUME_MOUNT_PATH/images/` |
| 爬虫数据快照 | 数据库持久 | 直接写入 PostgreSQL |

### 1.2 Docker Compose 本地/自建方案

`docker-compose.prod.yml` 已配置 PostGIS + Redis 数据卷。优化建议：

```yaml
volumes:
  postgres_data:           # 已有，保留
  redis_data:              # 新增
  crawler_cache:           # 新增 — 爬虫去重/缓存
```

**新增 `.env.template`（数据卷路径安全）：**

```bash
# 数据卷路径 — 非 Docker 环境可设置绝对路径
VOLUME_BASE=/opt/chiangmai-property/data
DB_PASSWORD=changeme_prod
```

## 2. Railway 部署方案

### 2.1 当前问题

| 问题 | 影响 |
|------|------|
| `Dockerfile` 中前端 dist 路径硬编码 | 运行时找不到 `frontend-react/dist/` |
| 单容器运行（后端+前端都在同一容器） | 耦合度高，扩展性差 |
| 缺少 startup.sh 作为官方入口点 | 启动时依赖 Dockerfile CMD 里的复杂 shell |
| 没有 `Procfile` | Railway 无法灵活配置进程 |
| 爬虫任务无法在 Railway 独立运行 | 没有独立 worker 进程 |

### 2.2 改进方案

**改进 Dockerfile：**

```dockerfile
# ===== Stage 1: Build Frontend =====
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend-react/package.json frontend-react/package-lock.json* ./
RUN npm ci
COPY frontend-react/ ./
RUN npm run build

# ===== Stage 2: Build Backend =====
FROM python:3.11-slim
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend to a KNOWN location
COPY --from=frontend-builder /app/dist/ ./frontend/dist/

# Health check — checks real frontend path
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python3 -c "import urllib.request,os; p=os.environ.get('PORT','8000'); urllib.request.urlopen(f'http://localhost:{p}/health')" || exit 1

# Entry point script
COPY docker/startup.sh /startup.sh
RUN chmod +x /startup.sh
CMD ["/startup.sh"]
```

**新增 `docker/startup.sh`：**

```bash
#!/bin/bash
set -e

# 确保前端构建产物路径
FRONTEND_DIST="/app/frontend/dist"
if [ ! -d "$FRONTEND_DIST" ]; then
    echo "WARNING: Frontend dist not found at $FRONTEND_DIST — trying alternatives"
    ls -la /app/frontend/ 2>/dev/null || true
fi

# 只运行数据库迁移（不运行 seed_data）
cd /app/backend
alembic upgrade head 2>/dev/null || echo "No pending migrations"

# 启动
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

**更新 `railway.json`：**

```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "numReplicas": 1,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### 2.3 爬虫 Worker（Railway 独立服务）

Railway 不支持 Docker Compose，但支持多 Service：

1. **Web Service** (当前) — API + 前端
2. **Cron Job Service** (新增) — 定时爬虫

在 Railway Dashboard 创建第二个 Service，使用相同 Dockerfile，但添加 `--worker` 标志和 `Procfile`：

```bash
# Procfile
web: /startup.sh
worker: cd /app/backend && python run_hipflat_list.py
```

### 2.4 Railway 环境变量清单

| 变量 | 来源 | 必填 | 说明 |
|------|------|------|------|
| `PORT` | Railway 自动 | ✅ | 动态端口 |
| `DATABASE_URL` | Railway PG 插件 | ✅ | `postgresql+asyncpg://...` |
| `DATABASE_URL_SYNC` | 手动设置 | ✅ | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Railway Redis 插件 | 可选 | 缓存加速 |
| `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` | ✅ | JWT 签名密钥 |
| `ENV` | 手动设置 | ✅ | `production` |
| `PROXY_ENABLED` | 手动设置 | 可选 | `false`（暂无多数据源） |
| `SCRAPINGANT_API_KEY` | ScrapingAnt 注册 | 可选 | 多个数据源时才需 |

## 3. 待完善功能的技术实现方案

### 3.1 爬虫稳定性增强

**当前状态：** 仅 HipFlat 一个数据源，ScrapingAnt 代理 API，无重试/去重/增量机制

**实现方案：**

#### A. 多数据源适配器框架

```
backend/proxy_crawler/
├── __init__.py
├── proxy_adapter.py        # 通用 ScrapingAnt 适配器（已有）
├── parsers.py              # 通用 HTML 解析器（已有）
├── base_crawler.py         # 新增：爬虫基类（重试/去重/限速）
├── hipflat_crawler.py      # 已有，但重构继承 base_crawler
├── fazwaz_crawler.py       # 新增：FazWaz 爬虫
├── ddproperty_crawler.py   # 新增：DDProperty 爬虫（需绕过 CF）
├── renthub_crawler.py      # 新增：Renthub 爬虫
├── kaidee_crawler.py       # 新增：Kaidee 爬虫
└── storage.py              # 新增：数据去重和存储逻辑
```

#### B. 爬虫基类关键特征

```python
# base_crawler.py 核心方案
class BaseCrawler(ABC):
    RETRY_COUNT = 3
    RETRY_DELAY = 2        # 秒
    RATE_LIMIT = 2.5       # 请求间隔
    CACHE_TTL = 3600       # 去重缓存 1h
    
    @abstractmethod
    async def parse_listing(self, html: str) -> list[dict]: ...
    @abstractmethod
    async def parse_detail(self, html: str, listing: dict) -> dict: ...
    
    async def crawl(self) -> int:
        """带重试、限速、去重的全量爬取"""
        ...
```

#### C. 增量爬取实现

在 `Property` 模型中加入 `checked_at` 字段。爬虫运行策略：

```
首轮 → 全量爬取 → 写入 DB
后续 → 爬取列表页 → 比对 URL hash → 新增+过期标记
        - 已有(checked_at < 24h) → 跳过
        - 已有(checked_at > 24h) → 更新价格/状态
        - 新 URL → 爬详情页插入
```

#### D. 定时爬虫（cronjob）

在 Railway 创建 Cron Job Service：

```yaml
# railway.toml（Railway Cron Job 配置）
[cron]
schedule = "0 */6 * * *"  # 每6小时
command = "python /app/backend/cron_crawl.py"
```

创建 `backend/cron_crawl.py`：

```python
"""定时爬虫入口 — 遍历所有数据源执行增量爬取"""
from proxy_crawler.hipflat_crawler import HipFlatCrawler
# 后续添加其他数据源

async def main():
    crawler = HipFlatCrawler()
    count = await crawler.crawl()
    print(f"HipFlat: {count} properties updated")
```

#### E. Cloudflare 绕过方案（DDProperty）

当前 DDProperty 被 CF 封锁。三阶段方案：

| 阶段 | 方案 | 复杂度 | 效果 |
|------|------|--------|------|
| 1 | ScrapingAnt 启用 JS Rendering | 低 | 可能有效 |
| 2 | Playwright 浏览器自动机 | 中 | 稳定但资源大 |
| 3 | 第三方数据 API（如 SerpAPI） | 中 | 稳定需付费 |

推荐先试阶段 1，ScrapingAnt 有 JS Rendering 参数（`wait_for_selector` + `render_js=true`）。

### 3.2 i18n 国际化补全

**当前状态：** `i18n.jsx` 骨架存在但翻译未填充，前端硬编码中文。

**实现方案：**

#### A. 后端 API i18n 支持（新增）

```
backend/
├── app/
│   ├── i18n/
│   │   ├── __init__.py       # 语言加载器
│   │   ├── zh.json           # 中文（默认）
│   │   └── en.json           # 英文
│   ├── middleware/
│   │   └── locale.py         # 新增：Accept-Language 中间件
```

```python
# locale.py
from fastapi import Request
from app.i18n import get_translator

async def locale_middleware(request: Request, call_next):
    lang = request.headers.get("Accept-Language", "zh")[:2]
    if lang not in ("zh", "en"):
        lang = "zh"
    request.state._ = get_translator(lang)
    return await call_next(request)
```

#### B. 前端 i18n 填充

当前 `frontend-react/src/i18n.jsx` 只有骨架。填充步骤：

```javascript
// i18n.jsx — 完整实现
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

const resources = {
  zh: {
    translation: {
      nav: { home: '首页', favorites: '收藏', profile: '我的' },
      property: { rent: '出租', sale: '出售', bedrooms: '室', area: '面积' },
      search: { placeholder: '搜索房源...', filter: '筛选', reset: '重置' },
      // ... 完整翻译键值对
    }
  },
  en: {
    translation: {
      nav: { home: 'Home', favorites: 'Favorites', profile: 'Profile' },
      property: { rent: 'Rent', sale: 'Sale' },
      // ...
    }
  }
};
```

**依赖：** `npm install i18next react-i18next i18next-browser-languagedetector`

### 3.3 AI 分析增强

**当前状态：** 纯本地规则引擎（无 LLM），评分仅靠价格/面积/位置等简单维度。

#### A. 增强方向（分阶段）

| 阶段 | 特性 | 实现方式 |
|------|------|----------|
| P0 | LLM 房源描述总结 | `POST /properties/{id}/ai-summary` 调用外部 AI API |
| P1 | 价格预测模型 | 历史数据 + scikit-learn 线性回归 |
| P2 | 智能推荐 | 协同过滤（用户收藏行为） |
| P3 | 市场洞察报告 | LLM + 统计数据自动生成 |

#### B. P0 — LLM 总结（快速实现）

```python
# app/services/llm_analysis_service.py
import httpx, os

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")

async def llm_property_summary(property_data: dict) -> str:
    """调用 LLM 生成房源自然语言总结"""
    if not LLM_API_KEY:
        return _fallback_summary(property_data)  # 降级到规则引擎
    
    prompt = f"请用中文为清迈的这套{property_data['property_type']}房源写一段100字以内的简介，突出亮点：{json.dumps(property_data, ensure_ascii=False)}"
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(LLM_API_URL, json=..., headers={"Authorization": f"Bearer {LLM_API_KEY}"})
        return resp.json()["choices"][0]["message"]["content"]
```

#### C. P1 — 价格预测模型

```python
# backend/services/price_prediction.py
"""
使用 scikit-learn 训练房价预测模型
特征：区域、面积、卧室数、楼层、装修、到市中心距离

依赖：scikit-learn, numpy, pandas（放入 requirements.prod.txt）
"""

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
import joblib

MODEL_PATH = "/app/backend/price_model.pkl"

def train_model(properties_df):
    """训练价格预测模型"""
    # 特征工程
    features = ["area_sqm", "bedrooms", "total_floors", "furnished",
                "district_encoded", "property_type_encoded", "lat", "lng"]
    X = properties_df[features]
    y = properties_df["price_rent"].fillna(properties_df["price_sale"])
    
    model = RandomForestRegressor(n_estimators=100, max_depth=10)
    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)

async def predict_price(property_data):
    """预测房源合理价格"""
    if not os.path.exists(MODEL_PATH):
        return None
    model = joblib.load(MODEL_PATH)
    # ... 特征转换 + 预测
    return {"predicted_price": float(pred), "confidence": "high" if n_samples > 200 else "low"}
```

### 3.4 自动化抓取

**方案：** 基于 Railway Cron Job + 增量爬虫 + 自动推送

**架构：**

```
[Railway Cron Job] → cron_crawl.py
    ├── HipFlat（每6h） → 增量爬取 → DB 更新
    ├── FazWaz（每12h） → 同上
    ├── Renthub（每12h）→ 同上
    └── 数据校验 → 异常告警 → 站内通知
```

**数据校验组件：**

```python
# proxy_crawler/quality.py
def validate_property(prop: dict) -> list[str]:
    """数据质量校验，返回缺失字段列表"""
    warnings = []
    required = ["title", "price_rent", "district"]
    for field in required:
        if not prop.get(field):
            warnings.append(f"缺少{field}")
    if prop.get("price_rent", 0) < 500:
        warnings.append("价格异常低(<500฿)")
    return warnings
```

### 3.5 价格预测

详见 3.3-C。短期先实现基于统计的简单预测：

```python
# backend/services/simple_price_prediction.py
"""基于聚合统计的价格预测（无需 ML 依赖）"""

def estimate_fair_price(district: str, area_sqm: float, bedrooms: int, 
                        property_type: str) -> dict:
    """
    基于现有数据统计估算合理价格。
    
    方法：找同区同户型房源的均价 × 面积比例
    """
    # SQL: SELECT AVG(price_rent/area_sqm) FROM properties 
    #       WHERE district=X AND property_type=Y
    # 返回估算价格 + 置信区间
```

## 4. 实施优先级路线图

| 优先级 | 模块 | 工作量 | 依赖 | 建议执行 |
|--------|------|--------|------|----------|
| 🔴 P0 | Dockerfile + Railway 部署修复 | 1h | — | 立即 |
| 🔴 P0 | 多数据源爬虫框架 | 4h | — | 第2天 |
| 🟡 P1 | HipFlat 爬虫重构成 base_crawler | 1h | 框架 | 第2天 |
| 🟡 P1 | 定时爬虫 cronjob | 1h | 框架 | 第2天 |
| 🟡 P1 | i18n 填充（前端） | 2h | — | 第3天 |
| 🟡 P1 | LLM 房源总结 | 3h | API Key | 第3天 |
| 🟢 P2 | 价格预测模型 | 4h | 数据量>200条 | 第4天 |
| 🟢 P2 | 智能推荐 | 3h | 收藏数据 | 第5天 |
| 🟢 P3 | CI/CD GitHub Actions | 1h | — | 第6天 |
| 🟢 P3 | 单元测试补全 | 4h | — | 持续 |

## 5. GitHub 仓库分支策略

```bash
main        # 生产分支，直接部署到 Railway
├── dev     # 开发分支，合并后测试
├── feat/  # 功能分支
│   ├── feat/multi-source-crawler
│   ├── feat/i18n-full
│   ├── feat/price-prediction
│   └── feat/ci-cd
└── fix/    # 修复分支
```

**提交流程：**
```
feature branch → PR → dev → 验证 → main → Railway 自动部署
```

---

## 附：关键文件修改清单

| 文件 | 操作 | 简要说明 |
|------|------|----------|
| `Dockerfile` | 修改 | 修复前端 dist 路径，简化 CMD |
| `docker/startup.sh` | 新增 | 统一入口点 |
| `railway.json` | 修改 | update healthcheckTimeout |
| `.env.railway` | 更新 | 添加 SECRET_KEY 生成命令 |
| `backend/proxy_crawler/base_crawler.py` | 新增 | 爬虫基类 |
| `backend/proxy_crawler/hipflat_crawler.py` | 修改 | 继承 base_crawler |
| `backend/proxy_crawler/storage.py` | 新增 | 去重+增量逻辑 |
| `backend/cron_crawl.py` | 新增 | 定时爬虫入口 |
| `backend/app/i18n/` | 新增 | 后端国际化 |
| `frontend-react/src/i18n.jsx` | 填充 | 完整翻译键值对 |
| `backend/app/services/llm_analysis_service.py` | 新增 | LLM 总结 |
| `backend/app/services/price_prediction.py` | 新增 | 价格预测 |
| `backend/requirements.prod.txt` | 更新 | 添加 scikit-learn |
| `.github/workflows/` | 新增 | CI/CD 配置 |
