# Week 6 — Dimensional Modeling: Star Schema + SCD Type 2

## Kiến thức chi tiết từ mentor

---

## 1. TẠI SAO CẦN DIMENSIONAL MODELING?

Tuần 5 đã học Relational Modeling — normalize đến 3NF, tối ưu cho **ghi dữ liệu** (OLTP). Nhưng khi phân tích dữ liệu (OLAP), normalized schema gây ra vấn đề lớn: một query báo cáo doanh thu phải JOIN 7-8 bảng, query chậm, khó đọc, khó maintain.

**Dimensional Modeling** (do Ralph Kimball phát triển) giải quyết đúng bài toán này: thiết kế schema **tối ưu cho đọc và phân tích**, chấp nhận dư thừa dữ liệu (denormalization có chủ đích) để query nhanh và trực quan.

### Vấn đề cụ thể của 3NF cho analytics

Ví dụ câu hỏi: "Tổng doanh thu theo từng danh mục sản phẩm, theo từng quý, trong năm 2024."

Trên 3NF cần JOIN 4 bảng: `order_items → orders → products → categories`. Mỗi câu hỏi business khác nhau = viết lại query từ đầu, JOIN khác nhau, logic lặp lại.

Ngoài ra, query analytics nặng chạy trên cùng database OLTP → **tranh chấp tài nguyên** với user đang đặt hàng. Response time tăng vọt cho tất cả user.

### Vấn đề của 1 bảng phẳng (flatten hết)

Nếu merge tất cả vào 1 bảng: Customer "Nguyễn Văn A" mua 500 đơn → tên, city, segment lặp 500 lần. Product "iPhone 15" bán 10.000 lần → tên, category lặp 10.000 lần. Bảng phình to, tốn storage, UPDATE một cái tên khách phải sửa hàng nghìn row.

### Giải pháp: tách "số đo" ra khỏi "mô tả"

- **Số đo (measures)**: quantity, price, total_amount — thứ thay đổi mỗi giao dịch, SUM/AVG được
- **Mô tả (attributes)**: customer name, city, product name, category — thứ tương đối ổn định, dùng lại nhiều lần

Tách thành **Fact Table** (số đo + FK) và **Dimension Tables** (mô tả). Đây là nền tảng của Dimensional Modeling.

---

## 2. FACT TABLE vs DIMENSION TABLE

### Fact Table

Chứa các **sự kiện đo lường được** (measurable events) — những thứ đã xảy ra trong business. Mỗi row là một sự kiện ở mức chi tiết nhất.

Cấu trúc fact table:
- **FK trỏ sang dimensions** — xác định ai, cái gì, khi nào, ở đâu
- **Measures** — con số SUM/AVG được
- **Degenerate dimensions** — dimension không cần bảng riêng (VD: order_id)

FK chính là thứ cho mỗi dòng giao dịch một "danh tính". Không có FK thì row chỉ là số vô nghĩa — không biết ai mua, mua gì, khi nào.

### Dimension Table

Chứa **ngữ cảnh mô tả** (descriptive context) cho sự kiện — trả lời câu hỏi **ai, cái gì, ở đâu, khi nào, như thế nào**.

### Quy tắc phân biệt

- **Fact = động từ** (bán, đặt, thanh toán, giao) → chứa số đo
- **Dimension = danh từ** (khách hàng, sản phẩm, ngày, cửa hàng) → chứa thuộc tính mô tả
- **Measure** = cột mà phép SUM / AVG / COUNT có ý nghĩa → quantity, unit_price, total_amount
- **Attribute** = cột text/label mô tả ngữ cảnh → customer_name, city, product_name, category_name

> Fact trả lời "**điều gì đã xảy ra và bao nhiêu?**", Dimension trả lời "**xảy ra với ai, cái gì, ở đâu và khi nào?**"

---

## 3. GRAIN

**Grain** (độ chi tiết) là câu trả lời cho: **"Mỗi row trong fact table đại diện cho cái gì?"**

Đây là quyết định thiết kế đầu tiên và quan trọng nhất khi xây star schema. Nếu chọn grain sai, toàn bộ schema sẽ sai theo.

### Ví dụ

- Grain = **1 dòng sản phẩm trong 1 đơn hàng** → `fact_order_line` (chi tiết nhất, linh hoạt nhất)
- Grain = **1 đơn hàng** → `fact_order` (mất thông tin từng sản phẩm)
- Grain = **doanh thu theo ngày theo cửa hàng** → `fact_daily_store_sales` (đã aggregate, mất khả năng drill-down)

### Tại sao grain "1 order" sai cho fact_sales

Khách A đặt 1 đơn hàng, mua 3 sản phẩm khác nhau. Nếu grain = "1 order" → chỉ có 1 row, vậy `product_key` trỏ sang sản phẩm nào? Không thể chọn được vì 1 row chỉ có 1 FK.

Nếu grain = "1 dòng sản phẩm trong 1 order" → 3 rows, mỗi row có đúng 1 `product_key`.

### Nguyên tắc Kimball

> **Chọn grain chi tiết nhất có thể (atomic grain).** Vì từ chi tiết có thể SUM lên tổng, nhưng từ tổng không thể tách ngược ra chi tiết.

### Grain statement

Viết thành 1 câu ngắn, đọc 1 lần hiểu ngay:

> "Mỗi row = một dòng sản phẩm trong một đơn hàng" (one order line item)

Seller, customer, date đã implicit qua FK — không cần liệt kê hết trong grain statement.

---

## 4. BA LOẠI MEASURE

### Additive

SUM được theo **mọi dimension**. Ví dụ: `quantity`, `payment_value`.

Tổng quantity theo customer ✅, theo product ✅, theo date ✅.

### Semi-additive

SUM được theo **một số dimension**, nhưng **không theo thời gian**. Ví dụ: `account_balance` (số dư tài khoản).

SUM balance theo chi nhánh → đúng (tổng tiền tất cả chi nhánh). SUM balance theo tháng → **vô nghĩa** (số dư tháng 1 + số dư tháng 2 không có ý nghĩa). Với semi-additive, theo thời gian phải dùng AVG hoặc lấy snapshot cuối kỳ.

### Non-additive

Không SUM được theo **bất kỳ dimension nào**. Ví dụ: `unit_price`, `ratio`, `percentage`. SUM giá đơn vị 3 sản phẩm lại = vô nghĩa. Chỉ dùng AVG, MIN, MAX.

### Cách phân biệt nhanh

- **Lượng phát sinh** mỗi giao dịch (bán bao nhiêu, thu bao nhiêu tiền) → **additive**
- **Trạng thái tại thời điểm** (số dư, tồn kho, nhiệt độ) → **semi-additive**
- **Ratio / percentage / average** → **non-additive**

### Best practice cho non-additive

Thay vì lưu `conversion_rate` trực tiếp, lưu tử số và mẫu số (`visitors`, `orders`) rồi tính `conversion_rate = SUM(orders) / SUM(visitors)` khi query. Lưu ratio trực tiếp vào fact thì không aggregate được.

---

## 5. STAR SCHEMA

### Cấu trúc

Fact table ở giữa, các dimension tables xung quanh nối trực tiếp qua FK. Nhìn từ trên xuống có hình ngôi sao.

```text
     dim_customer          dim_date
           \                 /
            \               /
             fact_sales
            /               \
           /                 \
     dim_product          dim_seller
```

### Đặc điểm quan trọng

- Dimension table **không normalize** — flatten hết. `dim_product` chứa cả `category_name` ngay trong bảng, không tách ra bảng `categories` riêng.
- Fact table chỉ chứa FK + measures, rất "gầy" về chiều ngang nhưng "dài" về số row.
- Query đơn giản: chỉ cần JOIN fact với 1-2 dimension là có kết quả.

### So sánh hiệu quả query

| Query | JOIN trên Star Schema | JOIN trên 3NF |
|---|---|---|
| Doanh thu theo tháng | 1 (dim_date) | 3 (order_items → orders → extract date) |
| Top sản phẩm theo quarter | 2 (dim_date + dim_product) | 4 (order_items → products → categories + orders) |
| Doanh thu theo segment | 1 (dim_customer) | 3 (order_items → orders → customers) |

**Star Schema giảm trung bình 50-70% số JOIN.**

---

## 6. STAR SCHEMA vs SNOWFLAKE SCHEMA

**Star Schema:** dimension tables flatten — `dim_product` chứa luôn `category_name` bên trong.

**Snowflake Schema:** dimension tables normalize tiếp — tách `dim_product` → `dim_category` → `dim_department`. Giảm dư thừa nhưng thêm JOIN.

```text
Star:      fact_sales → dim_product (có category bên trong)
Snowflake: fact_sales → dim_product → dim_category → dim_department
```

| Tiêu chí | Star | Snowflake |
|---|---|---|
| Dimension structure | Denormalized (flatten) | Normalized (tách tiếp) |
| Số JOIN | Ít | Nhiều |
| Readability | Dễ hiểu | Phức tạp hơn |
| Query performance | Nhanh hơn | Chậm hơn |
| Storage redundancy | Có dư thừa có chủ đích | Ít dư thừa |

Star phổ biến hơn vì dimension table thường nhỏ, denormalize không tốn bao nhiêu storage mà query nhanh hơn đáng kể.

---

## 7. SURROGATE KEY vs NATURAL KEY

Dimension table dùng **surrogate key** (integer auto-increment) làm PK, giữ natural key từ source system làm **business key**.

### Tại sao?

- **SCD Type 2 bắt buộc surrogate key** — cùng 1 customer_id có nhiều rows (nhiều version), cần PK riêng cho mỗi version
- **Performance** — integer JOIN nhanh hơn varchar JOIN trên hàng triệu fact rows
- **Independence** — data warehouse không phụ thuộc vào business logic của source system
- **Source system có thể thay đổi key** — hệ thống mới dùng UUID thay cho mã cũ

### Convention

```text
customer_key    ← PK (surrogate, auto-increment) — đứng đầu
customer_id     ← business key (từ source) — đứng sau
```

PK luôn đứng đầu trong table definition.

---

## 8. dim_date — DIMENSION ĐẶC BIỆT

`dim_date` là bảng **lịch (calendar)** — mô tả bản thân ngày đó, không liên quan đến bất kỳ đơn hàng nào.

### Tại sao cần bảng riêng?

`dim_date` chứa rất nhiều thuộc tính phái sinh mà SQL thuần tính rất tốn:

```text
date_key        -- 20240115 (integer, PK)
full_date       -- '2024-01-15'
day_of_week     -- 3 (ISODOW: 1=Mon, 7=Sun)
day_name        -- 'Wednesday'
day_of_month    -- 15
month           -- 1
month_name      -- 'January'
quarter         -- 1
year            -- 2024
is_weekend      -- FALSE
is_holiday      -- TRUE (custom theo quốc gia)
```

### Pre-generate

Generate cho 10-20 năm (chỉ ~3650 rows cho 10 năm), load 1 lần, dùng mãi. Nên generate **cả ngày tương lai** (ít nhất 3-5 năm tới) vì:
- Fact table có thể chứa `expected_delivery_date` — ngày chưa đến
- Pipeline chạy ngày mai mà `date_key` ngày mai chưa tồn tại → FK constraint fail

### Lợi ích

Query "doanh thu Q3 các ngày không phải cuối tuần" → chỉ cần `JOIN dim_date WHERE quarter = 3 AND is_weekend = FALSE`. Không cần EXTRACT hay CASE WHEN.

### dim_date KHÔNG phải bảng order

**Sai:** đưa `order_id`, `order_status` vào dim_date.
**Đúng:** dim_date chỉ chứa thuộc tính của bản thân ngày. Order info nằm trong fact table.

---

## 9. DEGENERATE DIMENSION

Dimension **nằm trực tiếp trong fact table**, không có bảng dimension riêng.

### Khi nào dùng?

Khi dimension chỉ có 1 cột ID, không có attributes đi kèm. Tạo `dim_order` chỉ để chứa `order_id` thì lãng phí.

### Ví dụ

- `order_id` trong `fact_sales` — dùng GROUP BY tất cả line items cùng 1 đơn hàng
- `order_status` — ít giá trị (pending/shipped/delivered/canceled), không cần bảng riêng

### Đặc điểm quan trọng

Degenerate dimension **KHÔNG SUM được**. `order_id = 'ORD019'` — SUM vô nghĩa. Nó là dimension (mô tả, GROUP BY, filter), chỉ là không cần bảng riêng.

---

## 10. DATA TYPES CHO STAR SCHEMA

### Nguyên tắc

Chọn data type **chính xác nhất** — integer cho số nguyên, numeric cho tiền, date cho ngày, boolean cho true/false. VARCHAR chỉ dùng khi giá trị thực sự là text.

### Quy tắc tuyệt đối: tiền dùng NUMERIC, không dùng FLOAT

FLOAT lưu số theo binary floating point — không thể biểu diễn chính xác nhiều số thập phân:

```sql
SELECT 0.1::FLOAT + 0.2::FLOAT;
-- Kết quả: 0.30000000000000004 (không phải 0.3)

SELECT 0.1::NUMERIC + 0.2::NUMERIC;
-- Kết quả: 0.3 (chính xác)
```

SUM hàng triệu dòng với FLOAT → tổng cuối sai hàng triệu đồng.

### Bảng data types

| Cột | Data type | Lý do |
|---|---|---|
| surrogate key (PK) | `BIGINT GENERATED ALWAYS AS IDENTITY` | Auto-increment, không cho user tự insert |
| business key | `VARCHAR` | Có thể chứa "C001", "P0042" |
| date_key | `INTEGER` | 20240115, range scan nhanh |
| full_date | `DATE` | Kiểu ngày chuyên dụng, hỗ trợ date functions |
| is_weekend | `BOOLEAN` | TRUE/FALSE |
| quantity | `INTEGER` | Số nguyên, không có 0.5 cái iPhone |
| unit_price | `NUMERIC(12,2)` | Tiền phải dùng NUMERIC |
| payment_value | `NUMERIC(12,2)` | Tiền phải dùng NUMERIC |

---

## 11. SCD — SLOWLY CHANGING DIMENSION

### Bài toán

Dimension thay đổi theo thời gian. Khách hàng A ban đầu ở Hà Nội, sau chuyển vào Hồ Chí Minh. Đơn hàng cũ nên gắn với "Hà Nội" hay "Hồ Chí Minh"?

### SCD Type 0 — Retain Original

Không cập nhật gì. Giá trị lúc insert đầu tiên giữ mãi. Dùng cho thuộc tính không bao giờ nên đổi (ngày sinh).

### SCD Type 1 — Overwrite

Ghi đè giá trị mới lên cũ. Mất hoàn toàn lịch sử. Đơn hàng cũ mua ở Hanoi nhưng query ra HCM → **sai sự thật**. Phù hợp khi lịch sử không quan trọng (sửa lỗi chính tả, cập nhật email).

### SCD Type 2 — Add New Row

Tạo row mới trong dimension, giữ nguyên row cũ. **Giữ lịch sử đầy đủ.** Phổ biến nhất trong data warehouse.

#### 3 cột cần thêm

| Cột | Mục đích |
|---|---|
| `effective_date` | Version này bắt đầu có hiệu lực từ ngày nào |
| `expiry_date` | Version này hết hiệu lực ngày nào (`9999-12-31` = current) |
| `is_current` | TRUE/FALSE — shortcut để query version mới nhất |

#### Ví dụ

CUST001 chuyển từ Hanoi → HCM ngày 2025-07-01:

```text
customer_key | customer_id | city             | effective  | expiry     | is_current
101          | CUST001     | Hanoi            | 2025-01-01 | 2025-06-30 | FALSE
102          | CUST001     | Ho Chi Minh City | 2025-07-01 | 9999-12-31 | TRUE
```

Đơn hàng cũ (trước 01/07) vẫn JOIN với `customer_key = 101` → "Hà Nội".
Đơn hàng mới JOIN với `customer_key = 102` → "Hồ Chí Minh".

#### Logic xử lý (trong 1 transaction)

```sql
BEGIN;

-- Bước 1: Expire row hiện tại
UPDATE dim_customer
SET expiry_date = DATE '2025-06-30',    -- ngày trước effective mới
    is_current  = FALSE
WHERE customer_id = 'CUST001'
  AND is_current = TRUE;                 -- chỉ update row đang active

-- Bước 2: Insert version mới
INSERT INTO dim_customer (
    customer_id, customer_name, customer_email,
    customer_city, customer_state, customer_zip,
    customer_segment, effective_date, expiry_date, is_current
)
VALUES (
    'CUST001', 'Nguyen An', 'an.nguyen@example.com',
    'Ho Chi Minh City', 'HCM', '700000',
    'Consumer', DATE '2025-07-01', DATE '9999-12-31', TRUE
);

COMMIT;
```

#### 5 quy tắc quan trọng

1. **Không overlap:** `expiry` row cũ = `effective` row mới − 1 ngày
2. **Không gap:** ngày liên tiếp không bỏ sót
3. **Surrogate key bắt buộc:** cùng 1 business key có nhiều row
4. **Fact JOIN tự động đúng:** FK trỏ đến version tại thời điểm giao dịch
5. **INSERT phải copy toàn bộ attribute:** row mới là version độc lập

#### Query tại thời điểm

```sql
-- City của CUST001 vào ngày 2025-03-15
SELECT customer_city
FROM dim_customer
WHERE customer_id = 'CUST001'
  AND effective_date <= DATE '2025-03-15'
  AND expiry_date    >= DATE '2025-03-15';
-- Kết quả: Hanoi
```

#### Khi nào Type 1 vs Type 2

- Attribute thay đổi nhưng lịch sử **không quan trọng** (email, SĐT) → Type 1
- Attribute thay đổi và lịch sử **ảnh hưởng đến phân tích** (city, segment) → Type 2
- Cùng 1 dimension có thể mix: email dùng Type 1, city dùng Type 2

### SCD Type 3 — Add New Column

Thêm cột `previous_city` bên cạnh `current_city`. Chỉ giữ được đúng 1 lần thay đổi. Nếu đổi lần 2 thì `previous_city` bị ghi đè → mất lịch sử lần 1. Ít dùng trong thực tế.

---

## 12. INMON vs KIMBALL

### Kimball (Bottom-up)

Xây Star Schema (dimensional model) cho từng business process trước → nhanh ra report, team nhỏ thấy giá trị ngay.

Nhược: nếu 2 phòng ban thiết kế `dim_customer` khác nhau → dữ liệu không nhất quán. Giải pháp: **conformed dimensions** + **Bus Matrix**.

### Inmon (Top-down)

Xây Enterprise Data Warehouse chuẩn 3NF trước → mọi phòng ban dùng chung 1 nguồn sự thật.

Nhược: mất 6-12 tháng setup trước khi ai đó thấy được report đầu tiên.

### So sánh

| Tiêu chí | Kimball | Inmon |
|---|---|---|
| Approach | Bottom-up: từng business process | Top-down: enterprise warehouse trước |
| Tốc độ ra kết quả | Nhanh | Chậm ban đầu |
| Consistency | Phụ thuộc conformed dimensions | Cao từ đầu |
| Team size | Nhỏ-trung | Lớn, có governance mạnh |
| Medallion mapping | Gold layer | Silver layer |

### Thực tế hiện đại: Hybrid

Medallion Architecture chính là hybrid:

```text
Bronze (raw data)       → dữ liệu thô
Silver (cleaned, 3NF)   → Inmon ở đây
Gold (star schema)      → Kimball ở đây
```

Silver giữ data nhất quán, Gold phục vụ report nhanh. Hai trường phái bổ sung cho nhau ở hai layer khác nhau.

---

## 13. EDGE CASES

### Default Dimension Row (key = -1)

**Vấn đề:** pipeline ETL load đơn hàng từ khách mới, nhưng `dim_customer` chưa có khách này → FK constraint fail → pipeline crash → data mất.

**Giải pháp:** tạo sẵn 1 row "Unknown" trong mỗi dimension với `key = -1`. Khi pipeline gặp dimension chưa tồn tại → gán `key = -1` thay vì crash. Đơn hàng vẫn được load, doanh thu không mất.

### Late Arriving Dimension

Khi dimension data đến sau, pipeline chạy lại sẽ:
1. INSERT dimension row thật
2. UPDATE fact rows từ `key = -1` sang key thật

### Monitoring

Query đếm fact rows có `customer_key = -1` — count này nên trending toward zero.

---

## 14. BUS MATRIX

Ánh xạ business processes (fact tables) × dimensions. Dimensions dùng chung gọi là **conformed dimensions** — thiết kế 1 lần, dùng nhất quán.

|                    | dim_customer | dim_product | dim_date | dim_seller | dim_return_reason |
|--------------------|:---:|:---:|:---:|:---:|:---:|
| **fact_sales**     | ✅  | ✅  | ✅  | ✅  |     |
| **fact_returns**   | ✅  | ✅  | ✅  | ✅  | ✅  |

Conformed dimensions đảm bảo "Customer A" có cùng nghĩa trong sales report và returns report.

---

## 15. MEDALLION ↔ KIMBALL MAPPING

```text
Bronze (Raw)
  Dữ liệu thô từ source: CSV, JSON, API response
  Không transform, không clean
  Giữ nguyên để trace ngược
       ↓
Silver (Cleaned / 3NF-like)
  Deduplicate, validated, type-cast
  Normalized — thiết kế tuần 5
  Single source of truth (tư duy Inmon)
       ↓
Gold (Star Schema)
  Dimensional model — thiết kế tuần 6
  Denormalized, tối ưu cho BI/report
  Kimball fact + dimension
```

**Key insight:** Tuần 5 (3NF) = Silver, Tuần 6 (Star Schema) = Gold. Không đối lập mà bổ sung cho nhau ở hai layer khác nhau trong cùng một pipeline.

---

## 16. QUERY PATTERNS TRÊN STAR SCHEMA

### Pattern cơ bản

```sql
SELECT
    dim_attributes,
    AGG(measures)
FROM fact_table
JOIN dim_table ON fact.key = dim.key
WHERE dim_attributes = filter
GROUP BY dim_attributes
ORDER BY ...
```

### Lợi thế so với 3NF

- **1-2 JOIN** thay vì 3-4 JOIN
- **dim_date pre-compute** → không cần EXTRACT/CASE WHEN
- **Degenerate dimension** → query trực tiếp trên fact, 0 JOIN
- **Boolean flags** (`is_weekend`) → query đọc như tiếng Anh

### Ví dụ: weekday vs weekend

```sql
-- Star Schema: đọc như tiếng Anh
SELECT
    CASE WHEN d.is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    SUM(f.payment_value) AS total_revenue
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY day_type;

-- 3NF: phải tính lại mỗi lần
WHERE EXTRACT(DOW FROM order_date) NOT IN (0, 6)
```

---

## 17. SQL CONVENTIONS CHO STAR SCHEMA

### Seed data: dùng JOIN thay vì hardcode surrogate key

```sql
-- Đúng: dùng business key trong VALUES, JOIN lấy surrogate key
INSERT INTO fact_sales (customer_key, product_key, ...)
SELECT c.customer_key, p.product_key, ...
FROM (VALUES ('CUST001', 'PROD001', ...)) AS v(customer_id, product_id, ...)
JOIN dim_customer c ON c.customer_id = v.customer_id
JOIN dim_product p ON p.product_id = v.product_id;
```

Đây là cách ETL pipeline thực tế hoạt động — source data không bao giờ biết surrogate key.

### Idempotency

```sql
ON CONFLICT (order_id, order_item_id) DO UPDATE SET ...
```

Chạy script 10 lần cũng không duplicate. Pipeline chạy lại an toàn.

### Enforce grain bằng constraint

```sql
CONSTRAINT uq_fact_sales_order_item
    UNIQUE (order_id, order_item_id)
```

Nếu ETL load trùng → constraint báo lỗi ngay thay vì duplicate data âm thầm.

### payment_value ở item grain

Trong source system, payment thường ở order level. Khi load vào fact table với item-level grain, phải phân bổ xuống từng item. `payment_value` có thể ≠ `quantity × unit_price` vì discount, voucher, shipping allocation.