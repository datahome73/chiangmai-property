#!/bin/bash
# 清迈房产比价平台 — 开发环境快速启动脚本
set -e

echo "🚀 启动清迈房产比价平台开发环境..."

# 1. 检查环境
echo "📋 检查环境..."
command -v docker >/dev/null 2>&1 || { echo "❌ 需要安装 Docker"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ 需要安装 Node.js"; exit 1; }

# 2. 启动 Docker 服务
echo "🐳 启动 Docker 服务 (PostgreSQL + Redis)..."
docker compose up -d db redis
echo "⏳ 等待数据库就绪..."
sleep 3

# 3. 数据库迁移
echo "🗄️ 执行数据库迁移..."
docker compose run --rm backend alembic upgrade head

# 4. 启动后端
echo "⚙️ 启动后端 API..."
docker compose up -d backend

# 5. 启动前端
echo "🎨 启动前端开发服务器..."
cd frontend && npm run dev &

echo ""
echo "✅ 开发环境启动完成！"
echo "   📡 后端 API:  http://localhost:8000"
echo "   🎨 前端:      http://localhost:5173"
echo "   🗄️  数据库:    localhost:5432"
echo ""
echo "按 Ctrl+C 停止所有服务"
