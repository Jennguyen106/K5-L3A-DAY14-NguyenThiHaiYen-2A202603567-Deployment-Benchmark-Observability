"""
Cost guard (tiêu chí 8).

  • Cộng dồn chi phí LLM (tính theo token) vào Redis, theo từng ngày (UTC)
      key: cost:<YYYY-MM-DD>   — INCRBYFLOAT để cộng, EXPIRE để tự xoá sau 2 ngày
  • Tổng chi phí trong ngày >= DAILY_BUDGET_USD → HTTP 402 Payment Required
"""
from datetime import datetime, timezone

import redis
from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

# Giá USD / 1K tokens (tham khảo gpt-4o-mini)
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def _today_key() -> str:
    return "cost:" + datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_spent_today() -> float:
    return float(r.get(_today_key()) or 0.0)


def check_budget() -> None:
    """Gọi TRƯỚC khi gọi LLM. Hết budget → raise HTTPException(status_code=402)."""
    try:
        spent = get_spent_today()
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Cost guard unavailable")
    if spent >= settings.daily_budget_usd:
        raise HTTPException(
            status_code=402,
            detail=f"Daily budget exceeded: spent ${spent:.6f} / ${settings.daily_budget_usd}",
        )


def record_cost(input_tokens: int, output_tokens: int) -> float:
    """Gọi SAU khi gọi LLM. Cộng chi phí của request vào tổng, trả về chi phí request."""
    cost = input_tokens / 1000 * PRICE_INPUT_PER_1K + output_tokens / 1000 * PRICE_OUTPUT_PER_1K
    try:
        key = _today_key()
        pipe = r.pipeline()
        pipe.incrbyfloat(key, cost)
        pipe.expire(key, 2 * 24 * 3600)
        pipe.execute()
    except redis.RedisError:
        pass  # câu trả lời đã có — không làm hỏng response chỉ vì không ghi được chi phí
    return cost
