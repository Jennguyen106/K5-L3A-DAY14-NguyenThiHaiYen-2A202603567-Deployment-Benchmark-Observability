"""
Production AI Agent — Part 6 Final Project

Chạy:   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Kiểm:   python check_production_ready.py
"""
import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import redis_healthy
from utils.mock_llm import ask as llm_ask


# ──────────────────────────────────────────────────────────
# Tiêu chí 10 — Structured logging: mỗi dòng log là 1 JSON object
# ──────────────────────────────────────────────────────────
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "lvl": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Các field thêm truyền qua extra={"fields": {...}}
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(JsonFormatter())
logger = logging.getLogger("agent")
logger.handlers = [_handler]
logger.setLevel(logging.INFO)
logger.propagate = False  # không để root logger in thêm một bản không phải JSON


def log_event(event: str, **fields) -> None:
    logger.info(event, extra={"fields": {"event": event, **fields}})


# ──────────────────────────────────────────────────────────
# Tiêu chí 11 — Graceful shutdown qua lifespan
#   Khi nhận SIGTERM, uvicorn ngừng nhận kết nối mới, chờ request đang chạy xong,
#   rồi chạy phần sau `yield` và thoát với exit code 0.
#   Không tự đăng ký signal handler → không chặn mất handler của uvicorn.
# ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log_event("startup", environment=settings.environment, port=settings.port,
              rate_limit_per_minute=settings.rate_limit_per_minute,
              daily_budget_usd=settings.daily_budget_usd)
    yield
    log_event("shutdown", detail="graceful shutdown — in-flight requests completed")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    log_event("request", method=request.method, path=request.url.path,
              status=response.status_code, ms=round((time.perf_counter() - start) * 1000, 1))
    return response


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    # Lỗi không lường trước: ghi log chi tiết ở server, trả thông báo chung cho client
    logger.error("unhandled_error", exc_info=exc,
                 extra={"fields": {"event": "unhandled_error", "path": request.url.path}})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[str] = None


# ──────────────────────────────────────────────────────────
# Tiêu chí 4 — Liveness: luôn 200 khi process còn chạy (không phụ thuộc Redis)
# ──────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment,
            "timestamp": datetime.now(timezone.utc).isoformat()}


# ──────────────────────────────────────────────────────────
# Tiêu chí 5 — Readiness: 200 khi Redis kết nối được, 503 khi không
# ──────────────────────────────────────────────────────────
@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Not ready: Redis unavailable")
    return {"ready": True}


def _estimate_tokens(text: str) -> int:
    """Ước lượng số token (~4 ký tự / token) — mock LLM không trả usage thật."""
    return max(1, len(text) // 4)


# ──────────────────────────────────────────────────────────
# /ask: auth (6) → rate limit (7) → budget (8) → LLM → ghi chi phí (8)
# ──────────────────────────────────────────────────────────
@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    check_budget()

    answer = llm_ask(body.question)

    cost = record_cost(_estimate_tokens(body.question), _estimate_tokens(answer))
    log_event("llm_call", question_length=len(body.question), cost_usd=round(cost, 8))
    return {"question": body.question, "answer": answer}
