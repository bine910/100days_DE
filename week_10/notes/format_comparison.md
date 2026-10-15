# So sánh file format cho Data Engineering

> Tuần 10 — Day 6. CSV và Parquet đã đo thực nghiệm (xem `format_benchmark.md`); Avro, ORC, Arrow ở mức overview.

---

## Bảng tổng hợp

| Format | Row/Column | Có schema? | Nén | Splittable | Dùng khi |
|---|---|---|---|---|---|
| **CSV** | Row | ❌ Không | ❌ Không mặc định | ✅ Cắt ở newline — **nhưng mất nếu nén gzip** | Trao đổi dữ liệu đơn giản, người đọc trực tiếp, landing layer |
| **JSON** | Row / document | ❌ Không bắt buộc | ❌ Không mặc định | ⚠️ Khó (trừ JSON Lines) | API, dữ liệu semi-structured, nested data |
| **Parquet** | **Column** | ✅ Trong footer | ✅ snappy/gzip/zstd + encoding | ✅ **nhờ row group** | Data lake, analytics, Spark, DuckDB, BigQuery |
| **Avro** | **Row** | ✅ JSON ở đầu file | ✅ Có | ✅ nhờ sync marker | Kafka, streaming, data exchange, schema evolution |
| **ORC** | **Column** | ✅ Có | ✅ Có | ✅ nhờ stripe | **Kế thừa hệ thống Hive cũ**; dự án mới chọn Parquet |
| **Arrow** | **Columnar** | ✅ Có | **N/A — in-memory format** | **N/A — in-memory format** | Xử lý trong RAM, trao đổi giữa pandas/PyArrow/Spark/DuckDB |

---

## Giải thích các cột

### Splittable — và vì sao nó quan trọng

**Splittable = chia file thành nhiều mảnh độc lập, mỗi máy xử lý một mảnh mà không cần hỏi máy khác.** Đây là điều kiện bắt buộc để Spark xử lý song song.

| Format | Splittable nhờ đâu |
|---|---|
| Parquet | **Row group** — mỗi cái là tập dòng trọn vẹn đủ mọi cột (xem note Day 1) |
| ORC | **Stripe** — khái niệm tương đương row group |
| Avro | **Sync marker** — chuỗi byte đánh dấu ranh giới block |
| CSV | Ký tự xuống dòng |
| JSON | Không — object có thể lồng nhau nhiều cấp, không biết cắt ở đâu. JSON Lines (mỗi dòng một object) thì được |

> **Cạm bẫy kinh điển: CSV nén gzip thì KHÔNG splittable.**
> gzip phải giải nén tuần tự từ byte đầu, không nhảy vào giữa file được. Team nén CSV để tiết kiệm dung lượng → Spark chỉ dùng được 1 core cho mỗi file. Đây là lý do nên dùng Parquet thay vì "CSV + gzip": Parquet nén **theo từng page bên trong**, nên vẫn splittable.

### Vì sao Arrow khác hẳn phần còn lại

**Arrow không phải file format.** Nó là chuẩn bố trí dữ liệu columnar **trong RAM**.

Nén và splittable là thuộc tính của *cách lưu trên disk*; Arrow là *cách bố trí trong bộ nhớ*. Hỏi "Arrow có splittable không" giống hỏi "biến Python có splittable không" — câu hỏi không áp dụng.

PyArrow dùng cả tuần chính là nó. Luồng thực tế:

```
Parquet trên disk  →  đọc + giải nén  →  Arrow table trong RAM  →  pandas DataFrame
```

Mục đích của Arrow: nhiều ngôn ngữ và thư viện (pandas, Spark, DuckDB, Polars, R) trao đổi dữ liệu mà **không phải serialize lại**. Trước Arrow, chuyển dữ liệu từ Spark sang pandas phải convert qua một định dạng trung gian, tốn thời gian gấp nhiều lần việc tính toán.

*(Có Arrow IPC / Feather để ghi Arrow xuống disk, nhưng đó là format riêng, dùng cho cache tạm giữa các bước xử lý — không dùng lưu trữ dài hạn.)*

---

## Parquet vs Avro — vì sao Avro hợp streaming

Đây là cặp đối lập quan trọng nhất cần hiểu.

### Parquet ghi thế nào

```
gom đủ ~1 triệu dòng trong RAM
  → nén thành row group
  → ghi xuống disk
  → ... lặp lại ...
  → ghi FOOTER (metadata toàn file)
  → đóng file
```

Footer chỉ ghi được khi **biết hết mọi row group** — tức là khi file đã xong (lý do đầy đủ ở note Day 1). **File chưa có footer thì chưa đọc được gì cả.**

### Áp vào Kafka

Bản ghi đến từng cái một, không biết đến bao giờ dừng. Hai lựa chọn đều tệ:

| Cách làm | Hậu quả |
|---|---|
| Mỗi bản ghi → 1 file Parquet | Footer tốn vài KB cho 1 dòng dữ liệu; sinh hàng triệu file tí hon → **small files problem** (đo được ở note Day 4) |
| Gom 1 triệu dòng rồi ghi | Giữ dữ liệu trong RAM 10 phút; process chết là mất sạch; consumer không đọc được gì trong lúc chờ |

### Avro giải quyết thế nào

Row-based, schema ở **đầu file**, mỗi bản ghi tự chứa đầy đủ. Ghi xong bản ghi nào là nó nằm trên disk ngay, đọc được ngay. Không cần gom batch, không cần footer, không mất dữ liệu khi process chết giữa chừng.

> **Nguyên tắc:**
> **Parquet** tối ưu cho *ghi một lần, đọc nhiều lần, đọc theo cột*.
> **Avro** tối ưu cho *ghi liên tục từng bản ghi, đọc nguyên dòng*.

### Kiến trúc thực tế dùng cả hai

```
Kafka (Avro)  →  streaming ingest  →  gom theo giờ  →  Parquet trên data lake
     ↑ tầng vận chuyển                                      ↑ tầng lưu trữ phân tích
```

Không phải chọn một — mỗi format đứng ở tầng phù hợp với nó.

---

## Parquet vs ORC

Hai format gần tương đương về kỹ thuật: cùng columnar, cùng có đơn vị chia (row group / stripe), cùng nén và encoding tốt.

| | Parquet | ORC |
|---|---|---|
| Xuất thân | Hệ sinh thái Hadoop/Impala | Hệ sinh thái Hive |
| Điểm mạnh riêng | Hệ sinh thái rộng nhất | Lightweight index, hỗ trợ ACID trong Hive |
| Thực tế chọn | **Spark, Databricks, cloud warehouse, dự án mới** | **Kế thừa hệ thống Hive cũ** |

Parquet thắng không phải vì kỹ thuật vượt trội, mà vì **hệ sinh thái rộng hơn** — mọi engine đều đọc được.

---

## Khi nào CSV vẫn đúng

Đừng mặc định Parquet cho mọi thứ:

- **Landing layer** — giữ bản gốc nguyên trạng từ nguồn để replay được
- **Trao đổi với người dùng không kỹ thuật** — mở bằng Excel, đọc bằng mắt
- **Dataset rất nhỏ** (vài MB) — overhead của Parquet không đáng (đo được ở note Day 4: dataset 3.9 MB partition ra 26 file thì **chậm hơn 3.2 lần**)
- **Debug** — `head file.csv` là xong, Parquet phải viết code mới xem được

---

## Tóm tắt một câu cho từng format

| Format | Một câu |
|---|---|
| **CSV** | Đơn giản, ai cũng đọc được, không có schema — dùng ở biên hệ thống |
| **JSON** | Cho dữ liệu lồng nhau và API, không hợp phân tích quy mô lớn |
| **Parquet** | Mặc định cho data lake analytics — nhanh, nhỏ, schema trong file |
| **Avro** | Parquet của thế giới streaming — row-based, ghi liên tục được |
| **ORC** | Parquet của thế giới Hive — chọn khi hệ thống đã dùng nó |
| **Arrow** | Không phải file — là cách dữ liệu nằm trong RAM giữa các bước xử lý |