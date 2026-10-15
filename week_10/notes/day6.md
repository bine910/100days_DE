# Day 6 — Format comparison + Schema evolution

> Ngày lý thuyết + một thí nghiệm ngắn phát hiện ra hành vi nguy hiểm nhất của Parquet.

Bảng so sánh đầy đủ CSV/JSON/Parquet/Avro/ORC/Arrow nằm ở `format_comparison.md`. Note này ghi phần schema evolution và những điểm cần nhớ của Block 1.

---

## 1. Ba điểm quan trọng nhất từ bảng so sánh

### Splittable — và cạm bẫy CSV + gzip

**Splittable = chia file thành nhiều mảnh độc lập, mỗi máy xử lý một mảnh mà không cần hỏi máy khác.** Điều kiện bắt buộc để Spark xử lý song song.

| Format | Splittable nhờ đâu |
|---|---|
| Parquet | **Row group** (note Day 1) |
| ORC | Stripe |
| Avro | Sync marker |
| CSV | Ký tự xuống dòng |
| JSON | Không — object lồng nhau, không biết cắt ở đâu |

> **CSV nén gzip thì KHÔNG splittable.** gzip phải giải nén tuần tự từ byte đầu. Team nén CSV để tiết kiệm dung lượng → Spark chỉ dùng được 1 core mỗi file. Parquet nén **theo từng page bên trong** nên vẫn splittable — đây là lý do nên dùng Parquet thay vì "CSV + gzip".

### Arrow không phải file format

Nén và splittable là thuộc tính của *cách lưu trên disk*; Arrow là *cách bố trí dữ liệu columnar trong RAM*. Hai cột đó **N/A**.

Luồng thực tế: `Parquet trên disk → đọc + giải nén → Arrow table trong RAM → pandas DataFrame`. PyArrow dùng cả tuần chính là nó.

### Parquet vs Avro — vì sao Avro hợp streaming

Parquet ghi theo trình tự: gom ~1 triệu dòng trong RAM → nén thành row group → ghi disk → ... → **ghi footer** → đóng file. Footer chỉ ghi được khi biết hết mọi row group. **File chưa có footer thì chưa đọc được gì.**

Áp vào Kafka (bản ghi đến từng cái một), hai lựa chọn đều tệ:

| Cách làm | Hậu quả |
|---|---|
| Mỗi bản ghi → 1 file Parquet | Footer vài KB cho 1 dòng; hàng triệu file tí hon → small files problem (note Day 4) |
| Gom 1 triệu dòng rồi ghi | Giữ RAM 10 phút; process chết là mất sạch; consumer không đọc được gì trong lúc chờ |

Avro: row-based, schema ở **đầu file**, mỗi bản ghi tự chứa đầy đủ. Ghi xong là nằm trên disk ngay, đọc được ngay.

> **Parquet** tối ưu cho *ghi một lần, đọc nhiều lần, đọc theo cột*.
> **Avro** tối ưu cho *ghi liên tục từng bản ghi, đọc nguyên dòng*.

Kiến trúc thật dùng cả hai: `Kafka (Avro) → streaming ingest → gom theo giờ → Parquet trên data lake`.

---

## 2. Schema evolution — thí nghiệm

**Tình huống:** bronze có 7 cột. Nguồn thêm cột `discount` ở một partition mới.

```python
df = pd.read_csv(CSV)
df["discount"] = 0.15
ingest_to_bronze(tmp, "order_items", fs, bucket, date(2026, 11, 15))

out = pd.read_parquet(root, filesystem=fs)
print(out.shape)
```

### Kết quả

```
(450600, 8)              ← 450.600 dòng = 112.650 × 4 partition, đọc THÀNH CÔNG
KeyError: 'discount'     ← nhưng không có cột discount
```

Schema thực tế đọc được:
```
order_id, order_item_id, product_id, seller_id,
shipping_limit_date, price, freight_value, ingestion_date
```

**7 cột gốc + `ingestion_date`. Cột `discount` biến mất — không lỗi, không cảnh báo.**

### Vì sao

PyArrow đọc dataset nhiều file phải quyết định dùng schema nào. Mặc định nó lấy schema từ **file đầu tiên gặp** (partition `2026-10-05`, 7 cột) rồi áp cho tất cả. Cột không có trong schema đó bị bỏ qua im lặng.

Lý do thiết kế: quét schema của mọi file rất tốn thời gian khi dataset có hàng nghìn file.

**`ds.dataset()` mặc định cũng vậy** — nó cũng chỉ đọc file đầu tiên, không tự hợp nhất.

### Cách lấy đủ cột

```python
import pyarrow as pa
import pyarrow.dataset as ds

fragments = ds.dataset(root, filesystem=fs, format="parquet",
                       partitioning="hive").get_fragments()
unified = pa.unify_schemas([f.physical_schema for f in fragments])

dataset = ds.dataset(root, filesystem=fs, format="parquet",
                     partitioning="hive", schema=unified)
out = dataset.to_table().to_pandas()
print(out.groupby("ingestion_date")["discount"].apply(lambda s: s.isna().mean()))
```

Kết quả: `0.75` — đúng 3/4 partition không có `discount` nên toàn NaN.

### So sánh

| Cách đọc | Số cột | `discount` |
|---|---|---|
| `pd.read_parquet()` | 8 | **biến mất im lặng** |
| `unify_schemas` + `ds.dataset()` | 9 | có, NaN ở partition cũ (0.75) |

---

## 3. Bài học chính

> **Parquet KHÔNG tự động hợp nhất schema. Cột mới bị bỏ im lặng — không lỗi, không cảnh báo.**

Đây là loại lỗi tệ nhất trong DE: pipeline chạy xanh, dashboard vẫn ra số, chỉ là thiếu cột. Phát hiện ra thì đã mất vài tuần dữ liệu. Nguy hiểm hơn hẳn lỗi nổ ngay — lỗi nổ thì biết mà sửa.

### Ba cách xử lý

| Cách | Khi nào |
|---|---|
| Khai báo schema cố định, validate lúc ghi | Pipeline nhỏ, schema ít đổi — **fail sớm còn hơn mất dữ liệu ngầm** |
| `unify_schemas` lúc đọc | Chấp nhận schema đổi, nhưng tốn chi phí quét mọi file |
| **Table format (Iceberg / Delta Lake)** | Giải pháp thật — giữ schema ở tầng metadata riêng, schema evolution có kiểm soát |

### Vì sao Iceberg / Delta Lake tồn tại

**Parquet là file format — nó chỉ biết về một file.** Quản lý một tập hợp file như một bảng (schema thống nhất, version, transaction, time travel) là việc của **table format** ở tầng trên.

Lộ trình để Iceberg/Delta ở mức overview. Giờ đã biết chúng giải quyết vấn đề gì, với bằng chứng là lỗi vừa gặp.

---

## 4. Kịch bản chưa thử

- **Xoá cột** ở partition mới
- **Đổi kiểu dữ liệu** (`price` double → string) — cái này cho `ArrowInvalid` rõ ràng chứ không im lặng, nên **ít nguy hiểm hơn** thêm cột

---

## 5. Bẫy kỹ thuật

- **`pa.schema()` cần tên + kiểu**, không chỉ tên: `pa.schema([("order_id", pa.large_string()), ("price", pa.float64())])`. Schema Parquet luôn gồm cả hai — điểm phân biệt với CSV.
- **MinIO tắt khi đóng Docker Desktop / restart máy.** Phải `docker compose up -d` ở thư mục week_8 trước mỗi buổi. T11 nên thêm `restart: unless-stopped` vào docker-compose.
- **Dọn partition test sau khi thử nghiệm**, không để rác trong bronze:
  ```python
  fs.rm(f"{bucket}/bronze/order_items/ingestion_date=2026-11-15", recursive=True)
  ```
- **File tạm nên ghi vào `week10/data/`**, không ghi vào thư mục dataset gốc của week_4.

---

## 6. Việc cho Day 7

- [ ] Chạy end-to-end: `bronze_ingest.py --date X` → script T9 `--date X` → chạy lại kiểm tra PostgreSQL không duplicate
- [ ] Chuyển credentials hardcode trong code T9 sang `.env`
- [ ] Hoàn thiện báo cáo tuần, chốt Definition of Done
- [ ] Trả lời 5 câu tự kiểm tra
- [ ] Đọc lướt Airflow concepts (DAG, scheduler) cho T11