# Deployment Information

## Public URL
https://agent-production-d18ad049.up.railway.app

## Platform
Railway: deploy thư mục `06-lab-complete/` (build bằng Dockerfile, cấu hình `railway.toml`).
Project gồm 2 service: `agent` (Docker image Part 6) và `Redis-ia08` (Railway Redis).

## Test Commands
```bash
BASE="https://agent-production-d18ad049.up.railway.app"
# AGENT_API_KEY = key đặt trên Railway (không ghi ở đây)

curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"     # 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"      # 200
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'   # 401
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'   # 200
```

Kết quả (26/11/2026):
```
200
200
401
200
```

## Environment Variables Set (service `agent`)
- `AGENT_API_KEY`: secret, sinh bằng `secrets.token_hex(16)`, chỉ lưu trên Railway
- `REDIS_URL`: tham chiếu `${{Redis-ia08.REDIS_URL}}` (private network của Railway)
- `ENVIRONMENT=production`
- `RATE_LIMIT_PER_MINUTE=10`
- `DAILY_BUDGET_USD=1.0`
- `PORT`: Railway tự cấp (8080); Dockerfile dùng `${PORT:-8000}`

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)