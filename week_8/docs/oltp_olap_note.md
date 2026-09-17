# OLTP vs OLAP

## 1. Tại sao không chạy query phân tích trên database production?

Database production thường phục vụ **OLTP (Online Transaction Processing)**. Nhiệm vụ chính của nó là xử lý các transaction của ứng dụng một cách nhanh chóng, ví dụ:

- Tạo đơn hàng
- Cập nhật tồn kho
- Thanh toán
- Đăng nhập
- Cập nhật thông tin khách hàng

Trong khi đó, các query phân tích của **OLAP (Online Analytical Processing)** thường đọc và xử lý một lượng dữ liệu rất lớn.

Ví dụ:

```sql
SELECT
    SUM(amount)
FROM orders
GROUP BY month;
```

Nếu bảng `orders` có hàng triệu dòng, database có thể phải thực hiện **Seq Scan**, tức là đọc lần lượt một lượng rất lớn dữ liệu từ bảng.

Điều này gây ra tranh chấp tài nguyên với các request của ứng dụng:

- **I/O:** phải đọc rất nhiều dữ liệu từ disk.
- **RAM:** dữ liệu được đưa qua các vùng memory/buffer, có thể cạnh tranh với dữ liệu production cần cache.
- **CPU:** phải xử lý aggregation trên hàng triệu dòng.

Kết quả là các transaction bình thường của ứng dụng có thể bị chậm. API có thể gặp **timeout**, connection pool có thể bị chiếm hết, thậm chí ảnh hưởng đến toàn bộ ứng dụng.

Nói ngắn gọn:

> **OLTP và OLAP tranh nhau CPU, RAM và I/O trên cùng một hệ thống.**

Vì vậy, production database thường không phải nơi phù hợp để chạy các query phân tích nặng.

---

## 2. ACID giải quyết vấn đề gì?

ACID là tập hợp các tính chất giúp database đảm bảo transaction được thực hiện **đúng và nhất quán**, đặc biệt khi một thao tác gồm nhiều bước ghi dữ liệu.

ACID gồm:

- **Atomicity:** transaction hoặc thành công toàn bộ, hoặc thất bại toàn bộ.
- **Consistency:** dữ liệu phải chuyển từ một trạng thái hợp lệ sang một trạng thái hợp lệ khác.
- **Isolation:** các transaction đồng thời không làm dữ liệu rơi vào trạng thái không nhất quán.
- **Durability:** khi transaction đã commit, dữ liệu không bị mất do lỗi thông thường của hệ thống.

### Ví dụ: đặt hàng trong e-commerce

Giả sử user mua một sản phẩm còn 1 sản phẩm trong kho.

Hệ thống cần:

```text
1. INSERT order
2. INSERT order_item
3. UPDATE product SET stock = stock - 1
```

Nếu bước 1 thành công nhưng bước 3 thất bại thì sẽ xảy ra vấn đề:

```text
Order đã tồn tại
      ↓
Nhưng stock chưa bị trừ
      ↓
Hệ thống có thể bán quá số lượng thực tế
```

Transaction giúp các bước này được xử lý như **một đơn vị công việc**:

```text
BEGIN

    INSERT order
    INSERT order_item
    UPDATE stock

COMMIT
```

Nếu có lỗi:

```text
ROLLBACK
```

thì các thay đổi của transaction được hoàn tác.

Một ví dụ khác là nạp tiền:

```text
1. INSERT payment_transaction
2. UPDATE user_balance
```

Nếu chỉ ghi được một bước thì dữ liệu có thể trở nên sai: giao dịch đã tồn tại nhưng balance chưa được cập nhật, hoặc ngược lại.

Vì vậy:

> **ACID giúp các thao tác nhiều bước không để database rơi vào trạng thái "nửa vời".**

ACID không chỉ quan trọng với tiền. Nó hữu ích cho bất kỳ nghiệp vụ nào mà **nhiều thay đổi dữ liệu phải thành công cùng nhau hoặc thất bại cùng nhau**.

---

## 3. Tại sao OLAP dùng Denormalized Schema (Star Schema) thay vì 3NF?

Trong OLTP, **3NF (Third Normal Form)** thường được sử dụng để giảm redundancy và tránh các vấn đề khi INSERT, UPDATE, DELETE.

Ví dụ dữ liệu có thể được tách thành:

```text
orders
order_items
products
categories
customers
dates
```

Cách này phù hợp với transaction vì mỗi loại dữ liệu được quản lý ở một nơi.

Nhưng với OLAP, mục tiêu chính lại là **đọc và phân tích dữ liệu nhanh**.

### Vấn đề của 3NF khi phân tích

Giả sử muốn tính:

> Tổng doanh thu theo category.

Trong schema 3NF, có thể phải đi qua nhiều bảng:

```text
orders
   ↓
order_items
   ↓
products
   ↓
categories
```

Database phải thực hiện nhiều JOIN để lấy đủ thông tin.

Khi dữ liệu rất lớn, những JOIN này có thể trở nên tốn tài nguyên.

### Star Schema

OLAP thường tổ chức dữ liệu theo **Star Schema**:

```text
             dim_customer
                  |
                  |
dim_date ---- fact_sales ---- dim_product
                  |
                  |
             dim_store
```

Trong đó:

- `fact_sales`: chứa các sự kiện/số liệu cần phân tích.
- `dim_product`: thông tin sản phẩm.
- `dim_customer`: thông tin khách hàng.
- `dim_date`: thông tin thời gian.
- `dim_store`: thông tin cửa hàng.

Ví dụ `fact_sales` có thể chứa:

```text
sale_id
date_key
product_key
customer_key
amount
quantity
```

Muốn tính doanh thu theo category, có thể thực hiện:

```text
fact_sales
    ↓
JOIN dim_product
    ↓
GROUP BY category
```

Thay vì phải JOIN qua nhiều bảng nghiệp vụ như trong hệ thống 3NF.

### Tại sao denormalization phù hợp với OLAP?

OLAP ưu tiên **đọc nhanh** hơn việc tối ưu cho các thao tác INSERT/UPDATE.

Ngoài ra, các hệ thống OLAP hiện đại như BigQuery hoặc Snowflake thường sử dụng **columnar storage**.

Ví dụ:

```sql
SELECT SUM(amount)
FROM fact_sales;
```

Nếu dữ liệu được lưu theo cột, hệ thống có thể tập trung đọc cột `amount` thay vì phải đọc toàn bộ các cột khác.

Vì vậy có thể hiểu:

```text
Star Schema
     +
Columnar Storage
     +
Massive parallel processing
     ↓
Phù hợp với analytical query
```

Một điểm quan trọng:

> Không nên hiểu rằng Star Schema luôn nhanh hơn 3NF trong mọi trường hợp. Nó được thiết kế để phù hợp với workload phân tích: đọc nhiều dữ liệu, aggregation nhiều và thường ít transaction cập nhật từng dòng.

---

## 4. Data Engineer đóng vai trò gì giữa OLTP và OLAP?

Data Engineer không đơn giản là "chuyển database production sang database phân tích".

Vai trò chính là **xây dựng data pipeline** để đưa dữ liệu từ hệ thống phục vụ ứng dụng sang hệ thống phục vụ phân tích một cách an toàn và tự động.

Một flow đơn giản:

```text
                    OLTP
              (Production DB)
                     |
                     | Extract
                     ↓
              Raw / Staging Data
                     |
                     | Transform
                     ↓
              Data Warehouse
                (OLAP)
                     |
                     ↓
          BI / Dashboard / Analytics
```

### 1. Extract

Lấy dữ liệu từ OLTP mà hạn chế ảnh hưởng đến production.

Ví dụ:

```text
PostgreSQL Production
        ↓
     Extract
        ↓
    Raw data
```

Có thể sử dụng các phương pháp như batch processing hoặc CDC tùy hệ thống.

### 2. Transform

Data Engineer làm sạch và biến đổi dữ liệu:

```text
Raw data
   ↓
Clean
   ↓
Validate
   ↓
Transform
   ↓
Business logic
```

Một phần quan trọng là chuyển dữ liệu từ mô hình phục vụ transaction sang mô hình phục vụ phân tích:

```text
OLTP
3NF
 ↓
Transform
 ↓
OLAP
Star Schema
```

Ví dụ:

```text
orders
order_items
products
categories
```

có thể được biến đổi thành:

```text
fact_sales
dim_product
dim_category
dim_date
```

### 3. Load

Đưa dữ liệu đã xử lý vào hệ thống OLAP/Data Warehouse.

Ví dụ:

```text
Production PostgreSQL
        ↓
       ETL/ELT
        ↓
Data Warehouse
        ↓
   BI / Analytics
```

### 4. Data Quality

Data Engineer cũng phải đảm bảo dữ liệu:

- Đúng
- Đủ
- Không bị duplicate
- Không bị mất dữ liệu
- Đúng kiểu dữ liệu
- Đúng business rule

Ví dụ:

```text
fact_sales.amount < 0
```

có thể là một vấn đề cần được phát hiện tùy theo business rule.

### 5. Monitoring

Pipeline phải chạy tự động và có khả năng phát hiện lỗi.

Ví dụ:

```text
Daily Pipeline
      ↓
Extract
      ↓
Transform
      ↓
Load
      ↓
   Success
```

Nếu pipeline fail:

```text
Pipeline failed
      ↓
    Alert
      ↓
  Investigate
      ↓
     Fix
      ↓
    Retry
```

---

## Tổng kết

Có thể hình dung toàn bộ hệ thống như sau:

```text
                APPLICATION
                     |
                     ↓
              ┌─────────────┐
              │    OLTP     │
              │ Production  │
              │    3NF      │
              └──────┬──────┘
                     |
                Data Pipeline
              Extract / Transform
                     |
                     ↓
              ┌─────────────┐
              │    OLAP     │
              │ Data        │
              │ Warehouse   │
              │ Star Schema │
              └──────┬──────┘
                     |
                     ↓
             BI / Analytics
             / Dashboard
             / Reporting
```

### Mental model

**OLTP hỏi:**

> "Đơn hàng này có được tạo thành công không?"

**OLAP hỏi:**

> "Doanh thu tháng này là bao nhiêu? Category nào bán nhiều nhất? Doanh thu thay đổi thế nào theo thời gian?"

**Data Engineer xây cây cầu giữa hai bên:**

> **Lấy dữ liệu từ OLTP → xử lý → đưa vào OLAP → đảm bảo pipeline và dữ liệu luôn đáng tin cậy.**
