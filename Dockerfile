# ===== Stage 1: Build Frontend =====
FROM node:20-alpine AS frontend-builder

WORKDIR /app
COPY frontend-react/package.json frontend-react/package-lock.json* ./
RUN npm install
COPY frontend-react/ ./
RUN npm run build

# ===== Stage 2: Build Backend =====
FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/dist/ ./frontend-react/dist/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python3 -c "import urllib.request, os; p=os.environ.get('PORT','8000'); urllib.request.urlopen(f'http://localhost:{p}/health')" || exit 1

# Start
CMD cd backend && (ls -la ../frontend-react/dist/ 2>/dev/null || echo "dist NOT FOUND at ../frontend-react/dist/"; ls -la /app/frontend-react/dist/ 2>/dev/null || echo "dist NOT FOUND at /app/frontend-react/dist/") && python startup.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT
