# 🏠 清迈全城房屋比价平台

> **Chiang Mai Property Comparison Platform** — 聚合多家泰国房产网站的出租/出售房源，一站式比价搜索。

将 HipFlat、FazWaz、DDProperty 等泰国主流房产平台的清迈房源聚合到一个界面，支持**比价、搜索、地图浏览、收藏对比**。

---

## ✨ 功能

- **房源聚合** — 从多个泰国房产网站自动爬取最新房源
- **比价浏览** — 列表/地图双模式浏览，一键对比多套房源
- **智能搜索** — 按区域、价格、户型、面积等多维度筛选
- **房源详情** — 图片轮播、价格曲线、配套设施、地图定位
- **收藏对比** — 注册后可收藏房源、保存对比组合
- **PWA 支持** — 可安装到手机桌面，原生应用体验
- **移动优先** — 基于 antd-mobile 的移动端适配设计

## 🏗 技术栈

| 层 | 技术 |
|---|---|
| **后端** | FastAPI + SQLAlchemy 2.0 (async) + Pydantic |
| **前端** | React 18 + Vite + antd-mobile + Leaflet |
| **数据库** | SQLite（开发）/ PostgreSQL（生产） |
| **爬虫** | ScrapingAnt 代理 API + 自定义 HTML 解析器 |
| **部署** | Railway（Docker 多阶段构建） |
| **认证** | JWT + PBKDF2 |

## 🗺 项目结构

```
chiangmai-property/
├── backend/                     # FastAPI 后端
│   ├── app/                     # 应用核心
│   │   ├── api/v1/              # API 路由（6 个模块）
│   │   ├── core/                # 配置 + 数据库连接
│   │   ├── models/              # 5 个数据模型
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   └── services/            # 业务逻辑层
│   ├── crawlers/                # Scrapy 爬虫（备用）
│   ├── proxy_crawler/           # ✅ 正在使用的代理爬虫
│   │   ├── proxy_adapter.py     # ScrapingAnt 适配器
│   │   └── parsers.py           # HTML 解析器
│   ├── run_hipflat_list.py      # ✅ 主爬虫脚本
│   └── main.py                  # 应用入口
├── frontend-react/                 # React 18 前端
  ├── src/
  │   ├── pages/                 # 9 个页面组件
  │   ├── stores/                # Zustand 状态管理
  │   ├── components/            # 通用组件 (PropertyCard)
  │   ├── api/                   # Axios API 客户端
  │   └── styles/                # 全局样式
  └── vite.config.js
├── Dockerfile                   # Railway 多阶段构建
└── railway.json                 # 部署配置
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+
- 无需安装浏览器（爬虫使用代理 API）

### 1. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.prod.txt

# 启动开发服务器（自动创建数据库表）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 前端启动

```bash
cd frontend-react

npm install

# 启动开发服务器（自动代理 /api 到后端）
npx vite --host 0.0.0.0 --port 5173
```

Vite 已配置 `/api` 代理到 `localhost:8000`，前后端无需手动跨域配置。

### 3. 爬取房源数据

```bash
cd backend

# 设置 ScrapingAnt API key
export SCRAPINGANT_API_KEY=your_key_here

# 爬取 HipFlat 清迈房源（~40秒，产出约150条）
python run_hipflat_list.py
```

需要免费[注册 ScrapingAnt](https://scrapingant.com) 获取 API key（每月 10,000 次免费请求）。

### 4. 验证

```bash
# 健康检查
curl http://localhost:8000/health

# 获取房源列表
curl http://localhost:8000/api/v1/properties?page_size=5

# 前端访问
open http://localhost:5173
```

## 🧪 当前数据源状态

| 来源 | 状态 | 说明 |
|---|---|---|
| **HipFlat** | ✅ **稳定运行** | 148 条房源，100% 真实图片，99% 含价格 |
| **FazWaz** | ⚠️ 部分工作 | 列表页可解析，但详情页价格缺失严重 |
| **DDProperty** | ❌ Cloudflare 封锁 | 代理 API 无法绕过，暂不可用 |

## 📡 API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/health` | 健康检查 |
| `GET` | `/api/v1/properties` | 房源列表（分页+筛选） |
| `GET` | `/api/v1/properties/{id}` | 房源详情 |
| `GET` | `/api/v1/properties/compare?ids=1,2` | 多房源对比 |
| `GET` | `/api/v1/districts` | 区域统计 |
| `GET` | `/api/v1/markers` | 地图标记 |
| `POST` | `/api/v1/auth/login` | 用户登录 |
| `POST` | `/api/v1/auth/register` | 用户注册 |
| `GET` | `/api/v1/favorites` | 收藏列表 |
| `DELETE` | `/api/v1/favorites/{id}` | 取消收藏 |

### 房源列表筛选参数

```
?page=1&page_size=20&source=hipflat&district=Mueang
&price_type=RENT&min_price=500&max_price=5000
&bedrooms=2&sort=price_asc
```

## 🚢 生产部署

平台部署在 [Railway](https://railway.app)，使用 Docker 多阶段构建：

```bash
# 1. 构建前端
cd frontend && npx vite build

# 2. 构建 Docker 镜像
docker build -t cmproperty .

# 3. 推送至 GitHub（Railway 自动部署）
git push origin master
```

**环境变量（Railway）：**

| 变量 | 来源 | 说明 |
|---|---|---|
| `PORT` | Railway 自动 | 动态端口 |
| `DATABASE_URL` | PostgreSQL 插件 | `postgresql+asyncpg://...` |
| `SECRET_KEY` | 手动设置 | 生成: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ENV` | 手动设置 | 设为 `production` |

## 🔄 重新部署流程

```bash
# 1. 爬取最新数据
cd backend && python run_hipflat_list.py

# 2. 构建前端
cd ../frontend && npx vite build

# 3. 提交并推送
git add -A && git commit -m "crawl: update HipFlat data"
git push origin master

# 4. Railway Dashboard → Redeploy
# 5. 部署后在 Railway Shell 执行:
#    cd backend && python run_hipflat_list.py
```

## 🐛 常见问题

**Q: 前端页面显示空白或假图片？**
A: 确保 Vite 开发服务器已配置 `/api` 代理。运行 `curl http://localhost:5173/api/v1/properties?page_size=1` 应返回 JSON 而非 HTML。

**Q: 爬虫报错 409 Conflict？**
A: ScrapingAnt 免费版有速率限制，两次请求间隔至少 2 秒。脚本会自动重试。

**Q: 数据库文件在哪里？**
A: `backend/cmproperty.db`。前端和后端使用同一个数据库文件。

**Q: 如何查看数据库中有多少条数据？**
```bash
python3 -c "
from sqlalchemy import create_engine, text
engine = create_engine('sqlite:///backend/cmproperty.db')
with engine.connect() as c:
    r = c.execute(text('SELECT source, COUNT(*) FROM properties GROUP BY source'))
    for row in r: print(f'{row[0]}: {row[1]}条')
"
```

## 📄 许可证

MIT
