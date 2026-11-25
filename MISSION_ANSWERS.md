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
<DÁN OUTPUT /health, /ready, /ask>
```

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image:
2. Working directory:
3. Tại sao COPY requirements.txt trước:
4. CMD vs ENTRYPOINT:

### Exercise 2.2: Build và run