# Local vs Cloud — Week 13 Day 6

Nối cloud vào pipeline Airflow: `dbt_build >> export_marts >> upload_to_lake`
Ngày: 2026-11-05

---

## 1. Kiến trúc sau Day 6

```
CSV Olist
   │  scripts/load_raw.py                    ← Airflow: etl_daily (2h)
   ▼
raw.{orders, order_items, customers, products, order_payments}
   │  ════════ RANH GIỚI EL | T: source() ════════
   │  dbt build                              ← Airflow: dbt_daily task 1 (3h)
   ▼
analytics_marts.{fct_orders, dim_customers, dim_products}   [Postgres de_week9]
   │  export_marts.py --run-date {{ ds }}    ← Airflow: dbt_daily task 2
   ▼
week_13/export/marts/...parquet              [filesystem container]
   │  upload_to_lake.py --run-date {{ ds }}  ← Airflow: dbt_daily task 3
   ▼
s3://de-marts/marts/...                      [MinIO — thay cho GCS ở Track B]
```

**Vì sao export nằm trong `dbt_daily`, không tạo DAG thứ ba:** export là bước *sau* transform, phụ thuộc trực tiếp vào mart vừa build xong. Tách DAG riêng thì phải đồng bộ bằng lệch giờ hoặc sensor — thêm điểm hỏng mà không được gì.

---

## 2. Credential vào container — ba cách, một cách đúng

| Cách | Vấn đề |
|---|---|
| `COPY key.json` trong Dockerfile | Key nằm trong **image layer vĩnh viễn**. Push image lên registry = phát tán key. Xoá ở layer sau cũng không gỡ được khỏi layer trước. |
| Dán nội dung key vào Airflow Variable | Lộ trong UI, trong log, trong export metadata DB |
| **Mount file từ host + env trỏ tới** | Key không vào image, không vào git, không vào log |

```yaml
# x-airflow-common
volumes:
  - /home/binh/.gcp:/opt/airflow/.gcp:ro     # :ro — task chỉ cần đọc
environment:
  GOOGLE_APPLICATION_CREDENTIALS: /opt/airflow/.gcp/de-pipeline.json
```

**Set env thôi là KHÔNG đủ.** Container có filesystem riêng — `/home/binh/` bên trong container là thư mục rỗng của container, không phải home trên host. Env chỉ **trỏ đường**, volume mount mới **mang file vào**. Và env phải trỏ đường dẫn *trong container*, không phải đường dẫn host.

Cùng nguyên lý với `minio-lake:9000` thay vì `localhost:9000` ở Day 3: **bên trong container là một thế giới riêng** — đường dẫn, hostname, port đều tính theo góc nhìn của container.

Ở production thật thì dùng Workload Identity (không có key file nào cả), nhưng đó là tối ưu, không phải kiến thức nền.

### Biến môi trường phải đặt trong anchor dùng chung

```yaml
x-airflow-common:
  environment:
    &airflow-common-env
    DWH_URL: 'postgresql+psycopg2://dwh:dwh@postgres-dwh:5432/de_week9'
    EXPORT_ROOT: /opt/airflow/week_13/export
    MINIO_ENDPOINT: http://minio-lake:9000
    MINIO_ACCESS_KEY: de-pipeline
    MINIO_SECRET_KEY: pipeline-secret-2026
    MINIO_BUCKET: de-marts
```

Đặt riêng cho từng service là bug tuần 12 (biến không lan qua anchor). Kiểm bằng:

```bash
docker exec airflow-airflow-worker-1 env | grep -E 'MINIO|DWH_URL|EXPORT_ROOT'
```

### Script đọc env, có default local

```python
DWH_URL  = os.environ.get("DWH_URL", "postgresql+psycopg2://dwh:dwh@localhost:5433/de_week9")
OUT_ROOT = Path(os.environ.get("EXPORT_ROOT", "/mnt/c/DE/week_13/export"))
```

Một script, hai môi trường: chạy tay từ WSL dùng default, chạy trong Airflow thì env ghi đè.

---

## 3. Logical date, không phải `now()`

Airflow truyền **logical date** — ngày mà lần chạy đó *đại diện*, không phải lúc nó thực sự chạy.

```python
bash_command=f"python {SCRIPTS}/export_marts.py --run-date {{{{ ds }}}}"
```

Bốn ngoặc nhọn vì f-string ăn mất một cặp → render ra `{{ ds }}` cho Jinja của Airflow.

**Bằng chứng từ log:**

```
Running command: ['/usr/bin/bash', '-c',
  'python /opt/airflow/week_13/scripts/export_marts.py --run-date 2018-01-15']
```

Chạy lệnh vào ngày 2026-11-05, ghi vào partition `dt=2018-01-15`. Nếu dùng `date.today()` thì backfill 5 ngày sẽ đè cả 5 vào cùng một chỗ.

Script đã nhận `--run-date` từ ngoài từ Day 3 → hôm nay chỉ việc nối. Thiết kế đúng từ đầu tiết kiệm một lần viết lại.

### Timestamp trên lake = audit trail

```
[2026-11-05 12:56] marts/fct_orders/dt=2018-01-15/part-000.parquet   ← task hôm nay
[2026-10-29 15:21] marts/fct_orders/dt=2018-01-16/part-000.parquet   ← mc cp tuần trước
[2026-10-29 15:21] marts/fct_orders/dt=2018-01-17/part-000.parquet
[2026-11-05 12:56] marts/dim_customers/part-000.parquet              ← snapshot, luôn đẩy lại
```

Task chỉ đụng partition của logical date + dimension. Nếu `upload_to_lake.py` dùng `rglob("*.parquet")` (đẩy tất cả) thì cả 5 object đều mang timestamp hôm nay → mất khả năng biết cái nào thực sự mới.

Ba lý do lọc theo `run_date`:
1. **Tiết kiệm** — 600 partition × 365 lần/năm = 219.000 operation thừa. Trên GCS là tiền thật (class A).
2. **Ngữ nghĩa** — task tên "upload cho ngày X" không nên đụng dữ liệu ngày khác. Một partition cũ hỏng trên đĩa sẽ lặng lẽ lan lên lake.
3. **Audit** — timestamp trung thực.

```python
def iter_files(run_date: date):
    root = EXPORT_ROOT / "marts"
    yield from root.glob(f"*/dt={run_date:%Y-%m-%d}/*.parquet")   # partition đúng ngày
    yield from root.glob("*/part-*.parquet")                      # dimension: snapshot
```

### Fact bất biến, dimension là trạng thái hiện tại

| | Fact | Dimension |
|---|---|---|
| Bản chất | đơn hàng ngày 15/01 **đã xảy ra**, không đổi | khách đổi địa chỉ, sản phẩm đổi giá |
| Đẩy lại | lãng phí thuần tuý | bắt buộc — lake phải phản ánh trạng thái mới nhất |
| Layout | `dt=YYYY-MM-DD/` | không có `dt=`, chỉ một bản |

Khi cần giữ lịch sử thay đổi của dimension thì dùng SCD Type 2 (T6) — lúc đó dimension cũng thành bất biến và không cần đẩy lại.

---

## 4. Bẫy đã gặp Day 6

### botocore từ chối hostname có dấu gạch dưới

```
ValueError: Invalid endpoint: http://minio_lake:9000
```

botocore validate theo chuẩn DNS, RFC không cho `_` trong hostname. Docker thì cho. Hai chuẩn khác nhau, botocore nghiêm hơn.

Giải bằng **network alias** (sửa gốc, không đụng code):

```yaml
# week_8/minio_demo/docker-compose.yml
services:
  minio:
    container_name: minio_lake
    networks:
      default:
        aliases:
          - minio-lake      # gạch ngang
```

Hai cách còn lại đều tệ hơn: dùng IP (`172.20.0.2`) thì đổi khi restart; đổi `container_name` thì phải sửa mọi chỗ đã tham chiếu.

### Khối `networks:` đặt sai thụt lề cắt đứt YAML anchor

```
validating docker-compose.yaml: networks.depends_on additional properties
'postgres', 'redis' not allowed
```

Khối `networks:` top-level (không thụt lề) bị đặt **giữa** `x-airflow-common`, khiến `depends_on` phía dưới trở thành con của nó.

**Thụt lề LÀ cấu trúc.** Dòng không thụt lề = khối top-level mới, mọi thứ phía dưới thuộc về nó. Đặt sai một dòng là đổi cả cây.

Đúng:

```yaml
x-airflow-common:
  volumes:
    - ...
  networks:          # thụt 2 space — thuộc x-airflow-common
    - default
    - lake
  user: "..."
  depends_on: ...

# ...cuối file, không thụt lề:
networks:
  default:
    name: airflow_default
  lake:
    external: true
    name: minio_demo_default
```

Luôn kiểm trước khi restart:

```bash
docker compose config > /dev/null && echo "YAML OK"
```

### Nối hai network

Airflow ở `airflow_default`, MinIO ở `minio_demo_default` — mặc định **không thấy nhau**. Khai `lake` là network `external` rồi gắn vào `x-airflow-common`.

Kiểm (image Airflow không có `ping`):

```bash
docker exec airflow-airflow-worker-1 python -c "
import socket; print(socket.gethostbyname('minio-lake'))"
```

### `airflow dags test` không sinh task instance (Airflow 3.3)

`dags test` báo `success` ngay lập tức, log không có task nào, `tasks states-for-dag-run` trả `No data found`.

Đã loại trừ: hàm lồng (`tasks list` ra đủ 3 task), DAG paused (`No paused DAGs were found`), nhiều bản serialize (`find` chỉ ra 1 file, `dags details` chỉ 1 bundle).

→ Hành vi của công cụ `dags test` trong phiên bản này, không phải lỗi DAG. **Dùng `tasks test` để kiểm từng task** — nó render template thật và in log trực tiếp:

```bash
docker exec airflow-airflow-scheduler-1 airflow tasks test dbt_daily export_marts 2018-01-15
```

Điểm mở, chưa truy tiếp vì không chặn công việc.

---

## 5. MinIO vs GCS

| | MinIO (local) | GCS |
|---|---|---|
| API | S3 | GCS API + lớp tương thích S3 |
| Mô hình | bucket → object → policy | giống hệt |
| IAM | policy riêng kiểu AWS (`Effect`/`Action`/`Resource`) | gắn vào IAM toàn cục của Google |
| Phân quyền | `mc admin user add` + `mc admin policy attach` | service account + role binding |
| Chi phí | miễn phí (máy mình) | storage + **operation** + **egress** |
| Độ bền | một container, một volume | 11 số 9, replicate đa vùng |
| Dùng khi | học, CI, on-prem | production |

**Code gần như không đổi** — `boto3` nói chuyện với cả hai, chỉ khác `endpoint_url` và credential. Đó là giá trị thật của chuẩn S3: đổi backend không phải viết lại pipeline.

Khác biệt lớn nhất không nằm ở API mà ở **mô hình chi phí**: trên MinIO upload 1000 lần cũng không mất gì, trên GCS mỗi `PutObject` là một class A operation có giá.

---

## 6. Điểm mở

- **Credential GCP chưa test được** — Track B không có GCS (billing chưa `OPEN`). Volume mount `/home/binh/.gcp:/opt/airflow/.gcp:ro` đã chuẩn bị sẵn; khi billing thông thì đổi `upload_to_lake.py` từ `boto3` sang `google-cloud-storage`, phần còn lại của DAG giữ nguyên.
- **`dags test` không sinh task instance** — xem mục 4.
- **Chưa có retry/alert cho task upload.** Hiện dùng `default_args` chung (`retries: 1`). Task mạng nên có backoff riêng và cảnh báo khi fail — việc của T14 (data quality) hoặc khi lên production.

---

## 7. Lệnh kiểm tra tái dùng

```bash
# Env có lan tới worker không
docker exec airflow-airflow-worker-1 env | grep -E 'MINIO|DWH_URL|EXPORT_ROOT'

# Worker có thấy MinIO không
docker exec airflow-airflow-worker-1 python -c "
import socket; print(socket.gethostbyname('minio-lake'))"

# YAML hợp lệ chưa (TRƯỚC khi restart)
docker compose config > /dev/null && echo "YAML OK"

# DAG parse sạch chưa
docker exec airflow-airflow-scheduler-1 airflow dags list-import-errors

# Task có đăng ký đủ không
docker exec airflow-airflow-scheduler-1 airflow tasks list dbt_daily

# Chạy thử một task với logical date thật
docker exec airflow-airflow-scheduler-1 airflow tasks test dbt_daily export_marts 2018-01-15

# Xem object trên lake
docker exec minio_lake sh -c '
mc alias set lake http://localhost:9000 minioadmin minioadmin123 >/dev/null &&
mc ls --recursive lake/de-marts'
```