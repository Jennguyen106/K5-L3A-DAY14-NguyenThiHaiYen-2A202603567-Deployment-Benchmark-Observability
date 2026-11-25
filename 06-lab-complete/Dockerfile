# ============================================================
# Production Dockerfile — multi-stage build
#   Stage 1 (builder): cài dependencies vào /root/.local
#   Stage 2 (runtime): image slim sạch, chỉ copy thư viện đã cài + code,
#                      chạy bằng user non-root, có HEALTHCHECK
# ============================================================

# ── Stage 1: builder ─────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
# Copy requirements TRƯỚC code để tận dụng layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────
FROM python:3.11-slim AS runtime

# User non-root
RUN groupadd -r agent && useradd -r -g agent -d /home/agent -m agent

WORKDIR /app

# Chỉ copy thư viện đã cài từ builder (không mang theo pip cache, build tools)
COPY --from=builder --chown=agent:agent /root/.local /home/agent/.local
COPY --chown=agent:agent app/ ./app/
COPY --chown=agent:agent utils/ ./utils/

ENV PYTHONUSERBASE=/home/agent/.local \
    PATH=/home/agent/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

USER agent

EXPOSE 8000

# Docker tự gọi /health định kỳ; đọc PORT từ env
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8000') + '/health', timeout=3)" || exit 1

# exec → uvicorn là PID 1, nhận SIGTERM trực tiếp khi `docker stop`
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
