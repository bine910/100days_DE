# Star Schema Design

## 1. Grain Statement

**Mỗi row trong `fact_sales` đại diện cho một dòng sản phẩm trong một đơn hàng.**

Ví dụ, nếu một order có 3 sản phẩm thì `fact_sales` sẽ có 3 row.

```text
fact_sales
├── customer_key (FK)
├── product_key (FK)
├── date_key (FK)
├── seller_key (FK)
├── order_id
├── order_status
├── quantity
├── unit_price
└── payment_value
```

Chọn grain ở mức order item giúp giữ dữ liệu ở mức chi tiết thấp và có thể aggregate lên order, ngày, tháng, seller hoặc product category khi cần.

---

## 2. Measures

| Measure | Type | Giải thích |
|---|---|---|
| `quantity` | Additive | Có thể cộng theo product, customer, seller và time. |
| `unit_price` | Non-additive | Không nên `SUM(unit_price)` để tính doanh thu; cần kết hợp với `quantity`. |
| `payment_value` | Additive* | Có thể cộng nếu giá trị payment đã được phân bổ đúng xuống grain của từng order item. |

Ví dụ doanh thu:

```text
sales_amount = quantity × unit_price
```

> **Lưu ý về grain:** trong Olist, payment thường tồn tại ở cấp order/payment chứ không phải order item. Nếu đưa nguyên `payment_value` của cả order vào từng item thì sẽ bị duplicate. Khi đó nên phân bổ payment xuống item grain hoặc tách sang một fact table riêng như `fact_payments`.

---

## 3. Dimensions

### `dim_customer`

```text
customer_key (PK)
customer_id (BK)
name
email
city
state
zip
```

Dùng để phân tích sales theo customer và location, ví dụ revenue theo city hoặc state.

### `dim_product`

```text
product_key (PK)
product_id (BK)
name
category
```

Dùng để phân tích sales theo product và product category.

`category` được **flatten trực tiếp vào `dim_product`** thay vì tạo thêm `dim_category` vì Star Schema ưu tiên mô hình đơn giản, ít JOIN và dễ sử dụng cho analytics.

### `dim_date`

```text
date_key (PK)
full_date
day_of_week
day_of_month
month
month_name
quarter
year
is_weekend
is_holiday
```

Dùng để phân tích dữ liệu theo thời gian mà không phải tính lại các thuộc tính calendar trong mỗi query.

### `dim_seller`

```text
seller_key (PK)
seller_id (BK)
city
state
zip
```

Dùng để phân tích performance của seller và sales theo khu vực của seller.

---

## 4. Degenerate Dimensions

Một **degenerate dimension** là dimension không có bảng riêng mà được giữ trực tiếp trong fact table.

### `order_id`

`order_id` không phải measure vì không thể `SUM()` và cũng không cần tạo `dim_order` chỉ để chứa một ID.

Vì vậy nó nằm trực tiếp trong `fact_sales`:

```text
fact_sales.order_id
```

Nó hữu ích khi cần group hoặc drill-down tất cả sản phẩm thuộc cùng một order.

### `order_status`

Trong thiết kế đơn giản này, `order_status` cũng được giữ trực tiếp trong `fact_sales` vì chỉ có một số ít giá trị như:

```text
pending
shipped
delivered
canceled
```

Không cần tạo một dimension riêng nếu không có thêm descriptive attributes.

> Về thuật ngữ Kimball, `order_id` là ví dụ degenerate dimension điển hình. `order_status` về mặt chặt chẽ thường được xem là một low-cardinality attribute và đôi khi có thể đưa vào junk dimension. Ở schema nhỏ này, giữ trực tiếp trong fact là đủ đơn giản và thực dụng.
## 5. Bus Matrix

Bus Matrix ánh xạ các business process (fact table) với các dimension dùng chung.
Dimension xuất hiện ở nhiều fact table gọi là **conformed dimension** —
thiết kế một lần, dùng nhất quán across toàn bộ warehouse.

|                    | dim_customer | dim_product | dim_date | dim_seller | dim_return_reason |
|--------------------|:---:|:---:|:---:|:---:|:---:|
| **fact_sales**     | ✅  | ✅  | ✅  | ✅  |     |
| **fact_returns**   | ✅  | ✅  | ✅  | ✅  | ✅  |

`dim_customer`, `dim_product`, `dim_date`, `dim_seller` là conformed —
definition giống nhau dù truy cập từ sales hay returns.

`dim_return_reason` chỉ có ý nghĩa trong context đổi trả
(lỗi sản phẩm, sai size, đổi ý...), không liên quan đến sales.

---

## 6. Medallion Architecture Mapping

```text
Bronze (Raw)
  Dữ liệu thô: CSV, JSON, API response
  Không transform, giữ nguyên để trace ngược
  VD: raw/orders.csv, raw/customers.json
       ↓
Silver (Cleaned / 3NF)
  Deduplicate, validate, type-cast
  Normalized — thiết kế tuần 5
  Single source of truth (tư duy Inmon)
  VD: cleaned/customers, cleaned/orders, cleaned/order_items
       ↓
Gold (Star Schema)
  Dimensional model — thiết kế tuần 6
  Denormalized, tối ưu cho BI/report
  Kimball fact + dimension
  VD: mart/fact_sales, mart/dim_customer, mart/dim_product
```

Tuần 5 (3NF) và tuần 6 (Star Schema) không đối lập —
chúng phục vụ **hai layer khác nhau** trong cùng một pipeline:

- **Silver = Inmon** — normalized, integrated, consistent
- **Gold = Kimball** — denormalized, fast, analyst-friendly