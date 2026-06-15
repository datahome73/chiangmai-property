# Chiangmai Property - 调研报告

## 1. 项目概览

名称: chiangmai-property
描述: 清迈全城房屋出租出售比价平台
主语言: Python
创建: 2026-05-29 (17天前)
最后推送: 2026-06-05 (10天前)
默认分支: master
Star/Fork/Issues: 0/0/0
License: MIT
大小: 321KB

技术栈:
- 后端: FastAPI + SQLAlchemy 2.0(asyncio) + Pydantic v2
- 前端: React 18 + Vite 6 + antd-mobile 5 + Leaflet
- 数据库: SQLite(dev) / PostgreSQL(prod) + Redis
- 爬虫: ScrapingAnt + lxml/parsel
- 部署: Railway (Docker 多阶段构建)
- 认证: JWT + PBKDF2
- 状态管理: Zustand, API客户端: Axios, 迁移: Alembic
## 2. 目录结构

chiangmai-property/
+-- .env.railway / .gitignore
+-- Dockerfile / Makefile / README.md
+-- deploy.sh / start-dev.sh
+-- docker-compose.yml / docker-compose.prod.yml
+-- railway.json / docker/
|
+-- backend/ (FastAPI)
|   +-- requirements*.txt (dev/prod/crawler 三份)
|   +-- run_hipflat_list.py (主爬虫脚本 HipFlat)
|   +-- proxy_crawler/
|   |   +-- proxy_adapter.py (ScrapingAnt)
|   |   +-- parsers.py (HTML解析)
|   +-- crawlers/ (Scrapy 备用爬虫)
|   +-- app/
|   |   +-- main.py / core/ (配置+数据库)
|   |   +-- api/v1/ (6个路由模块)
|   |   +-- models/property.py (5个数据模型)
|   |   +-- schemas/ (auth/favorite/property)
|   |   +-- services/ (auth/favorite/property/AI分析)
|   +-- alembic.ini + alembic/ (数据库迁移)
|   +-- seed_data.py / startup.py / verify_all.py
|   +-- test_crawler.py / test_proxy_crawl.py
|
+-- frontend-react/ (React 18)
    +-- package.json (v2.0.0)
    +-- vite.config.js / index.html
    +-- public/ (PWA manifest + Service Worker)
    +-- src/
        +-- main.jsx / App.jsx / i18n.jsx / registerSW.js
        +-- api/ / components/ / pages/ (9 pages)
        +-- router/ / stores/ / styles/
## 3. 关键配置分析

后端依赖: fastapi==0.109.0, sqlalchemy[asyncio]==2.0.25, asyncpg==0.29.0, redis[hiredis]==5.0.1, scrapy==2.11.0, playwright==1.40.0, lxml==4.9.4, httpx, beautifulsoup4, python-jose, passlib[bcrypt], geoalchemy2

前端依赖: react ^18.3.1, react-router-dom ^6.28.0, zustand ^5.0.0, axios ^1.7.7, antd-mobile ^5.37.1, leaflet ^1.9.4

部署: Dockerfile 多阶段构建 (node:20-alpine 构建前端 -> python:3.11-slim 运行后端), docker-compose 含 Redis+PostgreSQL, Railway 平台部署

## 4. 已完成功能

- 后端架构: FastAPI 分层 (api/core/models/schemas/services)
- 数据模型: 5个模型 (Property + 关联表)
- 认证系统: JWT + PBKDF2 (register/login)
- 收藏系统: CRUD API
- HipFlat爬虫: proxy_crawler模块 + run_hipflat_list.py
- Scrapy备用爬虫: crawlers/目录
- 数据库迁移: Alembic
- AI分析服务: ai_analysis_service.py 存在, 功能待确认
- 前端骨架: React 18 + Vite 6 + 9页面
- PWA: Service Worker + manifest.json
- 地图: Leaflet
- 国际化: i18n.jsx骨架存在, 翻译待填充
- 部署配置: Docker + Railway + Makefile + deploy.sh

## 5. 待办缺口分析

### 5.1 数据源单薄
- ❌ **仅 HipFlat 一个数据源** — 爬虫只抓取 HipFlat.com，缺少 DDProperty、LivingStock、Renthub、Kaidee、BaanFinder 等主流清迈房屋平台
- ❌ 爬虫数据更新频率无 cronjob/定时任务配置
- ❌ 无增量爬取机制，每次都是全量运行

### 5.2 功能缺失
- ❌ **无搜索/筛选功能** — 前端没有搜索栏、筛选器（按价格/区域/户型/租赁方式等）
- ❌ **无用户系统扩展** — 仅有注册登录，无个人中心、发布房源、房东认证
- ❌ **无地图交互** — 后端有 geoalchemy2 但前端 Leaflet 集成可能不完整
- ❌ **无联系房东/咨询功能** — 没有站内信或联系方式展示
- ❌ **无数据统计/看板** — 无房源浏览量、收藏统计、价格趋势分析
- ❌ **无分类浏览** — 没有按区域（Nimman、Old City、Suthep 等）分类浏览

### 5.3 测试缺失
- ❌ **无单元测试** — 无 pytest 测试文件
- ❌ **无集成测试** — 无 API 端点测试
- ❌ **无 E2E 测试**

### 5.4 工程化缺失
- ❌ **无 CI/CD** — 无 GitHub Actions 配置
- ❌ i18n 翻译未填充（仅骨架）

### 5.5 运营缺口
- ❌ 无房源审核机制
- ❌ 无数据质量校验（爬虫抓取缺字段的兜底）
- ❌ 无房源详情页联系转化追踪

## 6. 总结与建议

### 当前评估
项目处于 **MVP 早期阶段**（开发约 5 天活跃，已停滞 10 天）。架构设计合理，技术选型现代，数据模型完整，但功能覆盖度不足。

### 优先级建议
1. 🔴 **高** — 增加更多数据源（DDProperty、LivingStock 等），丰富房源量
2. 🔴 **高** — 实现搜索/筛选功能（核心用户体验）
3. 🟡 **中** — 完善地图交互与区域分类
4. 🟡 **中** — 配置定时爬虫 cronjob 保持数据新鲜
5. 🟢 **低** — 补单元测试、CI/CD 流水线
6. 🟢 **低** — 联系房东功能、用户运营功能

### 技术栈亮点
- 前后端分离架构 ✅
- 异步 FastAPI + async SQLAlchemy ✅
- PWA 离线支持 ✅
- 多阶段 Docker 构建 ✅
- A lem bic 数据库迁移 ✅
