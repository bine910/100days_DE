-- Grain: 1 dòng = 1 product_id
with products as (
    select * from {{ ref('stg_olist__products') }}
)
select 
    product_id,
    product_category_name,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
from products