#!/bin/bash
# 清迈房产比价平台 — 一键部署脚本
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ─── Validate ─────────────────────────────────
command -v docker >/dev/null 2>&1 || err "Docker 未安装"
command -v node >/dev/null 2>&1 || err "Node.js 未安装"

[ -f .env ] || err ".env 文件不存在！请创建并填入 SECRET_KEY"

# ─── Build Frontend ───────────────────────────
log "构建前端..."
cd frontend
npm ci
npx vite build
log "前端构建完成"

# ─── Build & Deploy ───────────────────────────
cd ..
log "启动 Docker 服务..."
docker compose -f docker-compose.prod.yml up -d --build

log "等待服务就绪..."
sleep 5

# ─── Run DB Migration ─────────────────────────
log "执行数据库迁移..."
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# ─── Inject Seed Data (first time) ────────────
log "注入种子数据..."
docker compose -f docker-compose.prod.yml exec -T backend python seed_data.py

log "部署完成！"
echo ""
echo "  🌐 前端:   https://your-domain.com"
echo "  📡 API:    https://your-domain.com/api/v1"
echo "  📖 文档:   https://your-domain.com/docs"
echo ""
echo "首次部署后请:"
echo "  1. 替换 your-domain.com 为实际域名"
echo "  2. 配置 SSL 证书到 docker/ssl/"
echo "  3. 修改 .env 中的 SECRET_KEY 和 DB_PASSWORD"
