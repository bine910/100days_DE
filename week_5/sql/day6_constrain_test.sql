-- 1. INSERT order với customer_id không tồn tại   
INSERT INTO orders (order_id,customer_id,order_date,order_status) 
VALUES (11,6,NOW(),'Pending');
-- 2. INSERT order_item với quantity = 0               → CHECK violation
INSERT INTO order_items (order_id, product_id, seller_id, quantity, unit_price)
VALUES (1, 3, 1, 0, 199.99);
-- 3. INSERT customer trùng email                      → UNIQUE violation
INSERT INTO customers (customer_id,customer_name,email,city,state,zip_code,created_at)
 VALUES (6,'David Wilson','john.doe@example.com','Miami','FL','33101',NOW());
-- 4. INSERT review với score = 6                      → CHECK violation
INSERT INTO reviews (review_id,order_id,review_score,review_comment,review_created_at) 
VALUES (6,1,6,'Excellent product!',NOW());
-- 5. DELETE customer đang có orders                   → RESTRICT violation
DELETE FROM customers WHERE customer_id = 1;