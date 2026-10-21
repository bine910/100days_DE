with order_payments as (
    select * from {{ ref('stg_olist__order_payments') }}
),
aggregated as(
    select 
      order_payments.order_id,
        sum(order_payments.payment_value) as total_payment_value,
        count(*) as payment_count
        from order_payments
        group by order_payments.order_id
)
select * from aggregated