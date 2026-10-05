# Day 2 — Column pruning đo thật, compression codec, dtype

> Tiếp nối Day 1. Trọng tâm: đo bằng số thay vì tin lý thuyết.

## 1. Benchmark đọc — column pruning

Dataset Olist order_items, 112.650 dòng × 7 cột. Mỗi phép đo chạy 4 lần, bỏ lần đầu (OS page cache).

| | full | 1 cột | cải thiện |
|---|---:|---:|---:|
| CSV | 221.5 ms | 122.9 ms | **1.8x** |
| Parquet | 35.6 ms | 6.0 ms | **5.9x** |

**Con số đáng nhớ: CSV full 221.5 ms → Parquet 1 cột 6.0 ms = 37x.**

### `usecols` của CSV không phải column pruning

Chỉ giảm 1.8x dù bỏ 6/7 cột. Để lấy cột `price` ở vị trí thứ 6, pandas vẫn phải đọc và parse từng ký tự từ đầu dòng để đếm đủ 5 dấu phẩy. **Toàn bộ 14.72 MB vẫn đi từ disk lên RAM.** Thứ tiết kiệm được chỉ là bước cuối: không dựng object Python cho 6 cột kia.

Parquet thì đọc footer → biết `price` nằm ở byte offset nào → seek thẳng tới đó, đọc 207 KB, **không chạm vào 6 MB còn lại**.

> Một đằng "đọc hết rồi vứt", một đằng "không đọc".

### Overhead cố định

File có 7 cột, đọc 1 cột chỉ nhanh 5.9x (không phải 7x). Và `price` chỉ chiếm 3% file nên lý thuyết phải nhanh ~30x.

Thứ tự engine đọc file Parquet:

```
1. Mở file, seek tới cuối
2. Đọc 4 byte cuối → biết footer dài bao nhiêu
3. Seek ngược lên, đọc trọn footer
4. Parse footer: schema, row group, byte offset, min/max
5. Lọc: cột nào cần, row group nào cần
6. Seek tới offset các column chunk đã chọn → đọc byte
7. Giải nén (codec)
8. Giải mã (dictionary → giá trị thật)
9. Dựng cấu trúc Arrow trong RAM
10. Arrow → pandas DataFrame
```

| Bước | Tính chất |
|---|---|
| 1–5 (mở file, đọc + parse footer, lọc) | **CỐ ĐỊNH** — footer chứa metadata của cả 7 cột, phải parse hết mới biết `price` ở đâu |
| 6–10 (đọc byte, giải nén, giải mã, dựng Arrow) | **TỈ LỆ** với lượng dữ liệu đã chọn |

```
Parquet full:   ~3 ms (cố định) + ~33 ms (6.24 MB)  = 35.6 ms
Parquet 1 cột:  ~3 ms (cố định) +  ~3 ms (207 KB)   =  6.0 ms
```

**Hệ quả — small files problem:** overhead ~3 ms gần như không đổi dù file to hay nhỏ. Với file 1 KB vẫn trả ~3 ms. → 10.000 file Parquet nhỏ = 30 giây chỉ để đọc footer, chưa đọc byte dữ liệu nào.

## 2. Compression codec

### Lý thuyết

```
giá trị thô → ENCODING (dictionary/RLE) → NÉN (codec) → byte trên disk
```

Codec là tầng cuối, nén **byte** — không biết gì về cột hay kiểu dữ liệu.

| Codec | Tỉ lệ nén | Tốc độ nén | Tốc độ giải nén | Dùng khi |
|---|---|---|---|---|
| `none` | 1x | — | — | debug, data đã nén sẵn |
| `snappy` | thấp | rất nhanh | rất nhanh | mặc định cũ, hot data |
| `gzip` | cao | chậm | trung bình | archive, hệ thống cũ |
| `zstd` | cao | nhanh | rất nhanh | **mặc định mới của ngành** |

### Kết quả đo

| Codec | Write | Size | vs snappy | Read |
|---|---:|---:|---:|---:|
| none | 100.6 ms | 8.8 MB | +42% | 43.2 ms |
| snappy | 112.2 ms | 6.2 MB | — | 37.1 ms |
| gzip | **1398.4 ms** | 4.1 MB | −34% | 41.4 ms |
| **zstd** | **105.3 ms** | **3.7 MB** | **−40%** | **22.8 ms** |

**zstd thắng tuyệt đối cả 3 chiều.**

- **gzip ghi chậm gấp 12.5 lần** chỉ để đổi lấy file **to hơn** zstd. Không có lý do kỹ thuật nào chọn gzip cho data mới; nó tồn tại vì tương thích hệ thống cũ.
- **`none` đọc chậm hơn `snappy`** (43.2 vs 37.1 ms) — phản trực giác. Đọc 8.8 MB từ disk tốn nhiều hơn phần tiết kiệm được khi bỏ bước giải nén. → **I/O đắt hơn CPU.** Đây là nguyên tắc nền của mọi columnar format hiện đại.

### Per-column: codec ăn ở đâu?

| Cột | none | snappy | zstd | zstd vs none | Encoding |
|---|---:|---:|---:|---:|---|
| order_id | 3875 KB | 3024 KB | **1624 KB** | **2.39x** | PLAIN (fallback) |
| product_id | 1909 KB | 1610 KB | **918 KB** | **2.08x** | PLAIN (fallback) |
| shipping_limit_date | 2454 KB | 1058 KB | 697 KB | 3.52x | PLAIN (string) |
| order_item_id | 46 KB | 25 KB | 17 KB | 2.71x | dictionary ✓ |
| **seller_id** | 272 KB | 261 KB | **204 KB** | **1.33x** | dictionary ✓ |
| price | 221 KB | 202 KB | 180 KB | 1.23x | PLAIN (double) |
| freight_value | 232 KB | 209 KB | 192 KB | 1.21x | PLAIN (double) |

Chuyển snappy→zstd tiết kiệm 2.5 MB, trong đó **2.1 MB đến từ `order_id` + `product_id`** (hai cột PLAIN). `seller_id` chỉ bớt 57 KB.

> **Kết luận:** Codec mạnh ăn chủ yếu ở dữ liệu mà **encoding đã bó tay**. Cột đã được dictionary vắt kiệt thì đổi codec gần như vô ích — dãy index 2-byte đã là thông tin gần tối ưu, không còn pattern dư thừa.
>
> Encoding làm việc dựa trên **cấu trúc dữ liệu** (giá trị lặp, cardinality). Codec làm việc dựa trên **pattern byte**. Khi encoding đã thành công, codec chỉ còn nhặt vụn.

Hai điểm phụ:

- **Không có codec nào thắng mọi cột.** `order_item_id` và `shipping_limit_date` thì gzip nhỏ hơn zstd; tổng file zstd vẫn thắng vì ăn đậm ở 2 cột ID to. Chọn theo tổng thể.
- **`double` là loại dữ liệu khó nén nhất** (`price`/`freight_value` chỉ ~1.2x) — mantissa gần như ngẫu nhiên ở mức bit. Nhớ khi gặp dataset toàn số đo lường/cảm biến.

## 3. Ép dtype

### CSV vs Parquet: ai quyết định kiểu dữ liệu

`read_parquet` **không có tham số `dtype`** — và không cần có.

> **CSV:** kiểu dữ liệu do **người đọc** quyết định, mỗi lần đọc phải khai báo lại, ai quên thì sai.
> **Parquet:** kiểu dữ liệu do **người ghi** quyết định, nằm trong footer, mọi người đọc đều nhận giống nhau.

Hệ quả thực tế: với CSV, pipeline A đọc `order_id` ra int64, pipeline B quên `dtype` nên đọc ra string → join hỏng. Với Parquet không thể xảy ra. **Đó là lý do data lake dùng Parquet, không chỉ vì nó nhỏ.**

### Thí nghiệm

```python
# v1 — thô
df1 = pd.read_csv(CSV)

# v2 — ép dtype
df2 = pd.read_csv(
    CSV,
    parse_dates=["shipping_limit_date"],
    dtype={"order_item_id": "int8", "seller_id": "category", "product_id": "category"},
)
```

Cả hai ghi với zstd.

| Cột | v1 | v2 | Thay đổi |
|---|---:|---:|---:|
| product_id | 940.4 KB | 765.8 KB | **−18.6%** ✓ |
| order_item_id | 17.6 KB | 17.5 KB | −0.7% |
| order_id | 1662.5 KB | 1662.5 KB | 0% |
| price / freight_value | — | — | 0% |
| seller_id | 209.1 KB | 218.7 KB | **+4.6%** ✗ |
| **shipping_limit_date** | **713.8 KB** | **838.5 KB** | **+17.5%** ✗ |

**Tổng v2 TO HƠN v1.** Kết quả ngược kỳ vọng — và đáng giá hơn kết quả "đẹp".

### Giải thích từng chỗ

**`shipping_limit_date`: string 713 KB → timestamp 838 KB.** Nhìn `uncompressed`: 2513 → 976 KB, giảm đúng 2.6x như lý thuyết (19 byte → 8 byte). Nhưng sau zstd thì ngược lại:

- Chuỗi `"2017-09-13 08:59:02"` **cực dễ nén**: mọi dòng cùng format, cùng tiền tố `"201"`, dấu `-` và `:` ở đúng vị trí → zstd vắt 2513 → 714 KB (3.5x)
- Timestamp INT64 là số nguyên lớn, bit thấp gần như ngẫu nhiên (giây lẻ) → zstd chỉ vắt 976 → 838 KB (1.16x)

**`order_item_id`: `int8` không có tác dụng.** `physical_type` v2 là **INT32**, không phải INT8 — **Parquet không có kiểu INT8 vật lý**, nhỏ nhất là INT32. Nó chỉ ghi "logical type = int8" trong metadata. Sau nén thì bit-packing + zstd đã xử lý xong từ v1 rồi.

**`product_id` −18.6% — chỗ duy nhất `category` có tác dụng.** 33.000 giá trị unique: v1 từ điển vượt ngưỡng 1MB nên fallback PLAIN; v2 ép `category` buộc dictionary chạy đến cùng → uncompressed 1955 → 1412 KB.

**`seller_id` +4.6%** — PyArrow vốn đã tự dùng dictionary (3.000 giá trị, dưới ngưỡng). Ép thêm chỉ làm từ điển ghi theo cách khác, hơi tốn hơn.

### Vì sao vẫn ép timestamp dù tốn thêm 125 KB

| Khía cạnh | string | timestamp |
|---|---|---|
| min/max có đúng không | chỉ đúng với format ISO, **do may mắn** | luôn đúng |
| Trích năm/tháng | `.str.split("-").str[0]` — parse chuỗi, phụ thuộc format | `.dt.year` — vector hoá trên INT64 |
| Phép tính thời gian (cộng ngày, chênh lệch) | không làm được | làm được |
| Engine khác đọc (Spark, DuckDB, BigQuery) | thấy string, phải tự parse | thấy timestamp, dùng ngay |
| Dung lượng | nhỏ hơn 125 KB | — |

**Chi tiết về min/max:** với cột string, engine so sánh theo **thứ tự từ điển (alphabet)**, không phải theo thời gian — nó không biết đó là ngày. Format `YYYY-MM-DD` chạy đúng vì thứ tự alphabet **tình cờ trùng** thứ tự thời gian.

Đổi sang format `DD/MM/YYYY` thì may mắn hết tác dụng:
```
"01/01/2020"  <  "02/03/2016"  <  "03/12/2018"   (theo alphabet)
```
Năm 2020 "nhỏ hơn" năm 2016 → `statistics.min/max` **vô nghĩa hoàn toàn** → predicate pushdown skip nhầm row group → query trả về **kết quả SAI**, không phải chậm.

Với timestamp INT64 thì min/max là số, so sánh luôn đúng với mọi format hiển thị.

> **Nguyên tắc:** đánh đổi 17% dung lượng của một cột để lấy **tính đúng đắn và khả năng tương tác** là đổi có lời. Dung lượng chỉ là một chiều, và thường không phải chiều quan trọng nhất.
>
> Schema trong Parquet không chỉ mô tả dữ liệu — nó quyết định **engine được phép làm gì** với dữ liệu đó.

## 4. Ba bài học chốt

1. **Dung lượng nhỏ hơn ở tầng encoding không đảm bảo file nhỏ hơn.** Encoding và codec có thể triệt tiêu nhau. Chỉ số đáng tin duy nhất là `total_compressed_size` đo thật.
2. **Ép dtype vẫn đúng — nhưng không phải vì dung lượng.** Lý do chính là tính đúng đắn của min/max và khả năng tương tác giữa các engine.
3. **Đừng tối ưu theo lý thuyết. Đo.**

## 5. Bẫy kỹ thuật gặp phải

- `df.to_parquet()` trả về `None` — không gán lại (`df = df.to_parquet(...)` làm mất DataFrame)
- Đường dẫn tương đối phụ thuộc **thư mục đang đứng khi chạy `python`**, không phải vị trí file `.py`. Dùng `Path(__file__).resolve().parents[n]` — tuần 11 Airflow chạy DAG với working directory khác, script dùng đường dẫn tương đối sẽ gãy hết.
- `from module import x` **thực thi cả file** đó. Bọc phần chạy thử trong `if __name__ == "__main__":`
- Hàm `bench()` cắt `times[1:]` để bỏ warm-up → gọi với `runs=1` sẽ `ZeroDivisionError`. Và `runs=1` làm hỏng phép đo vì page cache.
- `lambda: fn(path)` bắt **biến**, không bắt giá trị — an toàn khi gọi ngay trong vòng lặp, sẽ sai nếu gom lambda vào list rồi chạy sau.

## 6. Việc còn lại cho Day 3–4

- [ ] Gộp mọi phép đo thành `format_benchmark.py` (output bắt buộc của tuần)
- [ ] `num_row_groups = 1` → chỉnh `row_group_size`, đo predicate pushdown thật
- [ ] Partition theo `year/month/day`, đo partition pruning