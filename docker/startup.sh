#!/bin/bash
# chiangmai-property startup — unified entry point
set -e

echo "=== Chiang Mai Property Server ==="
echo "Starting on port ${PORT:-8000}"

# Check frontend dist
if [ -d "/app/frontend-react/dist" ]; then
    echo "✅ Frontend dist found at /app/frontend-react/dist"
else
    echo "⚠️  Frontend dist not found"
fi

# Run migrations/seed
cd /app/backend
echo "Running startup (DB init)..."
python startup.py 2>/dev/null || echo "No pending startup tasks"

# Start uvicorn
echo "Starting uvicorn on 0.0.0.0:${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
