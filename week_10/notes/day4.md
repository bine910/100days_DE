# Day 4 — Row group, partitioning, data lake layout

> Trọng tâm: ba điều kiện để predicate pushdown hoạt động, và vì sao partition sai lại làm chậm. Cả hai đều được chứng minh bằng kết quả **ngược kỳ vọng**.

---

## 1. Row group size

### Thí nghiệm A — dữ liệu thứ tự ngẫu nhiên

```
row_group_size  num_row_groups  size_mb  filter_ms  full_ms
-----------------------------------------------------------
          5000              23      5.0       92.4     73.0
         20000               6      4.4       59.5     43.4
        112650               1      3.7       43.7     36.5
```

Filter `price > 1000` **chậm hơn** đọc toàn bộ. Chia nhỏ row group chỉ tốn thêm 35% dung lượng mà không được gì.

Min/max của 23 row group giải thích tất cả:

```
Row group  0:  3.49 → 6735.00
Row group  1:  4.20 → 2689.00
Row group  2:  3.99 → 4690.00
...
Row group 22:  4.90 → 6729.00
```

**Cả 23 row group đều có `max > 1000`** → không loại được cái nào → engine mở hết, đọc hết, rồi còn tốn thêm công so sánh từng giá trị.

### Thí nghiệm B — sort theo cột lọc

Chỉ thêm một dòng: `df.sort_values("price")`

```
row_group_size  num_row_groups  size_mb  filter_ms  full_ms
-----------------------------------------------------------
          5000              23      4.6       12.7     33.3
         20000               6      4.4       12.2     65.4
        112650               1      4.1       34.7     31.2
```

Min/max giờ tách rời nhau:

```
Row group  0:   0.85 →   16.22    ✗ skip
Row group  1:  16.24 →   21.90    ✗ skip
...
Row group 21: 295.00 →  579.99    ✗ skip
Row group 22: 579.99 → 6735.00    ✓ ĐỌC
```

**22/23 row group bị loại chỉ bằng cách đọc footer.** Engine chạm vào đúng 1 row group.

### So sánh

| row_group_size | filter_ms (ngẫu nhiên) | filter_ms (đã sort) | Cải thiện |
|---|---:|---:|---:|
| 5.000 | 92.4 | **12.7** | **7.3x** |
| 20.000 | 59.5 | 12.2 | 4.9x |
| 112.650 | 43.7 | 34.7 | 1.3x |

Thêm hai điểm:

- **`row_group_size = toàn bộ dataset` thì sort cũng vô dụng** (34.7 ≈ full 31.2). Không có đơn vị nào để skip.
- **Sort còn làm file nhỏ hơn** (5.0 → 4.6 MB ở mức 5.000). Giá trị gần nhau xếp cạnh nhau thì nén tốt hơn. Được cả hai mặt.

### Kết luận Block 1

> **Ba điều kiện để predicate pushdown hoạt động:**
> 1. File phải chia thành **nhiều row group** — không thì không có gì để skip
> 2. Dữ liệu phải **sort theo cột sẽ lọc** — không thì mọi row group có cùng khoảng min/max
> 3. Query phải **lọc đúng cột đã sort**
>
> Thiếu một trong ba là mất tác dụng hoàn toàn.

Chỉ sort được theo một hoặc vài cột → phải chọn cột nào hay filter nhất. Đây là quyết định thiết kế, **giống hệt việc chọn cột cho index trong PostgreSQL (T2)**.

Đánh đổi: nhiều row group hơn → file to hơn (+35%), vì mỗi row group có từ điển riêng và metadata riêng trong footer.

---

## 2. Partitioning

### Lý thuyết

Hive-style partitioning đưa giá trị cột vào **đường dẫn thư mục** thay vì lưu trong file:

```
bronze/items/year=2017/month=09/part-0.parquet
bronze/items/year=2017/month=10/part-0.parquet
bronze/items/year=2018/month=01/part-0.parquet
```

| | Đơn vị skip | Biết skip bằng cách | Chi phí |
|---|---|---|---|
| Predicate pushdown | row group | đọc footer, so min/max | mở file + ~3 ms/file |
| **Partition pruning** | **cả thư mục** | **đọc tên thư mục** | **gần như 0** |

Partition pruning nhanh hơn một bậc vì **không mở file nào**. Với 10.000 file mà chỉ cần 1 thư mục, pushdown vẫn phải đọc 10.000 footer; partition pruning bỏ qua ngay ở tầng liệt kê thư mục.

Hai điểm nữa:
- Cột đã partition **không còn lưu trong file** — giá trị suy ra từ đường dẫn
- Partition là sort **thô, vĩnh viễn, ở mức thư mục**; sort trong row group là mịn, trong phạm vi một file

### Thí nghiệm — và kết quả ngược kỳ vọng

Partition theo `year/month` trên dataset Olist (112.650 dòng, 3.9 MB):

```
layout       files  size_mb  query_1month_ms
--------------------------------------------
       flat      1      3.9             54.1
partitioned     26      5.4            171.6
```

**Partitioned CHẬM HƠN 3.2 lần và TO HƠN 38%.**

### Giải thích — small files problem, đo được bằng số

Overhead cố định mỗi file Parquet là **~3 ms** (mở file + seek + đọc + parse footer — xem note Day 2). Với 26 file:

```
26 file × ~3 ms overhead           ≈  78 ms
+ liệt kê thư mục, parse tên partition
+ ghép 26 bảng Arrow thành một
──────────────────────────────────────────
≈ 170 ms, trong khi dữ liệu thật cần đọc chỉ ~90 KB
```

Partition pruning **có hoạt động** — nó bỏ qua đúng 25 thư mục. Nhưng phần tiết kiệm được (đọc 90 KB thay vì 3.9 MB) quá nhỏ so với overhead quản lý 26 mảnh.

Dung lượng tăng 38% vì cùng lý do với row group: mỗi file có từ điển riêng + footer riêng.

### Kết luận Block 2

> **Partition chỉ có lời khi mỗi partition đủ lớn.** Target **128 MB – 1 GB** mỗi file.
>
> Công thức thô: partition có lời khi `kích thước mỗi partition >> overhead × số partition`.
>
> Dataset 3.9 MB **không nên partition** — nó thuộc loại "đọc hết còn nhanh hơn đi tìm".

Đây là lỗi thiết kế cực phổ biến: partition theo `year/month/day` cho dataset vài chục MB, rồi than Spark chậm.

---

## 3. Quyết định thiết kế data lake

### Chọn độ mịn partition theo quy mô

Không có nguyên tắc cố định — **quy mô dữ liệu quyết định**:

| Dữ liệu mỗi ngày | Partition theo |
|---|---|
| vài MB | `year` hoặc `year/month` |
| vài trăm MB | `year/month/day` |
| vài GB | `year/month/day/hour` |

Mục tiêu luôn là mỗi partition ra file 128 MB – 1 GB. Khi dữ liệu lớn dần thì đổi layout — việc này bình thường, gọi là **repartitioning**.

Cạm bẫy hai đầu:
- Partition quá mịn → small files problem (đã đo ở trên)
- Không partition → file phình tới vài GB, mỗi lần ingest phải đọc-ghi lại toàn bộ

### `ingestion_date` vs ngày business — câu phỏng vấn

**Tình huống:** pipeline chạy ngày 15/10, batch nhận được chứa:
- đơn ngày 15/10 (bình thường)
- đơn ngày 03/10 (hệ thống nguồn sửa muộn, giờ mới đẩy sang)

**Partition theo ngày business (`shipping_limit_date`):**
Bản ghi 03/10 phải ghi vào `date=2026-10-03` — partition đã tồn tại từ 12 ngày trước. Muốn idempotent phải xoá và ghi lại partition cũ. Pipeline hôm nay **chạm vào những partition nào thì không biết trước** — phụ thuộc nội dung dữ liệu. Chạy lại ngày 15/10 có thể làm hỏng dữ liệu ngày 03/10.

**Partition theo `ingestion_date`:**
Mọi thứ nhận hôm nay vào `ingestion_date=2026-10-15`, bất kể ngày business. Chạy lại = xoá đúng một thư mục, ghi lại. **Không bao giờ chạm partition của ngày khác.**

> **Quy tắc:** Bronze partition theo **`ingestion_date`**. Silver/Gold partition theo **cột business**.
>
> Bronze là bản ghi *"ta đã nhận được gì, khi nào"* — bất biến theo thời gian, idempotent dễ dàng.
> Silver/Gold là *"sự thật là gì"* — tổ chức theo cách người dùng query.

Hệ quả: bronze cho phép **replay chính xác** "pipeline ngày 15/10 đã thấy gì", kể cả khi nguồn đã sửa dữ liệu. Partition theo ngày business thì mất khả năng đó.

---

## 4. Bẫy kỹ thuật

- **`to_parquet` vào thư mục đã có dữ liệu sẽ GHI THÊM, không thay thế.** Chạy script lần hai là file nhân đôi, số đo sai. Phải `shutil.rmtree(part, ignore_errors=True)` trước. Đây chính là vấn đề idempotency của Day 5.
- **`glob` vs `rglob`**: file partition nằm sâu 2 cấp (`year=2017/month=9/x.parquet`). `glob("*.parquet")` chỉ nhìn cấp một → đếm ra 0. Phải dùng `rglob`.
- **Thư mục không có `.stat().st_size` dùng được.** Tổng dung lượng phải cộng: `sum(f.stat().st_size for f in part.rglob("*.parquet"))`.
- Tiêu đề bảng nên ghi rõ điều kiện chạy (`"[1] Row group (sorted by price)"`) — đọc lại sau một tuần sẽ không nhầm với bảng chạy trên dữ liệu ngẫu nhiên.

---

## 5. Hai bài học lớn nhất

1. **Tối ưu không phải lúc nào cũng tối ưu.** Cả row group nhỏ lẫn partition mịn đều *làm chậm* trong thí nghiệm này. Cơ chế có hoạt động, nhưng chi phí lớn hơn lợi ích. Phải đo mới biết.
2. **Pushdown và partition pruning cần dữ liệu được tổ chức đúng mới ăn.** Biết Parquet *có* tính năng gì khác hẳn biết làm cho tính năng đó *chạy*.

---

## 6. Việc cho Day 5

- [ ] Ghép Parquet vào pipeline T9: bronze layer trên MinIO
- [ ] Partition theo `ingestion_date`
- [ ] Idempotency: chạy lại 1 ngày → overwrite đúng partition đó, không append trùng, không xoá ngày khác
- [ ] Tìm hiểu `existing_data_behavior="delete_matching"` trong `pq.write_to_dataset`