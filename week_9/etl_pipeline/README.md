# ETL Pipeline — Gold Price (XAU)

Pipeline ETL đơn giản để nạp dữ liệu giá vàng (XAU) dạng nến ngày từ file CSV (hoặc từ MinIO) vào PostgreSQL, có hỗ trợ backfill theo khoảng ngày và load idempotent (chạy lại nhiều lần không tạo dữ liệu trùng).

## Mô tả project

Pipeline gồm 3 bước cổ điển:

1. **Extract** (`extract.py`) — đọc dữ liệu giá vàng từ:
   - file CSV local (`extract`), hoặc
   - object trên MinIO (`extract_from_minio`), dữ liệu được đọc thẳng vào `pandas.DataFrame` từ bytes trả về, không cần tải file xuống đĩa.
2. **Transform** (`transform.py`) — parse cột `Date` sang kiểu datetime và lọc dữ liệu theo khoảng `[start_date, end_date]` nếu được truyền vào (dùng cho backfill một giai đoạn cụ thể).
3. **Load** (`load.py`) — ghi dữ liệu vào bảng `gold_price_daily` trong PostgreSQL bằng `INSERT ... ON CONFLICT (date) DO UPDATE` (UPSERT), theo từng dòng.

`main.py` là entrypoint, nối 3 bước lại và nhận tham số dòng lệnh để chọn nguồn dữ liệu và khoảng ngày cần chạy.

Ngoài ra, `upload_to_minio.py` là một script phụ dùng để đẩy file CSV gốc lên MinIO theo layer "bronze" (`gold-price/bronze/<ngày>/XAU_1d_data.csv`), mô phỏng bước ingest dữ liệu thô vào data lake trước khi ETL đọc lại từ đó.

`docker-compose.yml` dựng 2 service cần thiết để chạy pipeline ở local: PostgreSQL và MinIO.

## Cấu trúc thư mục

```
week_9/
├── data/
│   └── raw/
│       └── XAU_1d_data.csv        # dữ liệu nguồn (CSV, phân cách bằng ";")
├── docs/
│   ├── etl_vs_elt.md
│   └── idempotency_patterns.md
└── etl_pipeline/
    ├── main.py                    # entrypoint: parse args, chạy extract -> transform -> load
    ├── extract.py                 # đọc CSV local hoặc object trên MinIO
    ├── transform.py                # parse ngày, filter theo start/end date
    ├── load.py                    # UPSERT vào PostgreSQL
    ├── upload_to_minio.py          # đẩy CSV gốc lên MinIO (bronze layer)
    ├── docker-compose.yml          # PostgreSQL + MinIO cho local dev
    └── README.md
```

## Cài đặt

### 1. Yêu cầu

- Python 3.12
- Docker (để chạy PostgreSQL + MinIO)

### 2. Dựng hạ tầng local

```bash
cd week_9/etl_pipeline
docker-compose up -d
```

Lệnh này khởi động:

- **PostgreSQL** — `localhost:5432`, database `de_week9`, user/password `postgres`/`postgres`
- **MinIO** — API tại `localhost:9000`, console tại `localhost:9001`, access/secret key `minioadmin`/`minioadmin`

### 3. Tạo bảng đích trong PostgreSQL

`load.py` giả định bảng `gold_price_daily` đã tồn tại với `date` là khóa duy nhất (bắt buộc để `ON CONFLICT (date)` hoạt động):

```sql
CREATE TABLE gold_price_daily (
    date   DATE PRIMARY KEY,
    open   NUMERIC,
    high   NUMERIC,
    low    NUMERIC,
    close  NUMERIC,
    volume BIGINT
);
```

### 4. Cài dependency Python

Project chưa có `requirements.txt`, cài trực tiếp các package sau vào virtualenv:

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install pandas boto3 psycopg2-binary
```

## Cách chạy

### Chạy toàn bộ file (không giới hạn ngày)

```bash
python main.py
```

Mặc định đọc từ `../data/raw/XAU_1d_data.csv` (nguồn `local`) và nạp toàn bộ dữ liệu vào Postgres.

### Ví dụ backfill theo khoảng ngày

Chỉ nạp lại dữ liệu của một giai đoạn cụ thể, ví dụ backfill cả năm 2023:

```bash
python main.py --start-date 2023-01-01 --end-date 2023-12-31
```

`transform.py` sẽ lọc DataFrame về đúng khoảng `[start-date, end-date]` trước khi load, nên có thể backfill từng giai đoạn nhỏ (theo tháng, theo năm...) mà không phải nạp lại toàn bộ file mỗi lần.

### Chạy từ nguồn MinIO thay vì file local

```bash
# 1. Đẩy raw CSV lên MinIO trước (ghi vào bronze/<ngày-hôm-nay>/...)
python upload_to_minio.py

# 2. Đọc lại từ MinIO và nạp vào Postgres
python main.py --source minio --start-date 2023-01-01 --end-date 2023-12-31
```

> **Lưu ý:** `main.py` đang hard-code key MinIO là `bronze/2026-09-22/XAU_1d_data.csv`. Muốn dùng `--source minio` với ngày khác, phải sửa lại `bronze_key` trong `main.py` (hoặc `extract_from_minio(...)` được gọi) cho khớp với ngày mà `upload_to_minio.py` đã upload.

## Idempotency (vì sao chạy lại nhiều lần vẫn an toàn)

Bước `load` dùng **UPSERT** thay vì `INSERT` thuần:

```sql
INSERT INTO gold_price_daily (date, open, high, low, close, volume)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (date)
DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    volume = EXCLUDED.volume;
```

`date` được dùng làm **natural key** (một ngày giao dịch chỉ có một dòng dữ liệu). Vì vậy:

- Chạy `python main.py --start-date ... --end-date ...` **nhiều lần với cùng khoảng ngày** sẽ không tạo dòng trùng — dòng đã tồn tại chỉ bị ghi đè bằng giá trị mới nhất, không insert thêm bản ghi mới.
- Có thể an toàn **retry** khi job backfill bị lỗi giữa chừng (network drop, container restart...) mà không cần logic dọn dẹp dữ liệu trước khi chạy lại — chỉ cần chạy lại đúng lệnh cũ.
- Có thể chạy backfill **chồng lấn khoảng ngày** (ví dụ chạy lại tháng 6 sau khi đã chạy cả quý 2) mà không sợ nhân đôi dữ liệu của những ngày trùng.

Đánh đổi: pipeline load từng dòng một (`for _, row in df.iterrows(): cursor.execute(...)`) nên với dataset lớn sẽ chậm hơn so với bulk upsert (`execute_values`/`COPY ... ON CONFLICT`); hiện tại chấp nhận được vì dữ liệu nến ngày (`XAU_1d_data.csv`) không quá lớn.
