with order_items as (
    select * from {{ ref('stg_olist__order_items') }}
),
products as (
    select * from {{ ref('stg_olist__products') }}
),
joined as (
    select
        order_items.order_id,
        order_items.order_item_id,
        order_items.product_id,
        order_items.seller_id,
        products.product_category_name,
        order_items.price,
        order_items.freight_value,
        order_items.price + order_items.freight_value as line_revenue
    from order_items
    left join products on order_items.product_id = products.product_id
)
select * from joined