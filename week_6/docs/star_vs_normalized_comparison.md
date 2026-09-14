# Star Schema vs Normalized Schema

## Query Q1

**Business question:** Doanh thu theo product category và tháng.

### Star Schema

```sql
SELECT
    d.year,
    d.month,
    p.category,
    SUM(f.payment_value) AS revenue
FROM fact_sales f
JOIN dim_date d
    ON f.date_key = d.date_key
JOIN dim_product p
    ON f.product_key = p.product_key
GROUP BY
    d.year,
    d.month,
    p.category
ORDER BY
    d.year,
    d.month,
    p.category;
```

**Số JOIN:** 2

Luồng đọc query khá trực tiếp:

```text
fact_sales
   ├── dim_date
   └── dim_product
```

`payment_value` nằm trong fact, còn `month`, `year`, `category` nằm trong dimension tương ứng. Query gần với cách business đặt câu hỏi: **SUM revenue BY month, category**.

---

## Normalized Schema

Ví dụ với schema 3NF:

```text
orders
order_items
products
categories
payments
```

Query tương đương có thể cần:

```sql
SELECT
    EXTRACT(YEAR FROM o.order_date) AS year,
    EXTRACT(MONTH FROM o.order_date) AS month,
    c.category_name,
    SUM(p.payment_value) AS revenue
FROM orders o
JOIN order_items oi
    ON o.order_id = oi.order_id
JOIN products pr
    ON oi.product_id = pr.product_id
JOIN categories c
    ON pr.category_id = c.category_id
JOIN payments p
    ON o.order_id = p.order_id
GROUP BY
    EXTRACT(YEAR FROM o.order_date),
    EXTRACT(MONTH FROM o.order_date),
    c.category_name;
```

**Số JOIN:** 4

Dữ liệu phải đi qua nhiều entity trước khi đến được `category` và `payment_value`.

---

## Comparison

| Tiêu chí | Star Schema | Normalized Schema |
|---|---|---|
| Số JOIN | 2 | 4 |
| Cấu trúc query | Ngắn, trực tiếp | Nhiều bước hơn |
| Readability | Gần với business question | Cần hiểu quan hệ giữa nhiều operational tables |
| Analytics | Thuận tiện cho aggregation | Không phải mục tiêu thiết kế chính |

Star Schema không có nghĩa là `JOIN` luôn xấu. Điểm chính là dimensional model tổ chức dữ liệu theo **business process**, nên analytical query thường ít JOIN hơn và dễ đọc hơn.
