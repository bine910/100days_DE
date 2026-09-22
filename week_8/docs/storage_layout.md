# Storage Layout — MinIO Data Lake (Tuần 8)

## 1. Tổng quan

- **Object Storage:** MinIO (open-source, S3-compatible)
- **Chạy bằng:** Docker Compose trên local
- **Endpoint API:** http://localhost:9000 (code Python kết nối)
- **Web Console:** http://localhost:9001 (quản lý bằng trình duyệt)
- **Bucket:** `datalake` (1 bucket duy nhất, phân tầng bằng path prefix)

## 2. Cấu trúc thư mục theo Medallion Architecture

```
datalake/                          ← Bucket
│
├── bronze/                        ← Tầng 1: Raw data nguyên bản
│   └── orders/
│       ├── 2026-09-18/
│       │   └── data.json          ← Y chang API trả về, KHÔNG sửa
│       └── 2026-09-19/
│           └── data.json
│
├── silver/                        ← Tầng 2: Data đã clean
│   └── orders/
│       ├── 2026-09-18/
│       │   └── orders_cleaned.parquet
│       └── 2026-09-19/
│           └── orders_cleaned.parquet
│
└── gold/                          ← Tầng 3: Aggregate cho business
    └── revenue_by_product/
        ├── 2026-09-18/
        │   └── revenue_by_product.parquet
        └── 2026-09-19/
            └── revenue_by_product.parquet
```

### Quy tắc đặt path

```
{tầng}/{source_name}/{date}/{filename}.{format}
```

- **tầng:** bronze / silver / gold
- **source_name:** tên nguồn data (orders, products, customers...)
- **date:** partition theo ngày (YYYY-MM-DD) → dễ backfill, dễ tìm
- **format:** .json (bronze), .parquet (silver/gold)

## 3. Chi tiết từng tầng

### Bronze — Raw data

| Mục | Chi tiết |
|-----|---------|
| **Mục đích** | Giữ nguyên bản gốc từ source |
| **Format** | Giữ nguyên format gốc: JSON từ API, CSV từ file |
| **Xử lý** | KHÔNG sửa gì — lưu y chang |
| **Khi nào cần** | Transform sai → quay lại đây chạy lại; Source sập → vẫn còn data; Audit/compliance |

### Silver — Cleaned data

| Mục | Chi tiết |
|-----|---------|
| **Mục đích** | Data sạch, có schema rõ ràng, query được |
| **Format** | Parquet (columnar, nhỏ gọn, có schema) |
| **Xử lý** | Flatten nested JSON → bảng phẳng; Cast type (string → int); Fill null; Deduplicate |
| **Khi nào cần** | Data Science dùng train model; DE dùng làm input cho Gold |

### Gold — Aggregated data

| Mục | Chi tiết |
|-----|---------|
| **Mục đích** | Data tổng hợp, trả lời câu hỏi business |
| **Format** | Parquet hoặc load vào PostgreSQL/BigQuery |
| **Xử lý** | GROUP BY, SUM, COUNT — aggregate theo nhu cầu business |
| **Khi nào cần** | BI dashboard (Metabase); Analyst query; Báo cáo cho sếp |

## 4. Data Flow Diagram

```
┌──────────────┐
│   SOURCE     │  API trả JSON / CSV file / PostgreSQL export
└──────┬───────┘
       │ Extract (Python requests, boto3)
       ▼
┌──────────────┐
│   BRONZE     │  MinIO: bronze/orders/2026-09-18/data.json
│   (Raw)      │  → Không sửa, giữ nguyên bản gốc
└──────┬───────┘
       │ Transform (Python pandas: flatten, clean, dedup)
       ▼
┌──────────────┐
│   SILVER     │  MinIO: silver/orders/2026-09-18/orders_cleaned.parquet
│   (Cleaned)  │  → Sạch, đúng type, không duplicate
└──────┬───────┘
       │ Aggregate (pandas/dbt: GROUP BY, SUM)
       ▼
┌──────────────┐
│    GOLD      │  MinIO: gold/revenue_by_product/2026-09-18/revenue_by_product.parquet
│ (Aggregated) │  → Sẵn sàng cho dashboard
└──────┬───────┘
       │ Serve
       ▼
┌──────────────┐
│  DASHBOARD   │  Metabase / Looker / SQL query
│   (BI)       │  → Sếp nhìn biểu đồ doanh thu
└──────────────┘
```

## 5. Kết nối MinIO bằng Python (boto3)

```python
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin123",
)

# Upload
s3.upload_file(Filename="local_file.json", Bucket="datalake", Key="bronze/orders/2026-09-18/data.json")

# Download
s3.download_file("datalake", "silver/orders/2026-09-18/orders_cleaned.parquet", "local_copy.parquet")
```

**Lưu ý:** MinIO API giống AWS S3 → khi deploy lên cloud, chỉ cần đổi `endpoint_url` sang `https://s3.amazonaws.com`, code không đổi.

## 6. Docker Compose

```yaml
services:
  minio:
    image: quay.io/minio/minio
    container_name: minio_lake
    ports:
      - "9000:9000"    # API (boto3 kết nối)
      - "9001:9001"    # Web Console (trình duyệt)
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"

volumes:
  minio_data:             # Data persist khi restart container
```

## 7. Scripts đã viết

| File | Tầng | Chức năng |
|------|------|-----------|
| `upload_bronze.py` | Bronze | Upload raw JSON vào MinIO, không sửa gì |
| `02_transform_silver.py` | Silver | Đọc Bronze → flatten, cast type, fill null, dedup → Parquet |
| `03_aggregate_gold.py` | Gold | Đọc Silver → GROUP BY product, SUM revenue → Parquet |