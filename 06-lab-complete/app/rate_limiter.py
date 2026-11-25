"""
Rate limiting (tiêu chí 7) — sliding window 60 giây, state lưu trong Redis.

Mỗi API key có một sorted set trong Redis:  ratelimit:<hash của key>
  • member = id duy nhất của request, score = thời điểm (giây)
Mỗi request:
  1. ZREMRANGEBYSCORE: xoá các request cũ hơn 60 giây
  2. ZCARD: đếm số request còn lại trong cửa sổ
  3. Vượt RATE_LIMIT_PER_MINUTE → HTTP 429 + header Retry-After
  4. Chưa vượt → ZADD request hiện tại + EXPIRE để Redis tự dọn key
Vì state nằm trong Redis nên mọi worker / instance dùng chung và vẫn còn sau khi restart agent.
"""
import hashlib
import time
import uuid

import redis
from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

WINDOW_SECONDS = 60


def check_rate_limit(key: str) -> None:
    # Không lưu API key thật trong Redis — chỉ lưu mã băm
    bucket = "ratelimit:" + hashlib.sha256(key.encode()).hexdigest()[:16]
    now = time.time()
    limit = settings.rate_limit_per_minute

    try:
        pipe = r.pipeline()
        pipe.zremrangebyscore(bucket, 0, now - WINDOW_SECONDS)
        pipe.zcard(bucket)
        _, count = pipe.execute()

        if count >= limit:
            oldest = r.zrange(bucket, 0, 0, withscores=True)
            retry_after = WINDOW_SECONDS
            if oldest:
                retry_after = max(1, int(oldest[0][1] + WINDOW_SECONDS - now) + 1)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limit} requests / {WINDOW_SECONDS}s",
                headers={"Retry-After": str(retry_after)},
            )

        pipe = r.pipeline()
        pipe.zadd(bucket, {f"{now}-{uuid.uuid4().hex[:8]}": now})
        pipe.expire(bucket, WINDOW_SECONDS + 5)
        pipe.execute()
    except redis.RedisError:
        # Không đếm được → từ chối an toàn (fail closed), không để lọt request không giới hạn
        raise HTTPException(status_code=503, detail="Rate limiter unavailable")
