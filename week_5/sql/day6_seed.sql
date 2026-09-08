BEGIN;

INSERT INTO customers (customer_id,customer_name,email,city,state,zip_code,created_at) 
VALUES (1,'John Doe','john.doe@example.com','New York','NY','10001',NOW()),
(2,'Jane Smith','jane.smith@example.com','Los Angeles','CA','90210',NOW()),
(3,'Bob Johnson','bob.johnson@example.com','Chicago','IL','60601',NOW()),
(4,'Alice Brown','alice.brown@example.com','Houston','TX','77001',NOW()),
(5,'Charlie Davis','charlie.davis@example.com','Phoenix','AZ','85001',NOW())
ON CONFLICT (customer_id) 
DO UPDATE SET 
customer_name= EXCLUDED.customer_name,
email= EXCLUDED.email,
city= EXCLUDED.city,
state= EXCLUDED.state,
zip_code= EXCLUDED.zip_code,
created_at= EXCLUDED.created_at
;

INSERT INTO categories (category_id,category_name,created_at) 
VALUES (1,'Electronics',NOW()),
(2,'Books',NOW()),
(3,'Clothing',NOW())
on conflict (category_id)
DO UPDATE SET
category_name= EXCLUDED.category_name,
created_at= EXCLUDED.created_at;

INSERT INTO sellers (seller_id,seller_name,seller_city,seller_state,seller_zip_code,created_at)
VALUES (1,'Best Buy','Richfield','MN','55423',NOW()),
(2,'Barnes & Noble','New York','NY','10001',NOW()),
(3,'Macy''s','New York','NY','10001',NOW()),
(4,'Walmart','Bentonville','AR','72716',NOW()),
(5,'Target','Minneapolis','MN','55403',NOW())
on conflict (seller_id)
DO UPDATE SET
seller_name= EXCLUDED.seller_name,
seller_city= EXCLUDED.seller_city,
seller_state= EXCLUDED.seller_state,
seller_zip_code= EXCLUDED.seller_zip_code,
created_at= EXCLUDED.created_at;

INSERT INTO products (product_id,category_id,product_name,weight,length,height,width)
VALUES (1,1,'Smartphone',0.3,5.5,2.8,0.3),
(2,1,'Laptop',4.5,13.3,9.0,0.8),
(3,2,'Novel',0.5,8.0,5.0,1.0),
(4,2,'Textbook',2.0,11.0,8.5,1.5),
(5,3,'T-shirt',0.2,10.0,8.0,0.1)
on conflict (product_id)
DO UPDATE SET
category_id= EXCLUDED.category_id,
product_name= EXCLUDED.product_name,
weight= EXCLUDED.weight,
length= EXCLUDED.length,
height= EXCLUDED.height,
width= EXCLUDED.width;

INSERT INTO orders (order_id,customer_id,order_date,rorder_status)
VALUES (1,1,NOW()),
(2,2,NOW(),'Pending'),
(3,3,NOW(),'Shipped'),
(4,4,NOW(),'Delivered'),
(5,5,NOW(),'Pending'),
(6,1,NOW(),'Processing'),
(7,2,NOW(),'Shipped'),
(8,3,NOW(),'Delivered'),
(9,4,NOW(),'Pending'),
(10,5,NOW())
on conflict (order_id)
DO UPDATE SET
customer_id= EXCLUDED.customer_id,
order_date= EXCLUDED.order_date,
rorder_status= EXCLUDED.rorder_status;

INSERT INTO order_items (order_id,product_id,seller_id,quantity,unit_price)
VALUES 
(1,1,1,1,199.99),
(2,2,1,1,49.99),
(3,3,2,1,29.99),
(4,4,2,1,99.99),
(5,5,3,1,149.99),
(6,1,1,1,79.99),
(7,2,1,1,59.99),
(8,3,2,1,39.99),
(9,4,2,1,89.99),
(10,5,3,1,129.99),
(1,2,1,2,49.99),
(2,3,2,3,29.99),
(3,4,2,1,99.99),
(4,5,3,1,149.99),
(5,1,1,1,79.99),
(6,2,1,1,59.99),
(7,3,2,1,39.99),
(8,4,2,1,89.99),
(9,5,3,1,129.99)
on conflict (order_id,product_id)
DO UPDATE SET
order_id= EXCLUDED.order_id,
product_id= EXCLUDED.product_id,
seller_id= EXCLUDED.seller_id,
quantity= EXCLUDED.quantity,
unit_price= EXCLUDED.unit_price;

Insert INTO payments (payment_id,order_id,payment_type,payment_installments,payment_value)
VALUES (1,1,'credit card',1,199.99),
(2,2,'debit card',1,49.99),
(3,3,'paypal',1,29.99),
(4,4,'credit card',1,99.99),
(5,5,'bank transfer',1,149.99),
(6,6,'credit card',1,79.99),
(7,7,'debit card',1,59.99),
(8,8,'paypal',1,39.99),
(9,9,'credit card',1,89.99),
(10,10,'bank transfer',1,129.99)
on conflict (payment_id)
DO UPDATE SET
payment_type= EXCLUDED.payment_type,
payment_installments= EXCLUDED.payment_installments,
payment_value= EXCLUDED.payment_value;

INSERT INTO reviews (review_id,order_id,review_score,review_comment,review_created_at)
VALUES (1,1,5,'Great product!',NOW()),
(2,2,4,'Good value for money.',NOW()),
(3,3,5,'Highly recommended!',NOW()),
(4,4,4,'Satisfied with the purchase.',NOW()),
(5,5,5,'Excellent quality.',NOW())
on conflict (review_id)
DO UPDATE SET
order_id= EXCLUDED.order_id,
review_score= EXCLUDED.review_score,
review_comment= EXCLUDED.review_comment,
review_created_at= EXCLUDED.review_created_at;

COMMIT;
