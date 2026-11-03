# BigQuery — Week 13 Day 4

Dataset `bine910.olist_marts` (US, sandbox) · `fct_orders` 891 dòng (2018-01-15..17), `CLUSTER BY status`
Ngày: 2026-11-03

---

## 1. Columnar: vì sao "bytes scanned" mới có nghĩa

Postgres lưu cả dòng liền nhau trên disk page. BigQuery (và Parquet) lưu **từng cột một chỗ**. Nên:

- `SELECT order_id` chỉ đọc đúng cột đó, các cột khác không bị chạm tới
- `SELECT *` đọc tất cả → đắt gấp N lần
- Cùng một bảng, cùng trả về 10 dòng, hai query chênh nhau hàng trăm lần tiền

Trên Postgres không bao giờ phải nghĩ, vì CPU là của mình.

### Số đo thật (dry_run, bảng 891 dòng)

| Query | Bytes | Nhận xét |
|---|---|---|
| `SELECT *` | 120.085 | mọi cột |
| `SELECT order_id` | 30.294 | **25%** — một cột string chiếm 1/4 bảng |
| `SELECT *` + `LIMIT 10` | **120.085** | y hệt câu 1 |
| `order_id` + `WHERE status` | 40.087 | = 30.294 + 9.793 (cột `status`) |
| `count(*)` | **0** | trả lời từ metadata |

Ba điều rút ra:

- **`LIMIT` không giảm một byte nào.** Scan hết rồi mới cắt. Hiểu lầm phổ biến nhất của người mới.
- **`WHERE` không tốn gì; đọc thêm CỘT mới tốn.** Chênh lệch 40.087 − 30.294 = 9.793 đúng bằng kích thước cột `status`.
- **`count(*)` miễn phí.** Postgres phải quét bảng, BigQuery đọc metadata. Một khác biệt kiến trúc gói trong một con số.

Bytes tính theo **kích thước thật của cột**, không theo số lượng cột: một `timestamp` (8 byte/dòng) và một `string` 32 ký tự chênh nhau 4 lần.

`dry_run` luôn báo **upper bound**. Clustering có thể làm bytes thật thấp hơn, nhưng không dự đoán trước được.

---

## 2. processed ≠ billed — sàn 10 MB

| processed | billed | tỉ lệ |
|---|---|---|
| 40.087 | 10.485.760 | **×262** |
| 7.128 | 10.485.760 | ×1.471 |
| 10.485.760 | 10.485.760 | ×1 (INFORMATION_SCHEMA) |
| 0 | 0 | — (`count(*)`) |

**Mỗi query có sàn tối thiểu 10 MB.** Bảng 120KB không bao giờ chạm sàn → mọi query tính như nhau.

Hai kết luận trái chiều, giữ cả hai:

- **Bảng nhỏ:** tối ưu cột vô nghĩa về tiền. Thứ đắt là **số lượng query**. Dashboard refresh 50 widget mỗi 5 phút đốt tiền dù dữ liệu tí hon.
- **Bảng lớn (GB+):** sàn 10MB không còn ý nghĩa, column/partition pruning quyết định hoá đơn.

Biết mình đang ở chế độ nào quan trọng hơn thuộc lòng kỹ thuật tối ưu.

---

## 3. Ba cách giảm bytes

| Kỹ thuật | Giảm gì | Bật thế nào |
|---|---|---|
| Column pruning | bỏ cột không cần | viết tên cột thay vì `*` |
| Partition pruning | bỏ **cả block** | `PARTITION BY` + filter đúng cột partition |
| Clustering | sắp xếp trong partition | `CLUSTER BY` — giảm bytes thật nhưng **dry_run không thấy** |

### Cột partition phải đứng trần

```sql
WHERE EXTRACT(YEAR FROM purchased_at) = 2018   -- scan toàn bảng
WHERE purchased_at >= '2018-01-01'
  AND purchased_at <  '2019-01-01'             -- pruning
```

BigQuery loại partition **trước khi đọc dữ liệu**, chỉ dựa vào metadata. Bọc cột trong hàm thì engine không biết nó tương đương khoảng nào → đọc hết rồi mới tính.

Cùng nguyên lý "bọc cột trong hàm là mất index" của T2, khác engine.

---

## 4. Native vs external table

| | Native | External |
|---|---|---|
| Dữ liệu ở | storage BigQuery | file trên GCS/S3 |
| Statistics, cache | có | **không** — mỗi query scan lại từ đầu |
| Partition | `PARTITION BY` thật | dựa Hive path `dt=.../` |
| Dùng khi | bảng query thường xuyên | data lake, file đổi liên tục |

External tiết kiệm **storage + bước copy**, đánh đổi **tốc độ + khả năng tối ưu**.
Layout Hive của Day 3 đã đúng chuẩn — có billing thì chỉ việc trỏ vào, không sửa gì.

---

## 5. Ba lỗi của Day 4 — cùng một hình dạng

### 5.1 Grain sai: partition không lọc dữ liệu

`run_date` chỉ dùng để **đặt tên thư mục**, câu SQL vẫn `SELECT *` không điều kiện → mọi partition chứa toàn bộ 99.441 dòng. Nạp 2 partition = 198.882 dòng, mỗi đơn đếm 2 lần.

Script chạy xanh, layout đúng chuẩn, test idempotency Day 3 vẫn pass — **mà dữ liệu sai**.

Sửa: `WHERE purchased_at >= :d_from AND < :d_to`, `TABLES` đổi từ `True/False` sang **tên cột ngày**. Kết quả: 307 / 302 / 282 thay vì 99.441 × 3.

> Grain của partition `dt=X` phải là *những dòng thuộc về ngày X*, không phải *ảnh chụp toàn bảng tại ngày X*.

**Snapshot vs incremental** — phải chọn có ý thức:

| | Snapshot | Incremental |
|---|---|---|
| Partition chứa | toàn bộ bảng tại thời điểm đó | chỉ dòng thuộc ngày đó |
| Đọc nhiều partition | **nhân bản** | cộng dồn đúng |
| Hợp với | dimension nhỏ cần lịch sử | fact |

Khác biệt này hiện ra thành một flag: `--replace` ở dimension, không có ở fact.

### 5.2 Schema drift từ pandas

`bq load` ngày 17 bị từ chối: *`item_count` has changed type from FLOAT to INTEGER`*.

Nguyên nhân **không ở BigQuery mà ở pandas**: numpy `int64` không biểu diễn được NULL. Ngày 15 có 2 NULL, ngày 16 có 1 → pandas âm thầm nâng cột thành `float64`. Ngày 17 không NULL → giữ `int64`. Cùng bảng nguồn, 3 file, 2 schema.

Sửa: `dtype_backend="pyarrow"` trong `read_sql` — kiểu Arrow có null thật.

```python
df = pd.read_sql(text(sql), conn, params=..., dtype_backend="pyarrow")
```

Kiểm trước khi nạp (data contract thô sơ, T14 sẽ làm bài bản):

```bash
python -c "
import pyarrow.parquet as pq, glob
for f in sorted(glob.glob('week_13/export/marts/fct_orders/*/*.parquet')):
    s = pq.read_schema(f)
    print(f.split('/')[-2], s.field('item_count').type, s.field('payment_count').type)
"
```

> Loại bug chỉ nổ khi **dữ liệu** thay đổi, không phải khi code thay đổi. Ở production nó nổ lúc 3h sáng.

### 5.3 Dữ liệu biến mất, không báo lỗi

5 job `bq load` đều `DONE`, job cuối khai `outputRows: 282`, `badRecords: 0`. Nhưng bảng `numRows: 0`, và `lastModifiedTime` **bằng đúng** `creationTime` → bảng chưa từng thay đổi.

Thủ phạm: `expirationMs: 5184000000` (60 ngày). **Partition expiration tính theo ngày CỦA PARTITION, không phải ngày nạp.** Partition `2018-01-15` quá hạn 8 năm trước khi bấm load → BigQuery nhận dữ liệu, tạo partition, thấy hết hạn, xoá luôn. Không lỗi, vì về kỹ thuật mọi thứ đúng.

Xác nhận: `INFORMATION_SCHEMA.PARTITIONS` rỗng.
Thử gỡ: `Partition expiration time must be less than 60 days while in sandbox mode`.

→ Sandbox + dữ liệu lịch sử + partition theo ngày = không đội trời chung.
→ Giải pháp: nạp bảng **không partition**, giữ `CLUSTER BY status`. Day 5 tạo bảng thứ hai với ngày dịch về gần hiện tại để đo pruning.

Kể cả ở project có billing: đặt expiration 90 ngày trên bảng chứa dữ liệu lịch sử là **mất dữ liệu ngay khi load, im lặng**.

---

## 6. Sợi chỉ xuyên suốt tuần

Ba lần, cùng một hình dạng: **lệnh chạy xong ≠ việc đã xảy ra.**

| Ngày | Triệu chứng | Field cần đọc |
|---|---|---|
| Day 1 | `billing projects link` không lỗi | `billingEnabled: false` |
| Day 3 | `curl -o` tải về 405 bytes | kích thước file (binary ~25MB) |
| Day 4 | 5 job `DONE` | `outputRows` vs `numRows`, `lastModifiedTime` vs `creationTime` |

Cách đọc đúng giống nhau cả ba lần: **đừng tin exit code, đọc field trong output.** Kỹ năng này không có trong tutorial nào.

Đối lập: lỗi `Source file not found` (đứng sai thư mục) là lỗi **ồn ào** — dễ. Lỗi im lặng mới đắt.

---

## 7. Lệnh đã dùng

```bash
# Nạp fact (không partition — sandbox không cho dữ liệu lịch sử)
cd /mnt/c/DE/week_13/export/marts/fct_orders
bq load --source_format=PARQUET --clustering_fields=status \
  bine910:olist_marts.fct_orders 'dt=2018-01-15/part-000.parquet'
bq load --source_format=PARQUET bine910:olist_marts.fct_orders 'dt=2018-01-16/part-000.parquet'
bq load --source_format=PARQUET bine910:olist_marts.fct_orders 'dt=2018-01-17/part-000.parquet'

# Nạp dimension (--replace = snapshot, ghi đè)
cd /mnt/c/DE/week_13/export/marts
bq load --source_format=PARQUET --replace bine910:olist_marts.dim_customers dim_customers/part-000.parquet
bq load --source_format=PARQUET --replace bine910:olist_marts.dim_products  dim_products/part-000.parquet

# Kiểm
bq ls bine910:olist_marts
bq show --format=prettyjson bine910:olist_marts.fct_orders | head -20
bq query --dry_run --use_legacy_sql=false '<query>'
```

`bq load` tự đọc schema từ Parquet, không cần khai tay.

---

## 8. Trạng thái cuối Day 4

| Bảng | Dòng | Ghi chú |
|---|---|---|
| `fct_orders` | 891 | 3 ngày 2018-01-15..17, CLUSTER BY status, **không** partition |
| `dim_customers` | 99.441 | snapshot |
| `dim_products` | 32.951 | snapshot |

Nhớ: dataset có `defaultTableExpirationMs` 60 ngày → mọi bảng tự biến mất khoảng **02/01/2027**. Không phải lỗi.

Cú pháp: `bq` dùng `project:dataset.table` (hai chấm), SQL dùng `` `project.dataset.table` `` (dấu chấm, trong backtick).