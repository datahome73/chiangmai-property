# 清迈房产比价平台 — 一键启动/管理

.PHONY: dev dev-build dev-down db-migrate db-revision shell logs clean

# ─── Development ──────────────────────────────────────────

dev:
	docker compose up -d

dev-build:
	docker compose up -d --build

dev-down:
	docker compose down

dev-logs:
	docker compose logs -f

# ─── Database ─────────────────────────────────────────────

db-revision:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

db-migrate:
	docker compose exec backend alembic upgrade head

db-rollback:
	docker compose exec backend alembic downgrade -1

# ─── Shell ────────────────────────────────────────────────

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec db psql -U cmproperty -d cmproperty

# ─── Cleanup ──────────────────────────────────────────────

clean:
	docker compose down -v
	docker system prune -f
