# ETL Pipeline — GitHub Repos → PostgreSQL

Pipeline lấy danh sách repo từ GitHub API rồi load vào PostgreSQL. Toàn bộ chạy trong Docker.

## Prerequisites

- Docker Engine
- Tài khoản GitHub (để lấy username)

## Setup & Run

1. Copy file env và điền giá trị:

```bash
cp .env.example .env
```

2. Điền thông tin vào `.env`:

```
POSTGRES_DB=de_practice
POSTGRES_USER=de_user
POSTGRES_PASSWORD=your_password
DB_HOST=postgres
DB_PORT=5432
GITHUB_USERNAME=your_github_username
```

3. Chạy stack:

```bash
docker compose up --build
```

4. Kiểm tra data:

```bash
docker exec -it etl_app-postgres-1 psql -U de_user -d de_practice -c "SELECT name, html_url FROM github_repos;"
```

## Dọn dẹp

```bash
docker compose down        # Stop + xóa containers
docker compose down -v     # Stop + xóa containers + volume (mất data)
```