-- Mỗi (order_id, order_item_id) chỉ được xuất hiện 1 lần
select
    order_id,
    order_item_id,
    count(*) as n_records
from {{ ref('stg_olist__order_items') }}
group by order_id, order_item_id
having count(*) > 1