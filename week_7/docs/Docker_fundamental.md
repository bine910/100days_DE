# Week 7 — Day 1: Docker Fundamentals

## 1. Image vs Container

- **Image** = blueprint đã build sẵn từ Dockerfile, nằm trên đĩa, không chạy.
- **Container** = instance tạo từ image, đang chạy (hoặc đã dừng).
- Một image tạo được nhiều container. Mỗi container độc lập.

```
postgres:16 (image)
  ├── container "db-dev"      (port 5432)
  ├── container "db-test"     (port 5433)
  └── container "db-staging"  (port 5434)
```

Analogy: Image ≈ class, Container ≈ instance (`new MyService()`).

## 2. Container vs VM

Container và VM đều cách ly ứng dụng, nhưng khác nhau ở **kernel sharing**.

```
VM:
  Hardware → Hypervisor → [Guest OS + Kernel + Libs + App]
                          [Guest OS + Kernel + Libs + App]
                          (mỗi VM có OS + kernel riêng)

Container:
  Hardware → Host OS + Kernel → Docker Engine → [Libs + App]
                                                [Libs + App]
                                (share kernel của host)
```

- Container start trong **giây** vì không boot OS. VM cần **phút**.
- Container dùng **MB** RAM. VM cần **GB**.
- Docker Engine chỉ là daemon quản lý container, **không có kernel riêng**.

## 3. Docker Run Flags

```bash
docker run -d --name pg-week7 \
  -e POSTGRES_USER=de_user \
  -e POSTGRES_PASSWORD=de_pass \
  -e POSTGRES_DB=de_practice \
  -p 5433:5432 \
  postgres:16
```

| Flag | Ý nghĩa |
|------|---------|
| `-d` | Chạy ngầm (detached mode), không chiếm terminal |
| `--name` | Đặt tên container |
| `-e` | Truyền environment variable vào container |
| `-p 5433:5432` | Port mapping — `host_port:container_port` |

## 4. Stop vs Remove

```bash
docker stop <name>   # Tạm dừng — container vẫn tồn tại, data còn
docker start <name>  # Bật lại container đã stop
docker rm -f <name>  # Xóa container — filesystem đi theo, data mất
docker ps            # Container đang chạy
docker ps -a         # Tất cả container (cả đã dừng)
```

**Quan trọng:** `stop` ≠ xóa. Container stop vẫn nằm trên đĩa, start lại được.

## 5. Volume — Data Persistence

Không volume: `rm` → `run` lại → **data mất**.
Có volume: `rm` → `run` lại → **data còn**.

```bash
docker run -d --name pg-with-vol \
  -e POSTGRES_PASSWORD=test \
  -p 5433:5432 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16
```

| Phần | Ý nghĩa |
|------|---------|
| `pgdata` | Tên volume (Docker quản lý, nằm ngoài container) |
| `/var/lib/postgresql/data` | Path bên trong container nơi PostgreSQL lưu data |

Volume lưu data **ngoài container**, nên container bị xóa thì data vẫn sống.

## Lệnh hữu ích

```bash
docker exec -it <name> bash          # Mở shell trong container
docker exec -it <name> psql -U user  # Chạy psql trong container
docker logs <name>                   # Xem log container
docker volume ls                     # Liệt kê volume
docker volume rm <name>              # Xóa volume
```