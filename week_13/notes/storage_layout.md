# Object storage layout — Week 13 Day 3

Stack: MinIO `minio_lake` (:9000 API, :9001 console) · bucket `de-marts`
Nguồn: `analytics_marts` trong `airflow-postgres-dwh-1` (user `dwh`, db `de_week9`, host port 5433)
Ngày: 2026-10-28

---

## 1. Object storage không có thư mục

`marts/fct_orders/dt=2026-10-28/part-000.parquet` là **một cái tên duy nhất** có dấu `/` bên trong. Không inode, không directory entry. Hệ quả:

- "Đổi tên folder" = copy toàn bộ object sang tên mới rồi xoá cái cũ. Không có `mv` rẻ như filesystem.
- `ls` một "folder" thực chất là **list toàn bộ bucket rồi lọc theo prefix** → bucket càng nhiều object càng chậm.
- `mc ls` hiển thị `0B marts/` như một thư mục — đó là **UI giả lập**, object đó không tồn tại. Muốn thấy object thật phải `--recursive`.

---

## 2. Layout đã chốt

```
marts/fct_orders/dt=2026-10-20/part-000.parquet   ← fact: partition theo NGÀY DỮ LIỆU
marts/fct_orders/dt=2026-10-28/part-000.parquet
marts/dim_customers/part-000.parquet              ← dimension: ghi đè, không partition
marts/dim_products/part-000.parquet
```

### Vì sao fact partition mà dimension không

`dim_customers` bị ghi đè toàn bộ mỗi lần chạy — nó chỉ có **một trạng thái hiện tại**. Nhét vào `dt=.../` thì mỗi ngày sinh một bản copy toàn bộ dimension: dữ liệu phình lên, mà engine vẫn luôn phải đọc partition mới nhất nên chẳng pruning được gì.

**Quy tắc: partition theo thứ dùng để LỌC.** Không ai query "khách hàng của ngày 28/10" — họ query "đơn hàng của ngày 28/10 rồi join sang khách hàng".

### Hive partitioning làm gì

`dt=2026-10-28/` là quy ước Hive. Engine đọc (BigQuery, Spark, DuckDB) nhìn **tên đường dẫn** để loại bỏ file không cần đọc **trước khi mở file nào** — partition pruning xảy ra ở tầng tên, không phải tầng nội dung.

Sai layout thì mất hẳn khả năng này: `fct_orders_2026-10-28.parquet` để phẳng trong một prefix buộc engine mở tất cả để biết file nào thuộc ngày nào.

---

## 3. Idempotency trong object storage

**Tên object phải là hàm của DỮ LIỆU, không phải của lần chạy.**

- `dt={run_date}/part-000.parquet` → chạy bao nhiêu lần cho ngày 28/10 cũng ghi đúng một tên, lần sau đè lần trước. ✓
- `part-{timestamp}.parquet` → mất idempotency dù layout nhìn vẫn đẹp: chạy 2 lần = 2 file cùng mô tả một ngày = đọc lên thành dữ liệu nhân đôi. ✗

Đây là cùng một bài toán đã giải bằng UPSERT ở T9 và `unique_key` ở T12, chỉ đổi chỗ chiến trường.

**Bằng chứng:** chạy `export_marts.py` 2 lần cùng ngày → `find` vẫn đúng 4 file, kích thước không đổi.

Hệ quả cho Day 6: `run_date` phải đến từ **bên ngoài** script (`--run-date`, Airflow truyền logical date), không phải `date.today()`. Backfill ngày 20/10 mà dùng `today()` sẽ ghi sai partition, và backfill 5 ngày sẽ đè cả 5 vào cùng một chỗ.

---

## 4. Ba khoản tiền của object storage (GCS lẫn S3)

| Khoản | Tính theo | Bẫy |
|---|---|---|
| Storage | GB × thời gian × storage class | Nearline/Coldline rẻ khi lưu nhưng **tính phí khi đọc** + phí xoá sớm |
| Operation | **Số request** — class A (ghi/list) đắt hơn class B (đọc) | 10.000 file nhỏ đắt hơn 1 file to cùng dung lượng |
| Egress | GB đi **ra khỏi** Google | Đọc từ laptop về là egress; BigQuery đọc cùng region thì không |

→ **Gộp partition, đừng sinh file vụn.** File Parquet lý tưởng 128MB–1GB. Olist nhỏ nên 1 file/partition là đủ.

---

## 5. Policy least privilege trên MinIO

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::de-marts",
        "arn:aws:s3:::de-marts/*"
      ]
    }
  ]
}
```

### Vì sao `Resource` cần hai dòng

| ARN | Dùng cho | Thiếu thì |
|---|---|---|
| `arn:aws:s3:::de-marts` | thao tác lên **chính bucket** (`ListBucket`) | `mc ls` fail dù `PutObject` chạy ngon |
| `arn:aws:s3:::de-marts/*` | thao tác lên **object bên trong** (`Get/PutObject`) | ghi/đọc file fail |

Đây là cùng cấu trúc "hai trục quyền" của BigQuery ở Day 2 (`jobUser` ở project + `dataEditor` ở dataset), chỉ khác cú pháp: một bên gán role lên resource, một bên viết policy liệt kê action + resource.

### Đối chiếu hai hệ

| BigQuery | Object storage |
|---|---|
| dataset `olist_marts` | bucket `de-marts` |
| binding `WRITER` trên dataset | policy cho phép ghi trên bucket đó |
| `Resource` giới hạn 1 dataset | `Resource` giới hạn 1 bucket, không phải `arn:aws:s3:::*` |

### Bằng chứng least privilege

| Test (user `de-pipeline`) | Kết quả |
|---|---|
| `mc ls pipe/de-marts` | được |
| `mc mb pipe/should-fail` | **Access Denied** |

---

## 6. Lệnh đã dùng

```bash
# Dựng lại stack (container mất, volume còn)
cd /mnt/c/DE/week_11/airflow && docker compose up -d
cd /mnt/c/DE/week_8/minio_demo && docker compose up -d

# Kiểm mart
docker exec -it airflow-postgres-dwh-1 psql -U dwh -d de_week9 -c "..."

# Export
python week_13/scripts/export_marts.py
python week_13/scripts/export_marts.py --run-date 2026-10-20

# Upload (mc chạy từ trong container MinIO)
docker cp /mnt/c/DE/week_13/export/marts minio_lake:/tmp/marts
docker exec -it minio_lake sh -c '
mc alias set lake http://localhost:9000 minioadmin minioadmin123 &&
mc mb --ignore-existing lake/de-marts &&
mc cp --recursive /tmp/marts/ lake/de-marts/marts/ &&
mc ls --recursive lake/de-marts'
```

---

## 7. Bẫy đã gặp Day 3

- **Container mất nhưng volume còn.** `docker compose down` (không `-v`) xoá container, giữ volume → `docker compose up -d` là mart quay về nguyên vẹn. `down -v` phải gõ có ý thức.
- **Đổi `OUT_ROOT` sau khi đã ghi** (`week13` → `week_13`) sinh cây mồ côi 27MB vẫn nằm trên đĩa. Trên cloud nó vẫn tính tiền cho tới khi có người nhớ ra → **layout phải chốt trước khi upload**.
- **`curl -o` ghi file cả khi server trả 410.** Binary `mc` lẽ ra ~25MB, tải về 405 bytes = một trang lỗi HTML. Dùng `curl -fL` để fail thẳng thay vì ghi rác ra đĩa. Cùng họ với `billingEnabled: false` — lệnh chạy xong ≠ việc đã xảy ra.
- **`apt install mc` là Midnight Commander**, không liên quan MinIO.
- **`~/.docker/config.json` có `credsStore: desktop.exe`** → mọi `docker pull` fail với `error getting credentials`. Sửa: `echo '{}' > ~/.docker/config.json` (backup trước; khôi phục khi cần `docker login` registry riêng).
- **`quay.io/minio/mc:latest` trả 401** — repo không có tag đó. Đường vòng: image MinIO server đang chạy đã có sẵn `mc` bên trong.
- **Trong container phải dùng hostname service** (`minio_lake:9000`), không phải `localhost` — service networking của T7.
- **`psql -U postgres` fail với `role does not exist`** — là cổng 7 (business logic), không phải cổng 3 (IAM). Compose khai user `dwh`.

---

## 8. Ghi chú mang sang Day 4+

- **`dim_customers` 99.441 dòng = bằng đúng `fct_orders`.** Olist sinh `customer_id` mới theo từng order, nên "số khách hàng" đếm trên `dim_customers` **không phải** số khách thật — phải dùng `customer_unique_id`. Nhớ trước khi làm dashboard T15.
- Credential MinIO: `minioadmin`/`minioadmin123` (root), `de-pipeline`/`pipeline-secret-2026` (pipeline, chỉ ghi được `de-marts`).
- Kích thước file: `fct_orders` 8.8MiB/partition, `dim_customers` 6.7MiB, `dim_products` 1.2MiB (Parquet + snappy).
- `week_13/export/` **không commit** — 27MB dữ liệu sinh ra, đã cho vào `.gitignore` cùng `*.parquet`.