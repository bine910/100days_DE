# Data Lake vs Data Warehouse — Ghi chú tuần 8

## 1. OLTP vs OLAP

### OLTP (Online Transaction Processing)
- Phục vụ **thao tác hàng ngày** của ứng dụng (CRUD, API)
- Query động vào **ít dòng** (WHERE id = 42)
- Ghi nhiều, đọc ít — INSERT/UPDATE liên tục
- Cần **ACID** — transaction phải all-or-nothing
- Schema **normalized (3NF)** — tách bảng để tránh duplicate khi ghi
- Ví dụ: PostgreSQL phục vụ NestJS API

### OLAP (Online Analytical Processing)
- Phục vụ **phân tích business** (báo cáo, dashboard)
- Query quét **hàng triệu dòng** (SUM, GROUP BY, aggregate)
- Đọc nhiều, ghi ít — batch load rồi query
- Không cần ACID chặt — data load xong mới query
- Schema **denormalized (Star Schema)** — gộp data để đọc nhanh, giảm JOIN
- Ví dụ: BigQuery, Snowflake

### Tại sao không chạy query phân tích trên production?
- Query OLAP chiếm **shared buffer (RAM)** → đẩy cache API ra → API chậm
- **Seq Scan** trên triệu dòng → lock I/O disk
- Chiếm **connection pool** → API hết connection → timeout
- Nói gọn: OLTP và OLAP **tranh nhau CPU, RAM, I/O** → phải tách ra

### ACID giải quyết vấn đề gì?
- Đảm bảo data **không rơi vào trạng thái nửa vời**
- Không chỉ cho chuyển tiền — bất kỳ thao tác nào cần nhiều bước ghi all-or-nothing
- **A**tomicity: thành công hết hoặc rollback hết
- **C**onsistency: data luôn đúng constraint
- **I**solation: transaction này không thấy transaction kia đang làm dở
- **D**urability: COMMIT rồi thì không mất dù mất điện
- Ví dụ: đặt hàng = INSERT order + UPDATE stock → thiếu 1 cái = bán quá kho

### Tại sao OLAP dùng Star Schema thay vì 3NF?
- 3NF phải JOIN 5-6 bảng → mỗi JOIN là hash join/nested loop tốn tài nguyên
- Star Schema: fact_sales JOIN 1 dim nhỏ (vài nghìn dòng) → gần như miễn phí
- OLAP engine lưu data **columnar** → SUM(amount) chỉ đọc cột amount, bỏ qua cột khác
- Star Schema + columnar = **nhanh gấp 10-100x** so với 3NF trên OLTP

### Data Engineer đóng vai trò gì?
- Xây **pipeline tự động**: Extract từ OLTP → Transform (3NF → Star) → Load vào OLAP
- Thiết kế data flow: data đi từ đâu đến đâu
- Đảm bảo chất lượng: data đúng, đủ, không trùng
- Monitor: pipeline fail → alert → fix → chạy lại

---

## 2. Data Warehouse

### Khái niệm
- Hệ thống lưu trữ **thiết kế riêng cho phân tích**
- Data phải có **schema trước** khi load (schema-on-write)
- Tối ưu cho SQL query phân tích trên dữ liệu lớn

### Kiến trúc 3 tầng
```
Tầng 3: SERVING    → Dashboard, BI tools, SQL query (Metabase, Looker)
Tầng 2: INTEGRATION → Transform, clean, 3NF → Star Schema (dbt, Python)
Tầng 1: STAGING     → Raw data từ sources, chưa transform
```

### Compute & Storage Separation
- **Truyền thống** (Oracle): compute + storage gắn liền → mua server đắt
- **Hiện đại** (BigQuery): tách riêng → storage rẻ, compute bật khi cần
- Lưu 10TB nhưng query 1 lần/ngày → chỉ trả storage rẻ + compute 5 phút
- BigQuery tính tiền theo **data scanned**, không theo server 24/7

### Trải nghiệm BigQuery thực tế
- Query scan **418.96 MB** (hàng chục triệu dòng) trong **365ms** — PostgreSQL local sẽ mất vài giây đến hàng chục giây
- Kết quả được **cache** → chạy lại query giống = 0 bytes, miễn phí
- Không cần tạo index, không cần EXPLAIN — managed service lo hết

---

## 3. Data Lake

### Khái niệm
- Kho chứa file — throw bất kỳ thứ gì vào: CSV, JSON, Parquet, ảnh, log
- **Schema-on-read** — không cần define schema lúc lưu, đọc lúc nào define lúc đó
- Rẻ hơn warehouse nhiều (chỉ tính tiền storage thuần)

### So sánh Data Lake vs Data Warehouse

| Tiêu chí | Data Warehouse | Data Lake |
|----------|---------------|-----------|
| Giống như | Tủ hồ sơ — mỗi ngăn có nhãn | Nhà kho — quăng hàng vào |
| Schema | Schema-on-write (define trước) | Schema-on-read (define khi đọc) |
| Data type | Chỉ structured (bảng, cột) | Mọi thứ: structured, semi, unstructured |
| Chi phí | Đắt (compute + storage) | Rẻ (chỉ storage) |
| Query | SQL cực nhanh | Cần engine riêng (Spark, Presto) |

### Tại sao pipeline ETL cần Data Lake?

**Lý do 1 — Transform sai thì còn data gốc chạy lại**
- Không có raw → phải gọi lại API → rate limit, data đã thay đổi, không tái tạo được
- Có raw → sửa code transform, chạy lại từ raw → xong 10 phút

**Lý do 2 — Source không phải lúc nào cũng available**
- API sập, đổi format, hết quota
- CSV đối tác gửi 1 lần rồi xóa
- Raw data = bảo hiểm

**Lý do 3 — Nhiều team dùng cùng raw data**
- BI → transform theo Star Schema
- Data Science → dùng raw JSON train model
- Compliance → giữ bản gốc 5 năm theo luật

### Object Storage — nền tảng Data Lake
- Không có folder thật — chỉ key-value (key = đường dẫn, value = file)
- Mỗi object **immutable** — ghi xong không sửa, chỉ ghi đè hoặc version mới
- Scale gần vô hạn
- **MinIO** = bản open-source, API giống AWS S3 → học local, deploy cloud không đổi code