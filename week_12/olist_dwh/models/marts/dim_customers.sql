-- Grain: 1 dòng = 1 customer_id
with customers as (
    select * from {{ ref('stg_olist__customers') }}
)
select
    customer_id,
    customer_unique_id,
    zip_code_prefix,
    city,
    state
from customers