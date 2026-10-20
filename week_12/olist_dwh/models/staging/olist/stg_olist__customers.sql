with source as (
    select * from {{ source('olist', 'customers') }}
),
renamed as (
    select
        customer_id,
        customer_unique_id,
        cast(customer_zip_code_prefix as text) as zip_code_prefix,
        upper(trim(customer_city))             as city,
        upper(trim(customer_state))            as state
    from source
)
select * from renamed