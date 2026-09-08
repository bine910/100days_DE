Entity: Customer

Purpose:
Đại diện cho một khách hàng thực hiện đơn hàng trên hệ thống e-commerce.

Attributes:
- customer_id
- customer_name        (optional)
- email                (optional)
- city
- state
- zip_code

Identifier:
- customer_id

Relationships:
- 1:N với Order

Entity: Order

Purpose:
Đại diện cho một giao dịch/đơn đặt hàng được tạo bởi một khách hàng.

Attributes:
- order_id
- customer_id
- order_date
- order_status

Identifier:
- order_id

Relationships:
- N:1 với Customer
- 1:N với OrderItem

Entity: OrderItem

Purpose:
Đại diện cho một sản phẩm cụ thể được mua trong một đơn hàng,
bao gồm số lượng và giá bán tại thời điểm mua.

Attributes:
- order_id
- product_id
- seller_id
- quantity
- unit_price

Identifier:
- (order_id, product_id)

Relationships:
- N:1 với Order
- N:1 với Product

Entity: Product

Purpose:
Đại diện cho một sản phẩm được bán trên marketplace.

Attributes:
- product_id
- product_name
- category
- weight
- length
- height
- width

Identifier:
- product_id

Relationships:
- 1:N với OrderItem

Entity: Seller

Purpose:
Đại diện cho một người bán hoặc cửa hàng cung cấp sản phẩm trên marketplace.

Attributes:
- seller_id
- seller_city
- seller_state
- seller_zip_code

Identifier:
- seller_id

Relationships:
- 1:N với OrderItem

Entity: Payment

Purpose:
Đại diện cho một lần hoặc một phương thức thanh toán được sử dụng cho một order.

Attributes:
- payment_id
- order_id
- payment_type
- payment_installments
- payment_value

Identifier:
- payment_id

Relationships:
- N:1 với Order

Entity: Review

Purpose:
Đại diện cho đánh giá của khách hàng về một order sau khi mua hàng.

Attributes:
- review_id
- order_id
- review_score
- review_comment
- review_created_at

Identifier:
- review_id

Relationships:
- N:1 với Order