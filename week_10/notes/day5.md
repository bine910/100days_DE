# Day 5 — Bronze layer trên MinIO: Parquet + partition + idempotency

> Ngày đầu tiên chuyển từ đo đạc sang dựng thật. Kết quả: pipeline T9 có thêm một điểm dừng bất biến, chạy lại bao nhiêu lần cũng ra cùng kết quả.

---

## 1. Kiến trúc: trước và sau

**Trước (T9):**
```
CSV → transform → PostgreSQL
```

**Sau (Day 5):**
```
CSV → bronze (Parquet + zstd, MinIO)  →  transform  →  PostgreSQL
          ↑ điểm dừng bất biến
```

### Vì sao cần bronze

Transform có bug mà không có bronze → phải xin lại dữ liệu từ nguồn, mà nguồn có thể đã đổi. Có bronze → đọc lại từ MinIO, sửa code, chạy lại.

**Nguyên tắc quan trọng nhất: bronze giữ NGUYÊN TRẠNG.** Không clean, không ép dtype, không lọc. Chỉ thêm cột `ingestion_date`.

Điều này ngược với thói quen fullstack (validate ngay ở input). Lý do ở DE: bronze là bản sao của *"nguồn đã cho ta cái gì"*; ép dtype là **diễn giải**, và diễn giải có thể sai. Mọi thứ học ở Day 2 về ép dtype áp dụng ở **silver**, không phải bronze.

---

## 2. Kết nối MinIO qua s3fs

```python
def make_fs() -> s3fs.S3FileSystem:
    """Tạo kết nối tới MinIO từ biến môi trường."""
    key = os.getenv("MINIO_ACCESS_KEY")
    secret = os.getenv("MINIO_SECRET_KEY")
    endpoint = os.getenv("MINIO_ENDPOINT")
    if not all([key, secret, endpoint]):
        raise RuntimeError("Thiếu biến MinIO trong .env — xem .env.example")
    return s3fs.S3FileSystem(
        key=key, secret=secret,
        client_kwargs={"endpoint_url": endpoint},
    )
```

MinIO nói giao thức S3 → mọi thư viện S3 đều dùng được. Đổi sang AWS S3 thật chỉ cần đổi endpoint.

**Vì sao gói vào hàm thay vì khởi tạo ở top-level:** top-level thì mọi lần `import` module đều mở kết nối MinIO — script khác chỉ muốn `from bronze_ingest import ingest_to_bronze` cũng bị ép kết nối, MinIO tắt là import chết. (Cùng bài học "import thực thi cả file" ở Day 2.)

**Fail sớm, fail rõ ràng:** `if not all([...])` để script trong Airflow (T11) báo ngay "thiếu biến gì", không quăng traceback 80 dòng về aiohttp.

---

## 3. Ghi bronze có partition

```python
def ingest_to_bronze(
    csv_path: Path,
    table: str,
    fs: s3fs.S3FileSystem,
    bucket: str,
    ingestion_date: date | None = None,
) -> str:
    ingestion_date = ingestion_date or date.today()

    df = pd.read_csv(csv_path)                    # KHÔNG clean, KHÔNG ép dtype
    df["ingestion_date"] = ingestion_date.isoformat()

    root = f"{bucket}/bronze/{table}"
    pq.write_to_dataset(
        pa.Table.from_pandas(df, preserve_index=False),
        root_path=root,
        filesystem=fs,
        partition_cols=["ingestion_date"],
        compression="zstd",
        existing_data_behavior="delete_matching",
    )
    return root
```

Cấu trúc sinh ra trên MinIO:
```
datalake/bronze/order_items/ingestion_date=2026-10-07/9b6e45136eec40c2abee9167e0cf727d-0.parquet
```

**Tên file có hash ngẫu nhiên** — PyArrow sinh ra để nhiều writer ghi song song không đè lên nhau. Đây chính là lý do cần `delete_matching`: không thể dựa vào tên file để ghi đè.

### `existing_data_behavior` — chìa khoá idempotency

| Giá trị | Hành vi |
|---|---|
| `"overwrite_or_ignore"` (mặc định) | ghi thêm → **duplicate** |
| `"error"` | báo lỗi nếu partition đã có |
| **`"delete_matching"`** | **xoá partition trùng, giữ nguyên partition khác** |

### `--date` truyền từ ngoài

```python
ap.add_argument("--date", type=date.fromisoformat, default=None,
                help="ingestion_date (YYYY-MM-DD), mặc định hôm nay")
```

Tham số quan trọng nhất của script. Cần nó để test idempotency hôm nay, và T11 Airflow sẽ truyền `{{ ds }}` vào đây để backfill ngày quá khứ.

`type=date.fromisoformat` — argparse tự convert và tự báo lỗi nếu sai định dạng, không cần validate tay.

---

## 4. Kiểm chứng idempotency

### Test 1 — chạy lại cùng ngày

```
lần 1: ingestion_date=2026-10-07/4d6b0f0a...-0.parquet
lần 2: ingestion_date=2026-10-07/73ff492f...-0.parquet
```
Hash đổi, vẫn **1 file**. File cũ bị xoá, file mới ghi vào. Không duplicate.

### Test 2 — ghi ngày khác, không đụng ngày cũ

```
--date 2026-10-06  →  acbd2fea (10-06) + 73ff492f (10-07 GIỮ NGUYÊN)
--date 2026-10-05  →  3d2bf148 (10-05) + acbd2fea + 73ff492f
```

### Test 3 — ghi lại ngày ở giữa

```
--date 2026-10-06  →  3d2bf148 (10-05 nguyên)
                      7ec386a3 (10-06 ĐỔI)
                      73ff492f (10-07 nguyên)
```

### Xác nhận bằng số dòng — bước không được bỏ

```python
df = pd.read_parquet(root, filesystem=fs)
print(len(df))                             # 337950
print(df["ingestion_date"].value_counts())
```

```
2026-10-05    112650
2026-10-06    112650
2026-10-07    112650
```

**Đếm file chỉ chứng minh được một nửa.** Nếu `delete_matching` có vấn đề ngầm, nó lộ ở số dòng chứ không lộ ở `fs.find()`.

---

## 5. Đổi pipeline T9 đọc từ bronze

```python
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def extract_from_bronze(table: str, ingestion_date: date) -> pd.DataFrame:
    """Đọc một partition ngày từ bronze layer (Parquet)."""
    fs = make_fs()
    df = pd.read_parquet(
        f"{BUCKET}/bronze/{table}",
        filesystem=fs,
        filters=[("ingestion_date", "==", ingestion_date.isoformat())],
    )
    log.info(f"Extracted {len(df)} rows from bronze/{table} @ {ingestion_date}")
    return df
```

So với `extract_from_minio()` cũ (boto3 + `get_object` + CSV):

| | Cũ | Mới |
|---|---|---|
| API | `s3.get_object(Bucket, Key)` — lấy MỘT object theo key chính xác | `read_parquet(dir, filters=...)` — mô tả *muốn gì*, không phải *lấy file nào* |
| Partition | không hiểu, phải tự ghép key | partition pruning tự động |
| Format | CSV + `sep=";"` — nguồn sai số | Parquet, schema trong file |
| Credentials | hardcode `minioadmin` trong code (đang commit vào git) | `.env` qua `make_fs()` |

`filters` ở đây chính là partition pruning đã đo ở Day 4 — chỉ đọc một thư mục, bỏ qua các thư mục khác.

**Và giờ mới ép dtype** (`parse_dates`, `category`) — ở bước transform/silver, không phải bronze.

---

## 6. Idempotency ở tầng PostgreSQL

Bronze đã idempotent, nhưng `df.to_sql(if_exists="append")` chạy 2 lần vẫn nhân đôi dữ liệu.

PostgreSQL **có** cơ chế chống trùng (`PRIMARY KEY`, `UNIQUE`, `ON CONFLICT DO NOTHING/UPDATE` — T5), nhưng chúng chỉ chạy nếu có khai báo ràng buộc. **Bảng tạo bởi `to_sql` không có constraint nào** — PostgreSQL không biết cột nào là khoá nên không phản đối gì.

### Giải pháp: delete-then-insert theo partition

```python
with engine.begin() as conn:                       # transaction
    conn.execute(
        text("DELETE FROM order_items WHERE ingestion_date = :d"),
        {"d": ingestion_date},
    )
    df.to_sql("order_items", conn, if_exists="append", index=False)
```

Đây chính xác là thứ `existing_data_behavior="delete_matching"` làm ở tầng Parquet, chỉ viết bằng SQL. **Cùng một tư duy ở hai tầng: đơn vị ghi lại là một partition, không phải một dòng.**

Hai chi tiết quyết định tính đúng đắn:
1. **`with engine.begin()`** mở transaction — DELETE và INSERT là một đơn vị. INSERT lỗi giữa chừng thì DELETE cũng rollback. Không có nó thì có thể rơi vào trạng thái "đã xoá, chưa chèn" → **mất dữ liệu**.
2. **Phải giữ cột `ingestion_date` trong bảng PostgreSQL** — đừng drop nó khi transform.

**`TRUNCATE` là sai** — nó xoá sạch mọi ngày; chạy lại ngày 10-06 là mất 10-05 và 10-07.

> **Quy tắc:** idempotency không phải tính chất của một bước, mà của **toàn chuỗi**. Bronze idempotent nhưng PostgreSQL append thì cả pipeline vẫn không idempotent. Mỗi bước phải tự lo phần của mình.

---

## 7. Bẫy kỹ thuật

**Đường dẫn object storage có hai cách viết — đừng trộn:**

```python
pd.read_parquet(root, filesystem=fs)                      # path trần + filesystem
pd.read_parquet(f"s3://{root}", storage_options={...})    # URI đầy đủ + storage_options
```

Trộn hai cách cho lỗi `ArrowInvalid: ... which is outside base dir 's3://...'` — thông báo không gợi ý gì về nguyên nhân thật. `fs.find()` trả path trần (`datalake/bronze/...`), nên dùng cách 1 cho nhất quán. Chuỗi `s3://` trong `print()` thì giữ — đó là text cho người đọc, không phải path truyền cho thư viện.

**Docker Compose volume gắn với thư mục dự án.** Tạo `docker-compose.yml` mới ở thư mục khác sẽ sinh volume mới → MinIO rỗng, tưởng mất dữ liệu. Luôn chạy lại stack cũ từ đúng thư mục T8.

**Biến môi trường viết HOA và có tiền tố:** `MINIO_ACCESS_KEY` chứ không phải `key`. T11 Airflow có hàng chục biến cùng chạy, tên chung chung sẽ đụng.

**`.env` vào `.gitignore`, kèm `.env.example`** liệt kê tên biến (không có giá trị thật) — quy trình T7.

---

## 8. Việc cho Day 6–7

- [ ] Chạy end-to-end: `bronze_ingest.py --date X` → script T9 `--date X` → kiểm tra PostgreSQL không duplicate khi chạy lại
- [ ] Viết `format_comparison.md`: CSV / JSON / Parquet / Avro / ORC (Avro, ORC, Arrow chỉ mức overview)
- [ ] Hoàn thiện báo cáo tuần, chốt Definition of Done
- [ ] Đọc lướt Airflow concepts (DAG, scheduler) cho T11