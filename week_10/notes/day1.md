# Day 1 — Row vs Columnar, cấu trúc file Parquet

> Tuần 10 — File formats. Mục tiêu: hiểu *vì sao* Parquet nhanh và nhỏ, không phải học thuộc.

## 1. Vấn đề gốc: disk là dãy byte 1 chiều

Bảng dữ liệu là 2 chiều, nhưng disk chỉ là một dãy byte tuyến tính. Câu hỏi thiết kế: xếp bảng 2 chiều vào dãy 1 chiều theo thứ tự nào?

Bảng mẫu:

| order_id | status | price | city |
|---|---|---|---|
| 1 | delivered | 100 | Hanoi |
| 2 | shipped | 200 | Hue |
| 3 | delivered | 300 | Hanoi |

**Cách A — row-based (CSV, PostgreSQL):**
```
1,delivered,100,Hanoi | 2,shipped,200,Hue | 3,delivered,300,Hanoi
```

**Cách B — columnar (Parquet, ORC):**
```
1,2,3 | delivered,shipped,delivered | 100,200,300 | Hanoi,Hue,Hanoi
```

Cùng dữ liệu, cùng số byte, chỉ khác thứ tự nằm trên disk.

## 2. Lợi thế 1 — Column pruning (đọc ít byte hơn)

Query `SELECT AVG(price)` trên bảng 50 cột:

- **Row-based:** phải đọc **100%** file. Giá trị `price` nằm rải rác, cách nhau 49 cột khác → không thể chỉ đọc phần cần.
- **Columnar:** engine chỉ đọc **column chunk** của `price` → khoảng **2%** file.

> Thuật ngữ: khối chứa một cột gọi là **column chunk**, không phải "row". Phân biệt với *row group* ở mục 5.

## 3. Lợi thế 2 — Nén tốt hơn (file nhỏ hơn)

### Dictionary encoding

Cột `status` có 10 triệu dòng nhưng chỉ 5 giá trị khác nhau:

```
Dictionary:  0→delivered, 1→shipped, 2→canceled, 3→processing, 4→approved
Data:        0,0,0,1,1,0,2,2,2,2,...
```

- Trước: `"delivered"` = 9 byte × 10 triệu ≈ **90 MB**
- Sau: dictionary ~40 byte + mỗi giá trị 3 bit ≈ **3.75 MB**

### Run-Length Encoding (RLE)

Dãy index `0,0,0,1,1,0,2,2,2,2` → `(0,3),(1,2),(0,1),(2,4)` — "giá trị 0 lặp 3 lần, giá trị 1 lặp 2 lần...".

Parquet chồng cả hai: dictionary → RLE → rồi mới bọc thêm codec nén chung (snappy/zstd).

### Vì sao row-based không làm được

Từ khoá: **tính đồng nhất (homogeneity)**.

```
Một cột:  100, 200, 300, 150, 250        → cùng kiểu, cùng miền giá trị
Một dòng: 3, delivered, 300, Hanoi       → int + string + int + string lẫn lộn
```

Thuật toán nén cần **pattern lặp** để khai thác. Một cột có pattern; một dòng thì không. Thêm nữa, RLE đếm số lần lặp **liên tiếp** — ở row-based các giá trị cùng cột bị chia cắt bởi các cột khác nên không bao giờ liên tiếp.

## 4. Columnar không phải lúc nào cũng thắng

`SELECT * WHERE id = 123` → **row-based nhanh hơn**. Cả dòng nằm liền một chỗ, đọc một phát là xong. Columnar phải đi nhặt 50 mảnh ở 50 vị trí rồi ghép lại.

→ Đây là lý do PostgreSQL (OLTP) vẫn row-based và sẽ không đổi. Columnar cho OLAP, row-based cho OLTP.

## 5. Cấu trúc thật của file Parquet

Nếu "một cột = một khối khổng lồ liên tục" thì sinh ra 2 vấn đề:

1. **Không chia việc được.** Máy nhận 10GB đầu file sẽ có vài cột đầy đủ nhưng thiếu các cột khác → không tự tính nổi `SUM(price) GROUP BY city`, phải xin dữ liệu qua mạng (shuffle). Tương tự khi RAM 8GB mà file 50GB: cần đọc từng mảnh, mà mỗi mảnh phải **đủ mọi cột**.
2. **Không skip được.** Khối 1GB thì không có đơn vị nào đủ nhỏ để gắn thống kê min/max vào mà bỏ qua.

**Giải pháp: cắt theo dòng trước, columnar bên trong mỗi mảnh.** Hai thứ lồng nhau, không phải hai bước nối tiếp.

```
┌──────────────────────────────────────┐
│ PAR1                    ← magic byte │
├──────────────────────────────────────┤
│ Row Group 1  (dòng 1 → 1.000.000)    │
│   Column Chunk: order_id             │
│     ├─ Page 1  (+ min/max)           │
│     ├─ Page 2  (+ min/max)           │
│     └─ Page 3                        │
│   Column Chunk: status               │
│   Column Chunk: price                │
│   ... đủ 50 column chunk             │
├──────────────────────────────────────┤
│ Row Group 2  (dòng 1.000.001 → ...)  │
├──────────────────────────────────────┤
│ FOOTER                               │
│   • schema (tên cột + kiểu dữ liệu)  │
│   • với mỗi row group:               │
│       - byte offset từng column chunk│
│       - min / max / null_count       │
│   • footer length (4 byte cuối)      │
│ PAR1                                 │
└──────────────────────────────────────┘
```

| Tầng | Kích thước điển hình | Nhiệm vụ |
|---|---|---|
| **Row Group** | ~128 MB | Đơn vị chia việc — độc lập, đủ mọi cột |
| **Column Chunk** | — | Đơn vị column pruning |
| **Page** | ~1 MB | Đơn vị nén & I/O nhỏ nhất, có min/max riêng |
| **Footer** | vài KB | Bản đồ + thống kê → predicate pushdown |

## 6. Predicate pushdown

```
Row Group 1 → order_date: min=2026-08-01, max=2026-08-15
Row Group 2 → order_date: min=2026-08-16, max=2026-08-31
Row Group 3 → order_date: min=2026-09-01, max=2026-09-15
```

Query `WHERE order_date = '2026-09-01'` → đọc 3 cặp min/max, bỏ qua hoàn toàn RG1 và RG2, chỉ mở RG3.

> **Lưu ý:** min/max chỉ cho phép **loại trừ chắc chắn**, không cho phép **khẳng định chắc chắn**. RG3 *có thể* chứa ngày cần — vẫn phải mở ra đọc. RG1 thì *chắc chắn không* chứa. Loại được cái chắc chắn không chứa là đủ ăn tiền.

## 7. Vì sao metadata ở footer, không ở header

**Phía ghi:** engine ghi tuần tự từ byte 0. Tại thời điểm ghi header, nó chưa nén row group nào → chưa biết min/max, chưa biết byte offset. Muốn ghi header đầy đủ phải giữ toàn bộ data trong RAM, hoặc quay lại ghi đè — mà chừa sẵn bao nhiêu byte thì không đoán được (footer to nhỏ phụ thuộc số row group, mà số row group phụ thuộc dữ liệu nén lại còn bao nhiêu).

Footer thì **không cần chừa chỗ** — nó nằm sau toàn bộ data, muốn dài bao nhiêu cũng được.

**Phía đọc:** seek tới cuối file → đọc 4 byte cuối (độ dài footer) → đọc ngược lên lấy trọn footer. **2 lần seek là có toàn bộ bản đồ file.**

**Lý do thực tế với DE:** Parquet thiết kế cho object storage (MinIO, S3, GCS) — nơi file **immutable**, không có thao tác "ghi đè 500 byte ở đầu object". Nếu dùng header, ghi file 10GB lên MinIO sẽ phải upload 2 lần.

> **Nguyên tắc chung:** format nào cần streaming write một lần thì metadata phải nằm ở cuối. Gặp lại ở ORC và ở Iceberg (manifest file).

**Hệ quả:** file Parquet **không stream được từ đầu** — phải có footer trước mới hiểu được gì. Khác CSV đọc từ dòng nào cũng được.

## 8. Thực nghiệm — dataset Olist order_items

112.650 dòng × 7 cột.

```
CSV:     14.72 MB
Parquet:  6.24 MB   (snappy)
Ratio:    2.36x
num_row_groups: 1
```

### Metadata per-column (snappy, row group 0)

| Cột | physical_type | compressed | uncompressed | ratio |
|---|---|---:|---:|---:|
| order_id | BYTE_ARRAY | 3,096 KB | 3,968 KB | 1.28x |
| product_id | BYTE_ARRAY | 1,649 KB | 1,955 KB | 1.19x |
| shipping_limit_date | BYTE_ARRAY | 1,084 KB | 2,513 KB | 2.32x |
| seller_id | BYTE_ARRAY | 267 KB | 279 KB | 1.04x |
| freight_value | DOUBLE | 214 KB | 237 KB | 1.11x |
| price | DOUBLE | 207 KB | 226 KB | 1.09x |
| order_item_id | INT64 | 25 KB | 48 KB | 1.87x |

### Phát hiện

**2.36x là thấp** so với kỳ vọng thông thường (5–10x). Lý do: 3 cột ID là hash 32 ký tự gần như unique → dictionary vô dụng, RLE vô dụng, snappy không tìm được pattern. **Nén tốt hay không phụ thuộc vào dữ liệu, không phải format.**

**`encodings` không nói lên encoding đã dùng.** Mọi cột đều hiện `('PLAIN', 'RLE', 'RLE_DICTIONARY')` — đó là *tập hợp các encoding từng xuất hiện đâu đó* trong column chunk. Cơ chế thật:

```
Bắt đầu ghi cột → thử dictionary encoding
  → xây từ điển dần khi gặp giá trị mới
  → nếu từ điển vượt ngưỡng (mặc định 1MB):
       "cardinality quá cao, bỏ dictionary"
       → các page còn lại chuyển sang PLAIN
```

`RLE` luôn xuất hiện vì nó encode **definition levels** (thông tin null), không phải encode giá trị.

**`uncompressed_size` KHÔNG phải kích thước dữ liệu gốc.** Nó là kích thước *sau encoding, trước nén*:

```
Giá trị thô → ENCODING (dictionary/RLE) → uncompressed_size
            → NÉN (codec)               → compressed_size
```

Bằng chứng: `order_id` và `seller_id` cùng là hash 32 ký tự, cùng 112.650 dòng, lưu thô đều phải ≈ 3.600 KB. Nhưng:

| | uncompressed | giải thích |
|---|---:|---|
| order_id (~98.666 unique) | 3,968 KB | từ điển vượt 1MB → fallback PLAIN |
| seller_id (~3.000 unique) | 279 KB | dictionary thành công: 96 KB từ điển + 112.650 index × 2 byte ≈ 225 KB |

→ `seller_id` ratio 1.04x **không có nghĩa là nén kém**, mà là dictionary đã vắt kiệt, snappy không còn gì để vắt thêm. Hai tầng — đừng đánh giá tầng sau mà quên tầng trước.

## 9. Việc còn lại

- [ ] `shipping_limit_date` đang là string → Day 2 ép `datetime64`, đo lại
- [ ] `num_row_groups = 1` → Day 4 chỉnh `row_group_size`, đo predicate pushdown

## 10. Câu hỏi phỏng vấn rút ra

1. Row group là gì, chọn row group size lớn/nhỏ ảnh hưởng thế nào?
2. Predicate pushdown hoạt động nhờ đâu?
3. Vì sao metadata Parquet nằm ở footer chứ không phải header?
4. `uncompressed_size` trong metadata nghĩa là gì?
5. Khi nào row-based vẫn thắng columnar?