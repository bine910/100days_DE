-- 1. Revenue by category
Select c.category_name,
         SUM(oi.quantity * oi.unit_price) AS total_revenue
FROM categories c
JOIN products p ON c.category_id = p.category_id
JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY c.category_name;

-- 2. Top 3 customers by total spending
Select cu.customer_name,
         SUM(oi.quantity * oi.unit_price) AS total_spending
FROM customers cu
JOIN orders o ON cu.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY cu.customer_name
ORDER BY total_spending DESC
LIMIT 3;
-- 3. Revenue by seller
Select s.seller_name,
         SUM(oi.quantity * oi.unit_price) AS total_revenue
FROM sellers s
JOIN order_items oi ON s.seller_id = oi.seller_id
GROUP BY s.seller_name
ORDER BY total_revenue DESC;
-- 4. Average order value
SELECT AVG(order_total) AS average_order_value
FROM (
    SELECT o.order_id,
           SUM(oi.quantity * oi.unit_price) AS order_total
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY o.order_id
) order_totals;
