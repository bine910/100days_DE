--Grain: 1 dòng = 1 order_id. Dự kiến 99.441 dòng.
{{ config(
    materialized='incremental',
    unique_key='order_id'
) }}

with orders as (
    select * from {{ ref('stg_olist__orders') }}
    {% if is_incremental() %}
    where purchased_at > (select max(purchased_at) from {{ this }})
    {% endif %}
),

items_agg as (
    select
        order_id,
        count(*)           as item_count,
        sum(line_revenue)  as total_revenue
    from {{ ref('int_order_items_enriched') }}
    group by order_id
),

payments as (
    select * from {{ ref('int_order_payments_agg') }}
),

final as (
    select
        orders.order_id,
        orders.customer_id,
        orders.status,
        orders.purchased_at,
        orders.delivered_customer_at,
        orders.estimated_delivery_at,
        items_agg.item_count,
        items_agg.total_revenue,
        payments.total_payment_value,
        payments.payment_count
    from orders
    left join items_agg on orders.order_id = items_agg.order_id
    left join payments  on orders.order_id = payments.order_id
)
select * from final