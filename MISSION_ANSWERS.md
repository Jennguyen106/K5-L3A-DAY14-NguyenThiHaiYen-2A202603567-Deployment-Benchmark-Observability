# Day 14 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found (`01-localhost-vs-production/develop/app.py`)
1. **Hardcode secret** (dòng 17–18): `OPENAI_API_KEY` và `DATABASE_URL` có mật khẩu viết thẳng trong code → push lên GitHub là lộ.
2. **In secret ra log** (dòng 34): `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` → ai đọc log cũng thấy key.
3. **Log bằng `print()`** (dòng 33, 38, 48): không có thời gian, level, không phải JSON → khó lọc, tìm kiếm.
4. **Config cứng** (dòng 21–22): `DEBUG = True`, `MAX_TOKENS = 500` không đổi được theo môi trường.
5. **Không có health check**: thiếu `/health`, `/ready` → platform không biết app chết để restart.
6. **Host `localhost` cứng** (dòng 51): chỉ nhận kết nối trong máy, container/cloud không truy cập được.
7. **Port 8000 cứng** (dòng 52): không đọc biến `PORT` mà Railway/Render cấp.
8. **`reload=True`** (dòng 53): chế độ debug, tốn tài nguyên, không dùng cho production.
9. **Không xử lý SIGTERM**: tắt đột ngột, request đang chạy bị cắt ngang.

### Exercise 1.2: Kết quả chạy bản develop
Lệnh: `curl -X POST "http://localhost:8000/ask?question=Hello"`

Response:
```
{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

Log server:
```
INFO:     Will watch for changes in these directories: [...]
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
[DEBUG] Got question: Hello
[DEBUG] Using key: sk-hardcoded-fake-key-never-do-this
[DEBUG] Response: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.
INFO:     127.0.0.1:44504 - "POST /ask?question=Hello HTTP/1.1" 200 OK
```

Nhận xét: agent chạy được nhưng chưa production-ready. Log cho thấy `reload` đang bật,
chạy trên `localhost:8000` cố định, log bằng `print()` và **in thẳng API key ra log**.

### Exercise 1.3: Comparison table
| Feature | Develop | Production | Tại sao quan trọng? |
|---------|---------|------------|---------------------|
| Config | Hardcode trong code | Đọc từ biến môi trường (`config.py`) | Đổi cấu hình theo môi trường không cần sửa code |
| Secret | Viết thẳng + in ra log | Lấy từ env, không log secret | Tránh lộ key khi push GitHub hoặc khi người khác đọc log |
| Health check | Không có | `GET /health` (liveness) + `GET /ready` (readiness) | Platform biết app còn sống / sẵn sàng để restart hoặc chuyển traffic |
| Logging | `print()` | JSON có cấu trúc | Máy đọc, lọc, tìm kiếm được; đưa vào hệ thống giám sát |
| Shutdown | Đột ngột | Bắt SIGTERM, uvicorn xử lý xong request rồi tắt | Không cắt ngang người dùng khi deploy/scale |
| Host/Port | `localhost:8000` cố định | `0.0.0.0` + `PORT` từ env | Chạy được trong container và trên cloud |

Kết quả chạy bản production:
```
Kết quả test bản production:
```
$ curl http://localhost:8000/health
{"status":"ok","uptime_seconds":147.4,"version":"1.0.0","environment":"development","timestamp":"2026-11-25T09:23:44.781998+00:00"}

$ curl http://localhost:8000/ready
{"ready":true}

$ curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"Hello"}'
{"question":"Hello","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","model":"gpt-4o-mini"}
```
Log khởi động: `WARNING:root:OPENAI_API_KEY not set — using mock LLM` ... `Uvicorn running on http://0.0.0.0:8000`
```

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image:  python:3.11

2. Working directory:/app : mọi lệnh sau đều chạy trong thư mục này bên trong container
3. Tại sao COPY requirements.txt trước: Tận dụng layer cache. Docker build từng lớp và lưu lại. Nếu chỉ sửa code mà không đổi thư viện, Docker dùng lại lớp đã cài thư viện, không cài lại → build nhanh hơn nhiều. Nếu COPY . . trước thì sửa 1 dòng code cũng phải cài lại toàn bộ thư viện
4. CMD vs ENTRYPOINT:CMD = lệnh mặc định, bị thay thế nếu docker run truyền lệnh khác. ENTRYPOINT = lệnh cố định, tham số của docker run chỉ được nối thêm vào sau. File này dùng CMD ["python", "app.py"] 

### Exercise 2.2: Build và run
```
$ docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
$ docker run --rm -p 8000:8000 my-agent:develop

$ curl -X POST "http://localhost:8000/ask?question=What%20is%20Docker"
{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}

$ curl http://localhost:8000/health
{"status":"ok","uptime_seconds":20.4,"container":true}
```

### Exercise 2.3: Image size comparison
Đo bằng `docker images | grep my-agent`:

| Image | DISK USAGE | CONTENT SIZE |
|-------|-----------:|-------------:|
| my-agent:develop (python:3.11, single-stage) | 1.67 GB | 426 MB |
| my-agent:advanced (python:3.11-slim, multi-stage) | 240 MB | 57.4 MB |

- Develop: 1670 MB
- Production: 240 MB
- Difference: giảm ≈ 85.6% (theo DISK USAGE); ≈ 86.5% theo CONTENT SIZE

Multi-stage:
- Stage 1 (builder, dòng 16–29): python:3.11-slim + gcc, libpq-dev; `pip install --user` vào /root/.local.
- Stage 2 (runtime, dòng 36–72): bắt đầu lại từ python:3.11-slim sạch, chỉ copy /root/.local từ
  builder, copy code, tạo user non-root `appuser`, thêm HEALTHCHECK, chạy uvicorn 2 workers.
- Nhỏ hơn vì: base slim thay cho bản đầy đủ, và build tools (gcc...) ở stage 1 không đi vào image cuối.
### Exercise 2.4: Docker Compose stack
Lệnh: `docker compose -p k5-day14-docker up -d --build` (trong `02-docker/production/`, đã `touch .env.local`)

Services: `agent` (FastAPI, build từ Dockerfile multi-stage), `redis` (cache/session/rate limit),
`qdrant` (vector DB cho RAG), `nginx` (reverse proxy / load balancer, mở cổng 80).

```
Client ──:80──▶ Nginx ──▶ agent:8000 ──▶ redis:6379
                                  └────▶ qdrant:6333
        (cùng network nội bộ "internal")
```
Các service gọi nhau bằng tên service (Docker DNS), ví dụ Nginx `proxy_pass` tới `agent:8000`,
agent dùng `REDIS_URL=redis://redis:6379/0`. Chỉ Nginx mở cổng ra ngoài; agent không expose port.
`depends_on` + `condition: service_healthy` đảm bảo redis, qdrant sẵn sàng trước khi agent chạy.

Test qua Nginx:
```
$ curl http://localhost/health
{"status":"ok","uptime_seconds":48.6,"version":"2.0.0","timestamp":"2026-11-25T09:56:15.322454"}

$ curl -X POST http://localhost/ask -H "Content-Type: application/json" -d '{"question":"Explain microservices"}'
{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```
## Part 4: API Security

### Exercise 4.1: API Key authentication (`04-api-gateway/develop/app.py`)
Chạy: `AGENT_API_KEY=secret-key-123 python app.py`

- **API key được check ở đâu?** Hàm `verify_api_key` (dòng 39–54), gắn vào `/ask` qua
  `Depends(verify_api_key)` (dòng 70). Key đọc từ biến môi trường `AGENT_API_KEY` (dòng 35),
  header tên `X-API-Key` (dòng 36).
- **Sai key thì sao?** Thiếu key → 401 "Missing API key"; sai key → 403 "Invalid API key".
  (Lưu ý: Part 6 yêu cầu cả thiếu lẫn sai đều trả 401.)
- **Rotate key thế nào?** Đổi giá trị biến môi trường `AGENT_API_KEY` rồi restart app, không
  sửa code. Thực tế nên hỗ trợ 2 key song song trong thời gian chuyển đổi để client kịp cập nhật.

Kết quả test:
```
$ curl -i -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"Hello"}'
HTTP/1.1 401 Unauthorized
content-type: application/json
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

$ curl -i -X POST http://localhost:8000/ask -H "X-API-Key: wrong-key" -H "Content-Type: application/json" -d '{"question":"Hello"}'
HTTP/1.1 403 Forbidden
content-type: application/json
{"detail":"Invalid API key."}

$ curl -i -X POST http://localhost:8000/ask -H "X-API-Key: secret-key-123" -H "Content-Type: application/json" -d '{"question":"Hello"}'
HTTP/1.1 200 OK
content-type: application/json
{"question":"Hello","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```
### Exercise 4.2: JWT authentication (`04-api-gateway/production`)
Lấy token tại `POST /auth/token` với tài khoản `student / demo123`:
```
$ curl -i -X POST http://localhost:8000/auth/token -H "Content-Type: application/json" -d '{"username":"student","password":"demo123"}'
HTTP/1.1 200 OK
{"access_token":"<TOKEN_ĐÃ_CHE>","token_type":"bearer","expires_in_minutes":60,...}

$ curl -i -X POST http://localhost:8000/ask -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"question":"Explain JWT"}'
HTTP/1.1 200 OK
x-content-type-options: nosniff
x-frame-options: DENY
{"question":"Explain JWT","answer":"...","usage":{"requests_remaining":9,"budget_remaining_usd":1.9e-05}}
```
JWT flow: đăng nhập 1 lần → server ký token (header.payload.signature, HS256) chứa
`sub`, `role`, `iat`, `exp` (hết hạn sau 60 phút) → các request sau gửi
`Authorization: Bearer <token>` → server kiểm chữ ký và hạn dùng, không cần tra mật khẩu lại.
Payload đọc được (base64) nhưng không sửa được vì sẽ sai chữ ký.

Nhận xét: field `budget_remaining_usd` thực chất trả về chi phí ĐÃ dùng
(`app.py` dòng 160 gán `usage.total_cost_usd`) → đặt tên sai, dễ gây hiểu nhầm.

### Exercise 4.3: Rate limiting
```
Request 1: 200
Request 2: 200
Request 3: 200
Request 4: 200
Request 5: 200
Request 6: 200
Request 7: 200
Request 8: 200
Request 9: 200
Request 10: 200
Request 11: 429
Request 12: 429
Request 13: 429
Request 14: 429
Request 15: 429

$ curl -i -X POST http://localhost:8000/ask -H "Authorization: Bearer $TOKEN" ... -d '{"question":"one more"}'
HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
x-ratelimit-reset: 1795601860
retry-after: 36
```
- **Algorithm:** Sliding window. Mỗi user có một `deque` lưu timestamp các request; mỗi lần gọi
  xoá timestamp cũ hơn 60s, đếm số còn lại, vượt limit → 429 kèm `Retry-After` (`rate_limiter.py` dòng 36–65).
- **Limit:** user 10 req/phút, admin 100 req/phút (`rate_limiter.py` dòng 86–87).
- **Bypass cho admin:** không bỏ hẳn giới hạn mà dùng limiter riêng cao hơn theo role trong JWT:
  `rate_limiter_admin if role == "admin" else rate_limiter_user` (`app.py` dòng 141). Tài khoản admin: `teacher`.
- **Hạn chế:** state nằm trong RAM của process → restart là mất, nhiều instance thì đếm riêng.
  Production cần lưu trong Redis (Part 6).

### Exercise 4.4: Cost guard implementation
- Trước khi gọi LLM: `check_budget(user_id)`: chi phí trong ngày của user ≥ $1 → **402 Payment Required**;
  tổng toàn hệ thống ≥ $10/ngày → **503**; ≥ 80% budget → ghi cảnh báo.
- Sau khi gọi LLM: `record_usage()` tính
  `cost = input_tokens/1000 × giá_input + output_tokens/1000 × giá_output` và cộng dồn.
- Reset theo ngày: bản ghi gắn với ngày hiện tại, sang ngày
## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks (`05-scaling-reliability/develop/app.py`)
- `GET /health` (liveness, dòng 104–145): trả 200 khi process còn chạy, kèm uptime, version,
  và tự kiểm tra bộ nhớ bằng psutil: `ok`, hoặc `degraded` nếu RAM > 90%.
  Platform gọi định kỳ, lỗi/timeout → restart container.
- `GET /ready` (readiness, dòng 147–168): trả 503 khi `_is_ready = False` (đang khởi động hoặc
  đang tắt), 200 khi sẵn sàng. Load balancer dùng để quyết định có chuyển traffic vào hay không.
- **Liveness vs Readiness:** liveness hỏi "còn sống không?" (sai → restart);
  readiness hỏi "nhận traffic được chưa?" (sai → tạm ngừng chuyển traffic, KHÔNG restart).
  Ví dụ: Redis mất kết nối → `/health` vẫn 200 (restart không giải quyết được),
  `/ready` trả 503 (đừng gửi request vào).

Kết quả test:
```
$ curl http://localhost:8000/health
{"status":"ok","uptime_seconds":13.9,"version":"1.0.0","environment":"development","timestamp":"2026-11-25T10:20:48.553508+00:00","checks":{"memory":{"status":"ok","used_percent":14.0}}}

$ curl http://localhost:8000/ready
{"ready":true,"in_flight_requests":1}
```
Ghi chú: `in_flight_requests = 1` là chính request `/ready` đang được xử lý
(middleware `track_requests` tăng bộ đếm trước khi gọi endpoint).

### Exercise 5.2: Graceful shutdown
- Middleware `track_requests` (dòng 72–81) đếm số request đang xử lý (`_in_flight_requests`).
- Khi nhận tín hiệu tắt, uvicorn gọi phần shutdown của `lifespan` (dòng 52–66):
  1. Đặt `_is_ready = False` → ngừng nhận request mới (`/ready` trả 503).
  2. Chờ request đang chạy hoàn thành, tối đa 30 giây.
  3. Ghi log và thoát.
- `uvicorn.run(..., timeout_graceful_shutdown=30)`; `handle_sigterm` chỉ ghi log,
  uvicorn tự xử lý việc tắt.

Log khi nhấn Ctrl+C:
```
2026-11-25 10:20:34,672 INFO Agent starting up...
2026-11-25 10:20:34,672 INFO Loading model and checking dependencies...
2026-11-25 10:20:34,873 INFO ✅ Agent is ready!
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:55108 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:55110 - "GET /ready HTTP/1.1" 200 OK
^CINFO:     Shutting down
INFO:     Waiting for application shutdown.
2026-11-25 10:21:07,201 INFO 🔄 Graceful shutdown initiated...
2026-11-25 10:21:07,202 INFO ✅ Shutdown complete
INFO:     Application shutdown complete.
INFO:     Finished server process [5812]
2026-11-25 10:21:07,202 INFO Received signal 2 — uvicorn will handle graceful shutdown
```
Nhận xét:
- Signal 2 = SIGINT (Ctrl+C). Trên cloud, platform gửi SIGTERM (signal 15) khi tắt container;
  uvicorn xử lý cả hai theo cùng cách graceful.
- Không có dòng "Waiting for ... in-flight requests" vì lúc tắt không còn request nào đang chạy,
  nên shutdown hoàn tất ngay (~1 ms). Nếu đang có request, app chờ tối đa 30s cho xong.

### Exercise 5.3: Stateless design (`05-scaling-reliability/production/app.py`)
- Session và conversation history lưu trong Redis: `save_session()` dùng
  `SETEX session:<id>` với TTL 3600s, `load_session()` dùng `GET`.
  Không lưu trong RAM của từng instance.
- Lý do: khi scale nhiều instance, mỗi instance có bộ nhớ riêng. Request 1 vào instance A,
  request 2 vào instance B → B không thấy history nếu lưu trong RAM.
  Lưu ở Redis dùng chung thì instance nào cũng đọc được.
- Mỗi response có `served_by` (INSTANCE_ID) để chứng minh nhiều instance cùng phục vụ một session.

### Exercise 5.4: Load balancing
Lệnh (trong `05-scaling-reliability/production/`, đã `touch .env.local`):
`docker compose -p k5-day14-scaling up -d --build --scale agent=3`

- Nginx (`nginx.conf`): `upstream agent_cluster { server agent:8000; }`. Docker DNS trả về
  cả 3 container agent nên request được chia vòng tròn (round-robin).
- `proxy_next_upstream error timeout http_503` + `proxy_next_upstream_tries 3`:
  1 instance lỗi/503 thì Nginx tự chuyển sang instance khác.
- Header `X-Served-By` cho biết instance nào đã xử lý. Stack mở cổng 8080, endpoint `POST /chat`.

```
$ docker compose -p k5-day14-scaling ps
NAME                       IMAGE                    SERVICE   STATUS                   PORTS
k5-day14-scaling-agent-1   k5-day14-scaling-agent   agent     Up 2 minutes (healthy)   8000/tcp
k5-day14-scaling-agent-2   k5-day14-scaling-agent   agent     Up 2 minutes (healthy)   8000/tcp
k5-day14-scaling-agent-3   k5-day14-scaling-agent   agent     Up 2 minutes (healthy)   8000/tcp
k5-day14-scaling-nginx-1   nginx:alpine             nginx     Up 2 minutes             0.0.0.0:8080->80/tcp
k5-day14-scaling-redis-1   redis:7-alpine           redis     Up 2 minutes (healthy)   6379/tcp

$ docker compose -p k5-day14-scaling logs agent | tail -20
agent-1  | ✅ Connected to Redis
agent-1  | INFO:app:Starting instance instance-fee1fa
agent-1  | INFO:app:Storage: Redis ✅
agent-1  | INFO:     Uvicorn running on http://0.0.0.0:8000
agent-1  | INFO:     127.0.0.1:53614 - "GET /health HTTP/1.1" 200 OK
agent-1  | INFO:     172.18.0.6:55114 - "POST /chat HTTP/1.1" 200 OK
agent-1  | INFO:     172.18.0.6:55114 - "POST /chat HTTP/1.1" 200 OK
agent-1  | INFO:     127.0.0.1:40188 - "GET /health HTTP/1.1" 200 OK
...
```


### Exercise 5.5: Test stateless
```
============================================================
Stateless Scaling Demo
============================================================
Session ID: b096d192-e05d-4e62-98df-5fdf9f9ae7a4

Request 1: [instance-fee1fa]  Q: What is Docker?
Request 2: [instance-167db8]  Q: Why do we need containers?
Request 3: [instance-83f0db]  Q: What is Kubernetes?
Request 4: [instance-fee1fa]  Q: How does load balancing work?
Request 5: [instance-167db8]  Q: What is Redis used for?
------------------------------------------------------------
Total requests: 5
Instances used: {'instance-83f0db', 'instance-fee1fa', 'instance-167db8'}
✅ All requests served despite different instances!

--- Conversation History ---
Total messages: 10
✅ Session history preserved across all instances via Redis!
```
Giải thích: 5 câu trong cùng một session được phục vụ bởi nhiều instance khác nhau (`served_by`),
nhưng history vẫn đủ toàn bộ tin nhắn vì được lưu ở Redis dùng chung → agent stateless,
scale ngang được mà không mất hội thoại. Script không tắt instance nào; nếu một instance chết,
Nginx chuyển request sang instance còn lại và history vẫn còn trong Redis.