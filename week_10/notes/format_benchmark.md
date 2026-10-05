# Benchmark: CSV vs Parquet — file format cho data lake

**Tuần 10 — de-100-days** · Dataset: Olist Brazilian E-Commerce (`olist_order_items`)

---

## 1. Môi trường

| Hạng mục | Giá trị |
|---|---|
| Dataset | `olist_order_items_dataset.csv` |
| Kích thước | 112.650 dòng × 7 cột, 14.7 MB |
| Hệ điều hành | WSL Ubuntu trên Windows |
| Thư viện | pandas, pyarrow *(điền phiên bản: `pip list \| grep -E "pandas\|pyarrow"`)* |
| Phương pháp đo | Mỗi phép đo chạy 4 lần, **bỏ lần đầu** để loại ảnh hưởng OS page cache, lấy trung bình 3 lần sau |
| Script | `week10/src/format_benchmark.py` |

**Cấu trúc dữ liệu đáng lưu ý:** 3 trong 7 cột là ID dạng hash 32 ký tự (`order_id`, `product_id`, `seller_id`), trong đó `order_id` gần như unique (~98.666 giá trị trên 112.650 dòng). Đặc điểm này ảnh hưởng lớn tới mọi kết quả nén bên dưới.

---

## 2. Kết quả

### [1] CSV vs Parquet

```
format   size_mb  read_full_ms  read_1col_ms
--------------------------------------------
    CSV     14.7         261.6         112.7
Parquet      6.2          36.7           6.6
```

Parquet nhỏ hơn 2.4 lần, đọc toàn bộ nhanh hơn 7 lần. **Chênh lệch lớn nhất nằm ở kịch bản thực tế của analytics — đọc một cột: 112.7 ms so với 6.6 ms, nhanh hơn 17 lần.** So trực tiếp "CSV đọc toàn bộ" với "Parquet đọc một cột" là **40 lần**.

`usecols` của CSV chỉ cải thiện 2.3 lần dù bỏ 6/7 cột, vì pandas vẫn phải đọc và parse từng ký tự từ đầu mỗi dòng để đếm dấu phẩy — toàn bộ 14.7 MB vẫn đi từ disk lên RAM. Parquet thì đọc footer, biết byte offset, seek thẳng tới cột cần. Một đằng "đọc hết rồi vứt", một đằng "không đọc".

### [2] So sánh codec

```
codec   write_ms  size_mb  read_ms
----------------------------------
  none      85.0      8.8     44.4
snappy     111.6      6.2     44.8
  gzip    1327.1      4.1     41.2
  zstd      98.3      3.7     34.6
```

**zstd cho file nhỏ nhất (3.7 MB) với thời gian ghi gần bằng không nén.** gzip ghi chậm hơn một bậc độ lớn (~13 lần) mà vẫn cho file lớn hơn zstd 10%.

> **Về độ tin cậy của số liệu:** cột `size_mb` lặp lại y hệt qua mọi lần chạy — kết luận về dung lượng là chắc chắn. Cột thời gian dao động theo tải máy (lần chạy khác cho zstd 143 ms thay vì 98 ms). Chênh lệch read_ms giữa none/snappy/gzip (41–45 ms) nằm trong nhiễu đo, **không kết luận được thứ tự giữa ba codec này**. Chỉ zstd tách khỏi nhóm ở mọi lần chạy.

### [3] Kích thước theo từng cột

| Cột | none | snappy | gzip | zstd | zstd vs none |
|---|---:|---:|---:|---:|---:|
| order_id | 3875.1 | 3024.1 | 1882.9 | **1623.6** | **2.39x** |
| product_id | 1909.4 | 1610.3 | 1049.9 | **918.4** | **2.08x** |
| shipping_limit_date | 2454.4 | 1058.2 | 615.6 | 697.1 | 3.52x |
| freight_value | 231.5 | 208.6 | 189.6 | 191.6 | 1.21x |
| price | 221.1 | 202.2 | 178.7 | 180.0 | 1.23x |
| seller_id | 272.1 | 260.9 | 211.3 | **204.2** | **1.33x** |
| order_item_id | 46.4 | 24.8 | 15.9 | 17.2 | 2.71x |

*(đơn vị: KB)*

Chuyển từ snappy sang zstd tiết kiệm 2.5 MB, trong đó **2.1 MB đến từ riêng `order_id` và `product_id`** — hai cột mà dictionary encoding đã thất bại (từ điển vượt ngưỡng 1 MB nên fallback sang PLAIN). `seller_id`, cột đã được dictionary vắt từ ~3.600 KB xuống 272 KB, chỉ bớt thêm được 68 KB.

Hai điểm phụ:
- **Không codec nào thắng mọi cột.** gzip nhỏ hơn zstd ở `order_item_id` và `shipping_limit_date`; tổng file zstd vẫn thắng nhờ ăn đậm ở hai cột ID lớn. Chọn codec theo tổng thể, không theo từng cột.
- **`DOUBLE` là kiểu khó nén nhất** (`price`, `freight_value` chỉ ~1.2x) vì phần mantissa gần như ngẫu nhiên ở mức bit. Đáng nhớ khi gặp dataset đo lường/cảm biến.

### [4] Ảnh hưởng của dtype

So hai phiên bản cùng ghi bằng zstd: **v1** đọc CSV mặc định, **v2** ép `parse_dates` + `category` + `int8`.

```
column               v1_kb   v2_kb   delta_pct
----------------------------------------------
         product_id   918.4   747.8      -18.6
      order_item_id    17.2    17.1       -0.7
           order_id  1623.6  1623.6        0.0
              price   180.0   180.0        0.0
      freight_value   191.6   191.6        0.0
          seller_id   204.2   213.6        4.6
shipping_limit_date   697.1   818.9       17.5
```

**Tổng v2 lớn hơn v1** — kết quả ngược kỳ vọng ban đầu.

- `product_id` giảm 18.6%: ép `category` buộc dictionary chạy đến cùng thay vì fallback PLAIN (uncompressed 1955 → 1412 KB).
- `shipping_limit_date` **tăng 17.5%** khi chuyển string → timestamp. Ở tầng encoding nó giảm đúng lý thuyết (2513 → 976 KB, 19 byte xuống 8 byte), nhưng chuỗi `"2017-09-13 08:59:02"` cực dễ nén (mọi dòng cùng format, cùng tiền tố, dấu phân cách cố định) nên zstd vắt được 3.5x; còn timestamp INT64 có các bit thấp gần như ngẫu nhiên, zstd chỉ vắt được 1.16x.
- `order_item_id` ép `int8` gần như vô tác dụng: **Parquet không có kiểu INT8 vật lý**, nhỏ nhất là INT32. Logical type được ghi trong metadata, nhưng bit-packing + zstd đã xử lý xong từ v1.
- `seller_id` tăng 4.6%: PyArrow vốn đã tự dùng dictionary cho cột này (3.000 giá trị, dưới ngưỡng); ép `category` thêm chỉ làm từ điển ghi theo cách khác, tốn hơn chút.

---

## 3. Kết luận

**1. Parquet thắng CSV ở mọi chiều với workload analytics — chênh lệch lớn nhất là 40x.** Đọc một cột từ Parquet (6.6 ms) so với đọc toàn bộ CSV (261.6 ms). Lợi thế đến từ hai cơ chế độc lập: column pruning (chỉ đọc column chunk cần) và predicate pushdown (dùng min/max trong footer để bỏ qua cả row group).

**2. zstd nên là mặc định thay cho snappy.** Nhỏ hơn snappy 40% (3.7 vs 6.2 MB), ghi nhanh hơn gzip khoảng 13 lần, và đọc nhanh nhất trong 4 codec ở mọi lần chạy. snappy là mặc định lịch sử từ thời zstd chưa phổ biến; không còn lý do kỹ thuật để giữ nó cho dữ liệu mới. gzip chỉ nên dùng khi cần tương thích hệ thống cũ.

**3. Codec mạnh chỉ cứu được dữ liệu mà encoding đã bó tay.** 84% phần tiết kiệm khi chuyển snappy→zstd đến từ hai cột PLAIN; cột đã dictionary thành công chỉ bớt thêm 1.33x. Encoding làm việc trên **cấu trúc dữ liệu** (cardinality, giá trị lặp), codec làm việc trên **pattern byte** — khi encoding đã thành công thì codec chỉ còn nhặt vụn.

**4. Tỉ lệ nén phụ thuộc vào dữ liệu, không phải format.** Dataset này chỉ đạt 2.4x so với CSV, thấp hơn nhiều con số 5–10x thường thấy, vì 3/7 cột là hash gần như unique — dictionary và RLE đều vô hiệu. Đừng kỳ vọng một con số cố định; phải đo trên dữ liệu thật.

**5. Tối ưu dtype để lấy tính đúng đắn, không phải để lấy dung lượng.** Ép timestamp làm cột đó **lớn thêm 17.5%**, nhưng vẫn là lựa chọn đúng:

| Khía cạnh | string | timestamp |
|---|---|---|
| `statistics.min/max` | chỉ đúng với format ISO, **do may mắn** (thứ tự alphabet tình cờ trùng thứ tự thời gian) | luôn đúng |
| Trích năm/tháng | `.str.split("-")` — parse chuỗi, phụ thuộc format | `.dt.year` — vector hoá trên INT64 |
| Phép tính thời gian | không làm được | làm được |
| Engine khác đọc (Spark, DuckDB, BigQuery) | thấy string, phải tự parse | hiểu ngay |

Nếu dữ liệu dùng format `DD/MM/YYYY`, so sánh alphabet cho `"01/01/2020" < "02/03/2016"` — min/max trở nên vô nghĩa và predicate pushdown sẽ skip nhầm row group, trả về **kết quả sai**, không phải chậm. Đây là rủi ro đúng đắn, không phải rủi ro hiệu năng.

---

## 4. Khuyến nghị cho pipeline (T9 → T11)

### Bronze layer — lưu raw data

| Quyết định | Chọn | Lý do |
|---|---|---|
| Format | **Parquet** | Schema nằm trong file, mọi consumer đọc ra cùng kiểu dữ liệu |
| Codec | **zstd** | Nhỏ nhất, ghi nhanh, đọc nhanh nhất trong 4 codec đã đo |
| `row_group_size` | **cần chỉnh** | Hiện `num_row_groups = 1` — predicate pushdown chưa hoạt động ở mức row group |

### Ép dtype lúc ghi

Áp dụng ở bước transform, **trước** khi ghi Parquet:

| Cột | Ép thành | Lý do |
|---|---|---|
| mọi cột ngày/giờ | `datetime64` | min/max đúng với mọi format; `.dt.year` cho partition; engine khác hiểu ngay |
| cột phân loại cardinality thấp (`status`, `state`, `category`) | `category` | Buộc dictionary encoding, giảm đáng kể |
| ID hash gần unique (`order_id`) | **giữ nguyên `str`** | Dictionary chắc chắn thất bại; ép `category` chỉ tốn RAM lúc xử lý mà không giảm được file |

Nguyên tắc: ép `category` khi **cardinality thấp so với số dòng**; để nguyên khi gần unique.

### Giữ CSV gốc hay không

**Giữ**, nhưng tách bạch vai trò:

- `landing/` — CSV gốc nguyên vẹn, không sửa, là nguồn để replay khi logic transform có bug
- `bronze/` — Parquet + zstd + đã ép dtype, là nguồn cho mọi bước phía sau

Chi phí giữ CSV chỉ là dung lượng (14.7 MB mỗi lần ingest); cái mua được là khả năng dựng lại toàn bộ pipeline khi phát hiện lỗi transform. Đây đúng tinh thần bronze layer của Medallion: **giữ nguyên bản, không mất thông tin**.

### Những điều chưa đo được trong báo cáo này

- **Predicate pushdown thật**: dataset chỉ có 1 row group nên chưa đo được hiệu quả skip. Cần dataset lớn hơn hoặc chỉnh `row_group_size`.
- **Partition pruning**: chưa test layout `year=/month=/day=`.
- **Small files problem**: đã xác định overhead cố định ~3 ms mỗi file (mở file + parse footer), nhưng chưa đo trên tập nhiều file nhỏ.

Ba điểm này là nội dung Day 4.