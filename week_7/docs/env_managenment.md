# Week 7 — Day 4: Environment Variables & Secret Management

## 1. Vấn đề — Hardcode secret trong docker-compose.yml

```yaml
# Sai — password nằm trong file, push GitHub → lộ
environment:
  - POSTGRES_PASSWORD=de_pass
```

## 2. Giải pháp — .env file

Docker Compose tự động đọc file `.env` cùng thư mục với `docker-compose.yml`.

### .env (giá trị thật — KHÔNG commit)
```
POSTGRES_DB=de_practice
POSTGRES_USER=de_user
POSTGRES_PASSWORD=de_pass
DB_HOST=postgres
DB_PORT=5432
GITHUB_USERNAME=bine910
```

### docker-compose.yml (dùng biến — commit được)
```yaml
environment:
  - POSTGRES_DB=${POSTGRES_DB}
  - POSTGRES_USER=${POSTGRES_USER}
  - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
```

## 3. .env.example — Template cho người khác

Commit lên repo để người clone biết cần biến gì, nhưng không thấy giá trị thật:

```
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
DB_HOST=postgres
DB_PORT=5432
GITHUB_USERNAME=
```

Người mới clone: `cp .env.example .env` → điền giá trị → chạy.

## 4. .gitignore

```
.env
```

`.env` chứa secret → không commit. `.env.example` là template → commit.

## Nguyên tắc

| File | Chứa gì | Commit? |
|------|---------|---------|
| `docker-compose.yml` | Cấu trúc stack + `${VAR}` | Có |
| `.env` | Giá trị thật (password, API key) | **Không** |
| `.env.example` | Template không có giá trị | Có |
| `.gitignore` | Danh sách file không commit | Có |