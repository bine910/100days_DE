# Dimensional Modeling Concepts

## 1. Fact vs Dimension

Trong Dimensional Modeling, **fact table** lưu các sự kiện kinh doanh có thể đo lường được, còn **dimension table** mô tả ngữ cảnh của các sự kiện đó.

Một cách nhớ đơn giản là:

- **Fact = động từ / hành động xảy ra**
- **Dimension = danh từ / đối tượng mô tả hành động đó**

Ví dụ trong hệ thống e-commerce:

- Customer **places** an order
- Customer **buys** a product
- Seller **sells** a product

Các hành động như `buy`, `sell`, `place order` thường dẫn tới fact table.

Ví dụ:

```text
fact_sales
- date_key
- customer_key
- product_key
- seller_key
- quantity
- sales_amount
```

Các đối tượng như `Customer`, `Product`, `Seller`, `Date` trở thành dimension:

```text
dim_customer
dim_product
dim_seller
dim_date
```

Dimension thường chứa các thuộc tính dùng để filter, group hoặc mô tả fact, ví dụ:

```text
product_category
customer_city
customer_state
seller_state
month
year
```

Nói ngắn gọn:

> Fact trả lời câu hỏi **“điều gì đã xảy ra và bao nhiêu?”**, còn Dimension trả lời **“xảy ra với ai, cái gì, ở đâu và khi nào?”**.

---

## 2. Grain

**Grain** xác định chính xác **một row trong fact table đại diện cho điều gì**.

Đây là quyết định phải đưa ra trước khi chọn dimension và measure, vì nếu grain không rõ thì rất dễ trộn dữ liệu ở nhiều mức chi tiết khác nhau và làm sai kết quả aggregate.

Với `fact_sales`, grain có thể được khai báo như sau:

> **"Mỗi row = một dòng sản phẩm trong một đơn hàng**

Ví dụ:

```text
Order O001
- Product A -> 200
- Product B -> 300
```

thì `fact_sales` sẽ có hai row, không phải một row cho toàn bộ order.

Tôi chọn **atomic grain**, tức mức chi tiết thấp nhất hợp lý mà source data cung cấp.

Lý do:

1. Có thể aggregate lên các mức cao hơn như order, ngày, tháng, category hoặc seller.
2. Giữ được nhiều khả năng phân tích hơn.
3. Không thể đi ngược từ dữ liệu đã aggregate để khôi phục chi tiết đã mất.
4. Giảm nguy cơ trộn measure ở order-level với item-level.

Ví dụ từ item-level:

```text
order item
   ↓
order
   ↓
day
   ↓
month
```

Có thể aggregate đi lên, nhưng nếu chỉ lưu monthly sales thì không thể biết từng order hoặc từng product đã tạo ra doanh thu đó.

---

## 3. Measure Types

Measure là các giá trị số nằm trong fact table và được dùng để tính toán hoặc aggregate.

| Loại | Đặc điểm | Ví dụ |
|---|---|---|
| **Additive** | Có thể cộng qua tất cả các dimension | `sales_amount`, `quantity`, `freight_value` |
| **Semi-additive** | Có thể cộng qua một số dimension nhưng không phải tất cả, thường không cộng được qua time | `account_balance`, `inventory_level` |
| **Non-additive** | Không thể cộng trực tiếp một cách có ý nghĩa | `conversion_rate`, `percentage`, `average_price` |

### Additive

Ví dụ:

```text
Jan sales = 100
Feb sales = 200
```

Có thể tính:

```text
Total sales = 300
```

Sales là **lượng phát sinh trong một khoảng thời gian**, nên cộng các khoảng lại vẫn có ý nghĩa.

### Semi-additive

Ví dụ inventory:

```text
01/09: inventory = 100
02/09: inventory = 80
03/09: inventory = 70
```

Không thể tính:

```text
100 + 80 + 70 = 250 inventory
```

vì inventory là **trạng thái tại một thời điểm**, không phải lượng phát sinh.

Tuy nhiên, tại cùng một thời điểm, có thể cộng inventory của nhiều warehouse hoặc nhiều product nếu business meaning cho phép.

### Non-additive

Ví dụ:

```text
Store A conversion rate = 10%
Store B conversion rate = 20%
```

Không thể cộng:

```text
10% + 20% = 30%
```

Với các ratio hoặc percentage, nên lưu các thành phần gốc nếu có thể.

Ví dụ thay vì chỉ lưu:

```text
conversion_rate
```

nên lưu:

```text
visitors
orders
```

và tính:

```text
conversion_rate = SUM(orders) / SUM(visitors)
```

### Cách phân biệt nhanh

Một câu hỏi hữu ích là:

> Giá trị này là **lượng phát sinh trong khoảng thời gian** hay **trạng thái tại một thời điểm**?

- Lượng phát sinh: thường additive  
  Ví dụ: revenue, quantity sold, number of orders.
- Trạng thái tại thời điểm: thường semi-additive  
  Ví dụ: account balance, stock level.
- Ratio / percentage / average: thường non-additive.

---

## 4. Star Schema vs Snowflake

### Star Schema

Trong Star Schema, fact table nằm ở trung tâm và nối trực tiếp với các dimension đã được denormalize.

Ví dụ:

```text
                  dim_date
                     |
                     |
dim_customer -- fact_sales -- dim_product
                     |
                     |
                 dim_seller
```

`dim_product` có thể chứa trực tiếp:

```text
product_name
category
subcategory
brand
```

### Snowflake Schema

Snowflake tiếp tục normalize dimension.

Ví dụ:

```text
fact_sales
    |
dim_product
    |
dim_category
    |
dim_department
```

Thay vì để category và department trong cùng `dim_product`, chúng được tách thành các bảng riêng.

### Khác biệt chính

| Star Schema | Snowflake Schema |
|---|---|
| Dimension thường denormalized | Dimension được normalize thêm |
| Ít JOIN hơn | Nhiều JOIN hơn |
| Dễ hiểu hơn với analyst | Quan hệ phức tạp hơn |
| Query đơn giản hơn | Query thường dài hơn |
| Có một mức redundancy có chủ đích | Giảm redundancy hơn |

### Tại sao Star Schema phổ biến hơn?

Trong analytics, mục tiêu chính không phải loại bỏ mọi redundancy mà là:

- dễ hiểu;
- dễ query;
- giảm số lượng JOIN;
- thuận tiện cho BI tools;
- làm business logic rõ ràng hơn.

Storage hiện nay thường rẻ hơn nhiều so với chi phí của một data model khó sử dụng.

Vì vậy Star Schema thường chấp nhận một lượng duplication có kiểm soát để đổi lấy usability và query simplicity.

Snowflake vẫn hữu ích khi dimension rất lớn, có hierarchy phức tạp hoặc có lý do mạnh để tái sử dụng các sub-dimension.

---

## 5. Inmon vs Kimball

Inmon và Kimball đều nhằm xây dựng hệ thống dữ liệu phục vụ analytics, nhưng cách tiếp cận khác nhau.

| Tiêu chí | Kimball | Inmon |
|---|---|---|
| **Approach** | Bottom-up: bắt đầu từ từng business process và xây dimensional data marts | Top-down: xây enterprise data warehouse trước rồi tạo data marts |
| **Tốc độ ra kết quả** | Nhanh hơn vì có thể triển khai từng mart độc lập | Chậm hơn ban đầu vì cần thiết kế mô hình enterprise trước |
| **Consistency** | Phụ thuộc nhiều vào conformed dimensions và governance giữa các marts | Consistency cao hơn từ đầu vì dữ liệu đi qua một integrated enterprise model |
| **Team size phù hợp** | Phù hợp team nhỏ hoặc vừa, cần delivery nhanh và incremental | Phù hợp tổ chức lớn, nhiều domain và có data architecture/governance mạnh |
| **Mapping với Medallion** | Gần với Gold layer: dimensional marts, fact và dimension phục vụ BI | Gần với Silver/Core layer: dữ liệu tích hợp, chuẩn hóa trước khi tạo downstream marts |

### Cách tôi hiểu hai hướng

Kimball:

```text
Business Process
      ↓
Dimensional Mart
      ↓
Fact + Dimension
      ↓
BI / Analytics
```

Ví dụ:

```text
Sales
Orders
Inventory
```

được xây từng phần, nhưng dùng các dimension thống nhất như `dim_customer`, `dim_product`, `dim_date`.

Inmon:

```text
Sources
   ↓
Enterprise Data Warehouse
   ↓
Integrated / Normalized Core
   ↓
Data Marts
```

Inmon ưu tiên một cái nhìn thống nhất cho toàn doanh nghiệp trước khi phục vụ từng nhóm analytics.

Trong kiến trúc hiện đại, hai cách không nhất thiết loại trừ nhau.

Ví dụ với Medallion:

```text
Bronze
Raw data
   ↓
Silver
Cleaned / integrated core
   ↓
Gold
Dimensional marts
Fact + Dimension
```

Có thể xem Silver mang một phần tư duy giống Inmon, trong khi Gold thường áp dụng tư duy Kimball.

Vì vậy trong thực tế, một hệ thống có thể kết hợp cả hai thay vì chọn hoàn toàn một phía.
