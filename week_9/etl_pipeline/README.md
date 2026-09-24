# ETL Pipeline — Gold Price (XAU)

Pipeline ETL đơn giản để nạp dữ liệu giá vàng (XAU) dạng nến ngày từ file CSV (hoặc từ MinIO) vào PostgreSQL, có hỗ trợ backfill theo khoảng ngày và load idempotent (chạy lại nhiều lần không tạo dữ liệu trùng).

## Mô tả project

Pipeline gồm 3 bước cổ điển:

1. **Extract** (`extract.py`) — đọc dữ liệu giá vàng từ:
   - file CSV local (`extract`), hoặc
   - object trên MinIO (`extract_from_minio`), dữ liệu được đọc thẳng vào `pandas.DataFrame` từ bytes trả về, không cần tải file xuống đĩa.
2. **Transform** (`transform.py`) — parse cột `Date` sang kiểu datetime và lọc dữ liệu theo khoảng `[start_date, end_date]` nếu được truyền vào (dùng cho backfill một giai đoạn cụ thể).
3. **Load** (`load.py`) — ghi dữ liệu vào bảng `gold_price_daily` trong PostgreSQL bằng `INSERT ... ON CONFLICT (date) DO UPDATE` (UPSERT), theo lô (bulk) bằng `execute_values`.

`main.py` là entrypoint, nối 3 bước lại và nhận tham số dòng lệnh để chọn nguồn dữ liệu và khoảng ngày cần chạy.

`logger.py` cấu hình logging dùng chung cho cả pipeline: một logger tên `etl`, ghi log đồng thời ra console và ra file `logs/etl.log` (append). `extract.py`, `transform.py`, `load.py` đều import `log` từ module này thay vì tự gọi `logging.basicConfig` riêng lẻ, tránh log bị cấu hình trùng/khác định dạng giữa các module.

`test_pipeline.py` là bộ test chất lượng dữ liệu (data quality test) chạy **sau** khi pipeline load xong: kết nối thẳng vào PostgreSQL và kiểm tra lại dữ liệu thực tế trong bảng `gold_price_daily` bằng các câu SQL `COUNT`, thay vì test logic Python bằng dữ liệu giả.

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
    ├── load.py                    # UPSERT (bulk) vào PostgreSQL
    ├── logger.py                   # cấu hình logging dùng chung (console + file logs/etl.log)
    ├── logs/
    │   └── etl.log                 # log file, được logger.py ghi append vào
    ├── upload_to_minio.py          # đẩy CSV gốc lên MinIO (bronze layer)
    ├── test_pipeline.py            # test chất lượng dữ liệu sau khi load vào Postgres
    ├── docker-compose.yml          # PostgreSQL + MinIO cho local dev
    ├── requirement.txt             # dependency Python (pin version)
    ├── .env.example                # mẫu biến môi trường, copy thành .env
    └── README.md
```

## Cài đặt

### 1. Yêu cầu

- Python 3.12
- Docker (để chạy PostgreSQL + MinIO)

### 2. Cấu hình biến môi trường

Copy `.env.example` thành `.env` rồi điền giá trị thật:

```bash
cp .env.example .env
```

`docker-compose.yml` đọc trực tiếp các biến sau từ `.env` (Docker Compose tự nạp file `.env` cùng thư mục):

```
POSTGRES_DB=de_week9
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
aws_access_key_id=minioadmin
aws_secret_access_key=minioadmin
```

`.env.example` hiện chỉ có sẵn `aws_access_key_id`/`aws_secret_access_key` — cần tự thêm 3 dòng `POSTGRES_*` ở trên vào `.env.example`/`.env` thì `docker-compose up` mới chạy được, vì `docker-compose.yml` đã đổi từ giá trị hard-code sang `${POSTGRES_DB}`, `${POSTGRES_USER}`, `${POSTGRES_PASSWORD}`, `${aws_access_key_id}`, `${aws_secret_access_key}`.

`upload_to_minio.py` cũng tự đọc `aws_access_key_id`/`aws_secret_access_key` từ `.env` (qua `python-dotenv`) để xác thực với MinIO, nên giá trị trong `.env` phải khớp với `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` mà container MinIO đang chạy.

> **Lưu ý — chưa đồng bộ hết:** `extract.py` (`extract_from_minio`) và `load.py` (`psycopg2.connect(...)`) **vẫn đang hard-code** `minioadmin`/`minioadmin` và `postgres`/`postgres`/`de_week9`, chưa đọc từ `.env`. Nếu đổi giá trị trong `.env` khác với các giá trị hard-code này, `main.py --source minio` và bước `load()` sẽ kết nối thất bại. Cần sửa `extract.py`/`load.py` để dùng `os.getenv(...)` giống `upload_to_minio.py` nếu muốn đổi credential.

### 3. Dựng hạ tầng local

```bash
cd week_9/etl_pipeline
docker-compose up -d
```

Lệnh này khởi động:

- **PostgreSQL** — `localhost:5432`, database/user/password lấy từ `.env`
- **MinIO** — API tại `localhost:9000`, console tại `localhost:9001`, access/secret key lấy từ `.env` (`aws_access_key_id`/`aws_secret_access_key`)

### 4. Tạo bảng đích trong PostgreSQL

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

### 5. Cài dependency Python

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirement.txt
```

`requirement.txt` (lưu ý tên file không có "s") pin sẵn version của `pandas`, `boto3`, `psycopg2-binary`, `python-dotenv` (đọc `.env`) và `tenacity` (retry).

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

## Kiểm thử dữ liệu (data quality test)

Sau khi chạy pipeline, dùng `test_pipeline.py` để verify dữ liệu đã thực sự nằm đúng trong bảng `gold_price_daily`:

```bash
python test_pipeline.py
```

Hoặc chạy bằng pytest:

```bash
pytest test_pipeline.py -v
```

Script kết nối tới Postgres rồi chạy 3 assertion trên chính dữ liệu đã load (không dùng dữ liệu giả):

| Test | Câu SQL kiểm tra | Ý nghĩa |
|------|------------------|---------|
| 1. Completeness | `COUNT(*) WHERE date BETWEEN '2024-01-01' AND '2024-01-31'` phải bằng `22` | Đúng số phiên giao dịch của tháng 1/2024 — phát hiện trường hợp load thiếu ngày hoặc filter sai khoảng ngày. |
| 2. Validity | `COUNT(*) WHERE high < low` phải bằng `0` | Ràng buộc nghiệp vụ của nến giá: giá cao nhất không thể thấp hơn giá thấp nhất. Nếu > 0 thì dữ liệu nguồn hỏng hoặc thứ tự cột bị map sai khi insert. |
| 3. Uniqueness | `COUNT(*)` phải bằng `COUNT(DISTINCT date)` | Xác nhận UPSERT theo `date` hoạt động đúng — chạy lại pipeline nhiều lần không nhân đôi dữ liệu (kiểm chứng tính idempotent ở phần dưới). |

Mọi kết quả (pass/fail) đều được ghi qua logger chung nên xuất hiện cả trên console lẫn trong `logs/etl.log`. Nếu không kết nối được Postgres, test fail ngay với log `Database connection failed` thay vì báo lỗi mơ hồ.

Lưu ý: test số 1 đang hard-code mốc `22` dòng cho tháng 1/2024, nên chỉ đúng khi đã chạy pipeline phủ được khoảng ngày đó (ví dụ chạy full file, hoặc backfill `--start-date 2024-01-01 --end-date 2024-01-31`).

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

`load.py` dùng `execute_values` (thư viện `psycopg2.extras`) để gửi toàn bộ `VALUES` trong một câu lệnh duy nhất thay vì `cursor.execute()` từng dòng một trong vòng lặp, nên nhanh hơn đáng kể so với insert theo dòng khi dataset lớn dần.

## Retry tự động

`extract()`, `extract_from_minio()` và `load()` đều được bọc `@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))` (thư viện `tenacity`): nếu lỗi tạm thời (mất kết nối MinIO/Postgres, timeout...), hàm tự thử lại tối đa 3 lần, cách nhau 5 giây, trước khi raise exception ra ngoài. Kết hợp với UPSERT idempotent ở bước load, việc retry này không tạo dữ liệu trùng dù `load()` bị gọi lại nhiều lần cho cùng một batch.

## Logging

Toàn bộ pipeline dùng chung một logger (`log`) được cấu hình một lần trong `logger.py`, thay vì mỗi module tự `logging.basicConfig`. Logger này có 2 handler:

- **Console** — in log ra stdout khi chạy `python main.py`.
- **File** — ghi append vào `logs/etl.log` (thư mục `logs/` cần tồn tại sẵn cạnh các file `.py`, hoặc chạy pipeline từ đúng thư mục `etl_pipeline/` để đường dẫn tương đối `logs/etl.log` hợp lệ).

Mỗi dòng log có format `%(asctime)s - %(levelname)s - %(message)s`, dùng để theo dõi số dòng extract/transform được, kết quả load, và lỗi (kèm retry) khi có sự cố kết nối MinIO/Postgres. `test_pipeline.py` cũng import cùng logger này, nên kết quả từng test được ghi lại chung một dòng thời gian với log của pipeline.
