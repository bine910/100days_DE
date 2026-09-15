# Week 7 — Day 2: Dockerfile — Tự Build Image

## 1. Docker Hub & Image Registry

- Image có sẵn (postgres:16, python:3.12) được build bởi maintainer và push lên **Docker Hub** (hub.docker.com).
- `docker run postgres:16` → Docker Engine pull image từ Docker Hub về máy → tạo container.
- Docker Hub giống npm registry cho Node.js.

```
Docker Hub (registry)          Máy local
┌──────────────┐    pull     ┌──────────────┐
│ postgres:16  │ ────────→   │ postgres:16  │ (image)
│ (Dockerfile) │             │     ↓        │
└──────────────┘             │  container   │ (chạy)
                             └──────────────┘
```

## 2. Dockerfile — Cấu trúc cơ bản

Dockerfile = công thức build image. Mỗi dòng = 1 layer.

```dockerfile
FROM python:3.12.3             # Base image
WORKDIR /app                   # Tạo & cd vào /app
COPY requirements.txt .        # Copy dependencies list
RUN pip install --no-cache-dir -r requirements.txt  # Cài dependencies
COPY ./src/ ./src/             # Copy source code
CMD ["python", "src/main.py"]  # Lệnh chạy khi container start
```

| Instruction | Ý nghĩa |
|-------------|---------|
| `FROM` | Base image để bắt đầu |
| `WORKDIR` | Thư mục làm việc trong container |
| `COPY` | Copy file từ host vào image |
| `RUN` | Chạy lệnh khi build (cài dependencies) |
| `CMD` | Lệnh mặc định khi container start |

## 3. Layer Caching — Tối ưu build time

Docker cache layer từ trên xuống. Layer không thay đổi → dùng cache, không build lại.

**Nguyên tắc:** đặt thứ **ít thay đổi** trước, thứ **hay thay đổi** sau.

```
Sửa code trong src/main.py:

Cách tốt (tách):                    Cách xấu (gộp):
COPY requirements.txt .   ← cache    COPY . .          ← THAY ĐỔI
RUN pip install ...        ← cache    RUN pip install    ← CHẠY LẠI (tốn 30-60s)
COPY src/ ./src/           ← BUILD    COPY src/ ...      ← CHẠY LẠI
```

## 4. Build Context

- `docker build .` → dấu `.` = build context = thư mục hiện tại.
- Path trong `COPY` tính từ build context, không phải từ root project.
- Dockerfile nằm trong `etl_app/` → `COPY ./src/ .` chứ không phải `COPY ./etl_app/src/ .`

## 5. .dockerignore

Ngăn file không cần thiết bị copy vào image:

```
.env
__pycache__
*.pyc
```

## 6. Secret — Không bao giờ copy .env vào image

- Image có thể bị share (push Docker Hub, đồng nghiệp pull, CI/CD).
- `.env` trong image → ai có image đều thấy password.
- **Truyền secret lúc runtime** bằng `-e` flag:

```bash
# Đúng: secret chỉ tồn tại lúc container chạy
docker run -e GITHUB_USERNAME=bine910 etl-week7

# Sai: secret nằm trong image vĩnh viễn
COPY .env .  # KHÔNG LÀM THẾ NÀY
```

**Nguyên tắc:** Image chứa **code**, không chứa **secret**.

## 7. Path trong Container

Container có filesystem riêng biệt. Không dùng path máy host.

```python
# Sai — path máy host, không tồn tại trong container:
with open("week_7/data/output.json", "w") as f:

# Đúng — path relative trong container:
os.makedirs("data", exist_ok=True)
with open("data/output.json", "w") as f:
```

## Lệnh cần nhớ

```bash
docker build -t <image_name> .       # Build image từ Dockerfile
docker run --name <name> <image>     # Tạo & chạy container
docker run -e KEY=VALUE <image>      # Truyền env variable
docker rm <name>                     # Xóa container trước khi tạo lại
```