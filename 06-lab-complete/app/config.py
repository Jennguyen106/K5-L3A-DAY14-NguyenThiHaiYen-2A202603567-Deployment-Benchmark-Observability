"""
Config — 12-Factor: mọi cấu hình đọc từ biến môi trường.

Mỗi giá trị đọc bằng os.getenv(TÊN_BIẾN, giá_trị_mặc_định):
  • Có biến môi trường  → dùng giá trị đó (trên cloud, trong Docker, khi script chấm chạy)
  • Không có            → dùng giá trị mặc định an toàn cho máy local
Không có secret thật nào nằm trong code: AGENT_API_KEY mặc định là chuỗi rỗng.
"""
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", ""))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")))
    daily_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("DAILY_BUDGET_USD", "1.0")))


settings = Settings()
