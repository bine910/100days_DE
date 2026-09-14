# T5.5 — Denormalization & Engineering Trade-offs

## Tại sao cần denormalize?

Normalized schema (3NF) tối ưu cho **data integrity** — ít redundancy, không anomaly. Nhưng analytics query thường phải JOIN nhiều bảng → chậm khi data lớn.

**Ví dụ**: query "Revenue theo category, theo tháng" trên schema 3NF:

```sql
SELECT
    c.category_name,
    DATE_TRUNC('month', o.order_date) AS month,
    SUM(oi.quantity * oi.unit_price) AS revenue
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN products p ON oi.product_id = p.product_id
JOIN categories c ON p.category_id = c.category_id
WHERE o.order_date >= '2024-01-01'
GROUP BY c.category_name, month;
```

→ **4 JOINs** cho 1 câu hỏi business.

---

## Denormalized table

Gộp data từ nhiều bảng vào 1 bảng phẳng:

```
sales_report
────────────────────────
customer_id        FK
customer_name      ← duplicate từ customers
category_id        FK
category_name      ← duplicate từ categories
seller_id          FK
seller_name        ← duplicate từ sellers
payment_value      ← từ payments
order_date         ← từ orders
```

Cùng câu hỏi, query trở thành:

```sql
SELECT
    category_name,
    DATE_TRUNC('month', order_date) AS month,
    SUM(payment_value) AS revenue
FROM sales_report
WHERE order_date >= '2024-01-01'
GROUP BY category_name, month;
```

→ **0 JOINs**. Nhanh hơn, analyst tự query được.

---

## Trade-off matrix

|                    | Normalized (3NF)                 | Denormalized                          |
| ------------------ | -------------------------------- | ------------------------------------- |
| **Redundancy**     | Thấp                            | Cao                                   |
| **Write**          | Nhanh, an toàn                  | Phức tạp (update nhiều chỗ)           |
| **Read/Query**     | Chậm (nhiều JOINs)              | Nhanh (ít/không JOIN)                 |
| **Data integrity** | Cao (constraints enforce)        | Rủi ro inconsistency                  |
| **Storage**        | Tiết kiệm                       | Tốn hơn                              |
| **Use case**       | OLTP (transactions, write-heavy) | OLAP (analytics, reporting, read-heavy)|

---

## Risk: Update Anomaly quay lại

Nếu customer đổi tên:

- **Bảng `customers` (normalized)**: sửa **1 row** → xong.
- **Bảng `sales_report` (denormalized)**: `customer_name` lặp ở **mọi row** customer đó từng mua. 50 orders = 50 rows cần update. Quên update → dashboard hiển thị tên cũ, bảng `customers` hiển thị tên mới → **inconsistency**.

**Giải pháp trong thực tế DE**: không update từng row mà **rebuild toàn bộ** `sales_report` từ normalized tables theo schedule (daily/hourly) bằng ETL pipeline hoặc dbt model.

---

## Key takeaway

```
Normalize  → protect data integrity    → OLTP, write-heavy
Denormalize → optimize query performance → OLAP, read-heavy
```

DE pipeline dùng **cả hai**:

```
Silver layer = normalized (3NF)    → đảm bảo data đúng
Gold layer   = denormalized        → phục vụ dashboard/BI
```

---

## Nguyên tắc

 "It depends on workload and system requirements."