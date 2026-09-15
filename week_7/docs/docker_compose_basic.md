# Week 7 — Day 3: Docker Compose — Multi-Service Stack

## 1. Docker Compose là gì

Compose cho phép định nghĩa và chạy **nhiều container cùng lúc** từ 1 file `docker-compose.yml`.

```
Không Compose:                      Có Compose:
  docker run ... postgres             docker compose up
  docker run ... etl-app              (xong)
  docker run ... minio
  (nhớ N lệnh, đúng thứ tự)
```

## 2. Cấu trúc docker-compose.yml

```yaml
services:           # Level 0 — khai báo các service
  postgres:         # Level 1 — tên service
    image: postgres:13
    environment:
      - POSTGRES_DB=de_practice
      - POSTGRES_USER=de_user
      - POSTGRES_PASSWORD=de_pass
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  etl:
    build: .        # Build image từ Dockerfile trong thư mục hiện tại
    environment:
      - GITHUB_USERNAME=octocat
      - DB_HOST=postgres
      - DB_PORT=5432
    depends_on:
      - postgres

volumes:            # Level 0 — ngang hàng với services
  postgres_data:
```

## 3. Service Networking

Các container trong cùng compose file gọi nhau bằng **tên service**, không phải `localhost`.

```
ETL app muốn connect PostgreSQL:
  DB_HOST=postgres    ← tên service (đúng)
  DB_HOST=localhost   ← sai, localhost là chính container ETL
```

Docker Compose tự tạo network nội bộ, mỗi service có DNS entry theo tên.

## 4. Volume Declaration — cần 2 chỗ

```yaml
services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data   # "service này DÙNG volume này"

volumes:
  postgres_data:                                  # "volume này TỒN TẠI"
```

- Trong service = mount volume vào path cụ thể
- Ngoài services = khai báo volume để Docker quản lý
- Giống SQL: `CREATE TABLE` trước, `INSERT` sau

## 5. depends_on Trap

`depends_on` chỉ đợi container **start**, KHÔNG đợi service **sẵn sàng nhận connection**.

```
Timeline:
  0s  - PostgreSQL container start
  0s  - ETL container start          ← depends_on chỉ đợi đến đây
  3s  - PostgreSQL sẵn sàng          ← ETL đã crash trước đó
```

**Giải pháp:** retry logic trong code:

```python
import time

def load_to_db(data, retries=5, delay=3):
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(...)
            break
        except psycopg2.OperationalError:
            log.warning(f"Thử lại ({attempt+1}/{retries})...")
            time.sleep(delay)
    else:
        log.error("Không thể kết nối")
        return
```

## 6. Lệnh cần nhớ

```bash
docker compose up                # Start tất cả services
docker compose up --build        # Rebuild image rồi start
docker compose up -d             # Start ngầm (detached)
docker compose down              # Stop + remove containers
docker compose down -v           # Stop + remove containers + volumes
docker compose logs <service>    # Xem log của 1 service
docker compose ps                # Liệt kê containers đang chạy

# Chạy lệnh trong container
docker exec -it <container> psql -U user -d db
  -d <database>   # Connect vào database nào
  -c "SQL"        # Chạy 1 lệnh SQL rồi thoát
```