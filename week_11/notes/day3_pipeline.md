# Pipeline T9 trong Airflow — Week 11 / Day 3

> Deliverable bắt buộc của T11: `dags/etl_daily.py` — đưa ETL giá vàng (XAU) từ T9 vào Airflow DAG.
> Kết quả: 5531 dòng, 2004-06-11 → 2026-01-30, trong `postgres-dwh`.

---

## 1. Bốn chỗ gãy khi đưa script vào Airflow

Code T9 chạy tốt standalone, nhưng đưa nguyên vào Airflow thì hỏng ở 4 điểm. Đây là checklist cho mọi lần migrate script → DAG:

| # | Vấn đề | Vì sao gãy | Sửa |
|---|---|---|---|
| 1 | `host="localhost"` | Trong container, `localhost` là **chính container đó**, không phải máy host | Dùng **tên service Docker**: `postgres-dwh` |
| 2 | `"../data/raw/XAU_1d_data.csv"` | Đường dẫn tương đối tính từ nơi chạy lệnh; container không có thư mục đó | Mount volume + dùng path tuyệt đối `/opt/airflow/data/...` |
| 3 | `@retry` của tenacity | Chồng lên retry của Airflow → 3×3 = 9 lần thử, UI chỉ thấy 1 attempt | Bỏ tenacity, giao retry cho `default_args` |
| 4 | Truyền `pd.DataFrame` giữa các hàm | 3 task chạy ở 3 process khác nhau, data phải qua XCom | Truyền **path**, data nằm trên đĩa |

### Vì sao retry phải là của Airflow, không phải tenacity

Tenacity retry **bên trong** một lần chạy task → Airflow chỉ thấy một attempt. Nếu fail cả 3 lần, UI hiện `try 1/1 failed`, không biết đã thử gì.

Mất những thứ sau: lịch sử từng attempt trong UI, `retry_delay` cấu hình được, exponential backoff, và quan trọng nhất — **khả năng clear task để chạy lại thủ công sau khi fix**.

> **Nguyên tắc: giao việc retry cho tầng điều phối, không nhúng vào code nghiệp vụ.**
> Cùng họ với việc không tự viết `@Cron` trong NestJS service khi đã có scheduler.

---

## 2. Kiến trúc đã dựng

```
week_11/airflow/
├── docker-compose.yaml
├── dags/
│   ├── etl_daily.py          ← chỉ wiring, không logic
│   ├── hello_classic.py
│   ├── hello_taskflow.py
│   └── etl/
│       ├── __init__.py       ← BẮT BUỘC, file rỗng
│       ├── extract.py
│       ├── transform.py
│       └── load.py
└── ...

week_9/data/                  ← mount vào /opt/airflow/data
├── raw/XAU_1d_data.csv
└── staging/                  ← nơi task ghi parquet trung gian
```

Để `etl/` **bên trong** `dags/` để nó cũng được mount và import được.

### Luồng dữ liệu giữa 3 task

```
extract_gold_price()          → đọc CSV → ghi staging/raw.parquet   → return path
transform_gold_price(path)    → đọc parquet → lọc → ghi clean.parquet → return path
load_gold_price(path)         → đọc parquet → UPSERT Postgres        → return số dòng
```

XCom chỉ mang 2 chuỗi path + 1 số nguyên. **Data nằm trên đĩa.**

Chọn Parquet thay CSV (T10): giữ được kiểu dữ liệu (`Date` vẫn là datetime khi đọc lại), nén tốt, đọc nhanh.

> **Quan trọng:** ghi vào thư mục **đã mount** (`/opt/airflow/data/staging`). Ghi vào `/tmp` của container thì task sau chạy ở process/container khác sẽ **không thấy file** — lỗi kinh điển khi dùng CeleryExecutor.

---

## 3. Metadata DB ≠ Warehouse

Postgres có sẵn trong compose là **của Airflow**. Phải dựng cái thứ hai cho data:

```yaml
  postgres-dwh:
    image: postgres:16
    environment:
      POSTGRES_USER: dwh
      POSTGRES_PASSWORD: dwh
      POSTGRES_DB: de_week9
    ports:
      - "5433:5432"          # 5433 vì Postgres cài trên Windows đang giữ 5432
    volumes:
      - postgres-dwh-volume:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "dwh"]
      interval: 10s
      retries: 5
```

`5433:5432` = `<cổng trên host>:<cổng trong container>`. Trong mạng Docker nó vẫn là 5432; chỉ phần publish ra host mới đổi.

### Connection — không hardcode credential

Thêm vào `x-airflow-common` → `environment:`:

```yaml
  AIRFLOW_CONN_POSTGRES_DWH: 'postgresql://dwh:dwh@postgres-dwh:5432/de_week9'
```

Biến môi trường viết HOA + gạch dưới; `conn_id` dùng trong code là **thường**: `postgres_dwh`.

```bash
docker compose run --rm airflow-cli connections get postgres_dwh
```

Trong code:
```python
hook = PostgresHook(postgres_conn_id="postgres_dwh")
conn = hook.get_conn()          # KHÔNG tham số — mọi thông tin lấy từ Connection
```

> Truyền `host=`, `user=`… vào `get_conn()` vừa sai cú pháp, vừa phá đúng lợi ích của Connection.

---

## 4. Mount volume — cú pháp và cách debug

```yaml
volumes:
  - <đường dẫn trên host>:<đường dẫn tuyệt đối trong container>
```

Vế phải **luôn bắt đầu bằng `/`**.

```yaml
  - ${AIRFLOW_PROJ_DIR:-.}/dags:/opt/airflow/dags
  - ${AIRFLOW_PROJ_DIR:-.}/../../week_9/data:/opt/airflow/data
```

### Lệnh debug mount

```bash
docker compose config | grep -B 2 -A 4 "week_9"
```

In ra cấu hình **sau khi resolve mọi biến và đường dẫn tương đối** — cho biết chính xác Docker mount từ đâu đến đâu. Chạy lệnh này thay vì đọc YAML bằng mắt.

Sửa compose xong mà container không nhận: `docker compose up -d --force-recreate`.

---

## 5. DDL và kiểu dữ liệu

```sql
CREATE TABLE gold_price_daily (
    date   DATE PRIMARY KEY,     -- PK bắt buộc, nếu không ON CONFLICT (date) sẽ lỗi
    open   NUMERIC(12,4),
    high   NUMERIC(12,4),
    low    NUMERIC(12,4),
    close  NUMERIC(12,4),
    volume INTEGER
);
```

**Bẫy đã mắc: `NUMERIC(2,1)`.** Cú pháp là `NUMERIC(precision, scale)` = tổng số chữ số, số chữ số sau dấu phẩy. `NUMERIC(2,1)` chứa tối đa **9.9** — dữ liệu `384.8` sẽ gây lỗi tràn số.

> **Luôn đối chiếu kiểu cột với dữ liệu thật** (`head -3` file nguồn), không chọn theo cảm tính.
> Chọn dư một chút (`NUMERIC(12,4)`): chi phí lưu gần như bằng nhau, `ALTER TABLE` vì tràn số thì rất phiền.

### Grain — bẫy nguy hiểm nhất

CSV có `Date` = `2004.06.11 00:00` (có phần giờ). Cột Postgres là `DATE`. Postgres **tự cắt** phần giờ → hôm nay không mất gì.

Nhưng nếu chuyển sang `XAU_1h_data.csv`: `2004-06-11 09:00` và `2004-06-11 10:00` cùng ép về `2004-06-11` → `ON CONFLICT (date)` coi là trùng → **ghi đè, mất dữ liệu trong im lặng, không một lỗi nào.**

Đây là **grain** của T6: bảng `gold_price_daily` có grain = một dòng một ngày.

Chuẩn hoá tường minh trong `transform`, đừng trông chờ Postgres ép kiểu giùm:
```python
df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
```

---

## 6. `load.py` — bản hoàn chỉnh và lý do từng chi tiết

```python
import logging

import pandas as pd
from airflow.providers.postgres.hooks.postgres import PostgresHook

log = logging.getLogger(__name__)

COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]

INSERT_SQL = """
    INSERT INTO gold_price_daily (date, open, high, low, close, volume)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (date) DO UPDATE SET
        open   = EXCLUDED.open,
        high   = EXCLUDED.high,
        low    = EXCLUDED.low,
        close  = EXCLUDED.close,
        volume = EXCLUDED.volume
"""


def load(df: pd.DataFrame) -> int:
    if df.empty:
        log.warning("DataFrame rỗng — không có gì để load")
        return 0

    rows = list(df[COLUMNS].itertuples(index=False, name=None))

    hook = PostgresHook(postgres_conn_id="postgres_dwh")
    with hook.get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(INSERT_SQL, rows)
        conn.commit()

    log.info("Loaded %d rows into gold_price_daily", len(rows))
    return len(rows)
```

**`COLUMNS` tách thành hằng số, không dùng `df.values`.**
`data = [tuple(row) for row in df.values]` phụ thuộc **thứ tự cột** của DataFrame. Hôm nào `transform` thêm một cột là load sai cột mà không báo lỗi — "sai dữ liệu trong im lặng" lần nữa.
`df[COLUMNS]` chọn đúng 6 cột theo đúng thứ tự; thiếu cột thì pandas raise `KeyError` ngay — **fail sớm thay vì ghi sai**.

**Tên cột viết hoa trong `COLUMNS`** (`"Date"`, `"Open"`) là tên cột **DataFrame** (lấy từ header CSV). Tên viết thường nằm trong SQL. `executemany` chỉ ghép giá trị **theo vị trí**.
> **Ranh giới giữa pandas và SQL là ranh giới tên cột. Chỗ chuyển đổi phải tường minh.**

**Không `try/except` bọc toàn bộ.** Trong Airflow, bắt exception rồi `log.error` rồi `raise` lại là thừa: exception tự bay lên, Airflow ghi traceback vào tab Logs và đánh task đỏ. Giữ lại chỉ làm log dài gấp đôi. `with` tự rollback khi có exception.

**Trả về `int`** — số dòng đã load thành XCom (metadata nhỏ, đúng chuẩn). Day 5/6 cần con số này để verify backfill không tạo trùng.

**Chặn `df.empty` sớm** — Day 4 lọc theo ngày rất dễ ra rỗng.

---

## 7. `execute_values` vs `executemany` ⚠️

Lỗi mất thời gian nhất hôm nay:

```
AttributeError: 'Connection' object has no attribute 'encoding'
  File ".../psycopg2/extras.py", line 1287, in execute_values
```

**Nguyên nhân: trộn hai driver.** `PostgresHook` ở provider mới trả về connection của **psycopg v3**, còn `execute_values` import từ **psycopg2**. Hàm psycopg2 cố đọc `.encoding` — thuộc tính chỉ có trên connection psycopg2.

| | `execute_values` | `executemany` |
|---|---|---|
| Là gì | **Hàm** trong `psycopg2.extras` | **Method** của cursor (DB-API chuẩn) |
| Import | `from psycopg2.extras import execute_values` | không import gì |
| Cú pháp SQL | `VALUES %s` (một placeholder cho cả khối) | `VALUES (%s, %s, ...)` (một cho mỗi cột) |
| Gọi | `execute_values(cursor, sql, rows)` | `cursor.executemany(sql, rows)` |

→ Với provider Airflow mới, dùng `executemany`. Chạy được với cả hai driver.

(`from psycopg2.extras import executemany` là sai — nó không phải hàm import được.)

---

## 8. Import trong file DAG

```python
from etl.extract import extract        # ĐÚNG
```

```python
from week_11.airflow.dags.etl.extract import extract   # SAI — VS Code hay tự "sửa" thành thế này
```

> **Đường dẫn import tính từ `/opt/airflow/dags`, không phải cấu trúc thư mục trên máy host.**
> Airflow đã thêm `/opt/airflow/dags` vào `sys.path`, nên `from etl.extract import ...` tìm thấy `dags/etl/extract.py`.

IDE autocomplete hay dẫn sai ở đây vì nó nhìn filesystem host, container thì không.

`dags/etl/__init__.py` (file rỗng) là **bắt buộc** — nó báo Python biết thư mục này là package importable.

---

## 9. Mỗi DAG một file

Dán 2 DAG vào cùng file gây lỗi thật: `hello_taskflow` định nghĩa 3 hàm tên `extract`, `transform`, `load` → **đè lên** 3 hàm import từ `etl/`. `etl_daily` gọi `extract(...)` sẽ gọi nhầm hàm trả `[12, 45, 7, 103, 88]`.

→ Không chỉ để gọn, mà vì **namespace dùng chung**.

---

## 10. `retries` + `dags test` = treo vòng lặp ⚠️

```
No tasks to run. unrunnable tasks: {<TaskInstance: ... [up_for_retry]>}
No tasks to run. unrunnable tasks: ...   (lặp vô tận)
```

Task vào trạng thái `up_for_retry`, nhưng `dags test` chạy **một process đơn**, không có scheduler để đợi hết `retry_delay` rồi gọi lại → kẹt.

Khi debug:
- đặt tạm `retries: 0`, hoặc
- test **một task lẻ**:
```bash
docker compose run --rm airflow-cli tasks test etl_daily load_gold_price 2026-10-01
```

`tasks test` còn lợi nữa: sửa `load.py` thì chỉ chạy lại task đó, không phải đọc CSV và transform lại từ đầu — **đúng lợi ích của việc tách task** đã nêu ở Day 1.

---

## 11. Lệnh debug theo thứ tự

```bash
# DAG không hiện trong dags list → chạy cái này ĐẦU TIÊN
docker compose run --rm airflow-cli dags list-import-errors

# mount không như mong đợi
docker compose config | grep -B 2 -A 4 "<tên thư mục>"
docker compose exec airflow-scheduler ls /opt/airflow/data/raw

# connection
docker compose run --rm airflow-cli connections get postgres_dwh

# chạy
docker compose run --rm airflow-cli dags test etl_daily 2026-10-01
docker compose run --rm airflow-cli tasks test etl_daily load_gold_price 2026-10-01

# verify data — LUÔN LUÔN làm bước này
docker compose exec postgres-dwh psql -U dwh -d de_week9 \
  -c "SELECT count(*), min(date), max(date) FROM gold_price_daily;"
docker compose exec postgres-dwh psql -U dwh -d de_week9 \
  -c "SELECT * FROM gold_price_daily ORDER BY date LIMIT 3;"
```

---

## 12. Kết quả Day 3

```
 count |    min     |    max
-------+------------+------------
  5531 | 2004-06-11 | 2026-01-30

    date    | open  | high  |  low  | close | volume
------------+-------+-------+-------+-------+--------
 2004-06-11 | 384.0 | 384.8 | 382.8 | 384.1 |    272
 2004-06-14 | 384.3 | 385.8 | 381.8 | 382.8 |   1902
 2004-06-15 | 382.8 | 388.8 | 381.1 | 388.6 |   1951
```

Khớp chính xác với `head -3` của file nguồn — cột đúng vị trí, giá trị đúng.

> Nhắc lại Day 2: **DAG success ≠ data correct.** Task xanh chỉ nghĩa là không raise exception. Luôn verify bằng query thật.

### Test idempotency (nền tảng cho Day 6)

Chạy DAG lần thứ hai, rồi `count(*)` lại:
- Vẫn **5531** → UPSERT hoạt động, pipeline idempotent ✓
- Thành **11062** → `ON CONFLICT` không ăn, phải sửa trước khi sang Day 6

---

## 13. Ghi chú cho Day 4

- File `XAU_1d_data.csv` là **lịch sử từ 2004**, không phải dữ liệu mới mỗi ngày.
  → "Incremental theo ngày" sẽ phải **lọc từ file**, không phải đọc file mới.
- `transform(df, None, None)` hiện lấy hết. Day 4 thay `None` bằng `data_interval_start` / `data_interval_end`.
- `staging/raw.parquet` đang dùng **tên cố định** → các run khác nhau ghi đè nhau. Day 4 phải thêm ngày vào tên file.
- `XAU_1m_data.csv` nặng **348MB** — vô ý `pd.read_csv` file này trong task sẽ ngốn RAM container, có thể bị OOM kill (log Airflow hiện rất khó hiểu khi đó).

---

## 14. Tự kiểm tra

- [ ] 4 chỗ gãy khi migrate script → DAG là gì?
- [ ] Vì sao retry nên là của Airflow chứ không phải tenacity?
- [ ] `get_conn()` có nhận tham số không? Vì sao?
- [ ] Vì sao không dùng `df.values` để build rows?
- [ ] `execute_values` khác `executemany` thế nào?
- [ ] Tại sao ghi file trung gian vào `/tmp` là sai?
- [ ] Grain của `gold_price_daily` là gì? Dùng file `1h` thì hỏng ra sao?