-- Tổng doanh thu theo tháng năm 2025
select d.month,d.month_name, sum(f.payment_value )
from fact_sales f
join dim_date d 
on d.date_key=f.date_key
where d.year in(2025)
group by d.month,,d.month_name
order by d.month
;
-- Top 3 sản phẩm doanh thu cao nhất theo quarter
select t.quarter, t.product_name, t.total_revenue
from
(select d.quarter, p.product_name, sum(f.payment_value) as total_revenue
,row_number() over (partition by d.quarter order by sum(f.payment_value) desc ) as rank
from fact_sales f
join dim_date d on d.date_key=f.date_key
join dim_product p on p.product_key=f.product_key
group by d.quarter, p.product_name

) as  t
where t.rank<=3
order by t.quarter, t.total_revenue desc;
-- Doanh thu theo segment khách hàng
select c.customer_segment, sum(f.payment_value) as total_revenue
from fact_sales f
join dim_customer c on c.customer_key=f.customer_key
group by c.customer_segment
order by total_revenue desc;

-- So sánh doanh thu weekday vs weekend
select 
case when d.is_weekend then 'Weekend' else 'Weekday' end as day_type
, sum(f.payment_value) as total_revenue
from fact_sales f
join dim_date d on d.date_key=f.date_key
group by day_type
order by day_type;
-- Đơn hàng ORD019 có bao nhiêu line items, tổng bao nhiêu?
select f.order_id, count(*) as line_item_count, sum(f.payment_value) as total_payment_value
from fact_sales f
where f.order_id='ORD019'
group by f.order_id;
-- So sánh quantity × unit_price vs payment_value — tìm rows có chênh lệch
select f.order_id, f.order_item_id, f.quantity, f.unit_price, f.payment_value
, f.quantity * f.unit_price as calculated_value
from fact_sales f
where f.quantity * f.unit_price != f.payment_value
order by f.order_id, f.order_item_id;