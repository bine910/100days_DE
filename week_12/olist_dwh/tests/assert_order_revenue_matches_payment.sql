-- Với đơn thanh toán 1 lần, không trả góp: doanh thu hàng phải khớp số tiền trả.
-- Loại trừ trả góp (payment_installments > 1) vì lãi được cộng vào payment.
with orders as (
    select * from {{ ref('fct_orders') }}
),
single_payment as (
    select order_id, payment_installments
    from {{ ref('stg_olist__order_payments') }}
    where payment_installments <= 1
)
select
    orders.order_id,
    orders.total_revenue,
    orders.total_payment_value,
    abs(orders.total_revenue - orders.total_payment_value) as diff
from orders
join single_payment on single_payment.order_id = orders.order_id
where orders.total_revenue is not null
  and orders.total_payment_value is not null
  and orders.payment_count = 1
  and abs(orders.total_revenue - orders.total_payment_value) > 0.01