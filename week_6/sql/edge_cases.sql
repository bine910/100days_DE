-- =========================================================
-- EDGE CASES — Default Dimension Rows + Late Arriving Data
--
-- Problem:
-- ETL pipeline loads fact rows before the corresponding
-- dimension exists (e.g. new customer not yet in dim).
-- FK constraint rejects the INSERT → pipeline crashes
-- → data is lost.
--
-- Solution:
-- Pre-insert an "Unknown" row (key = -1) in every
-- dimension. When a dimension lookup misses, the pipeline
-- assigns key = -1 instead of crashing. The fact row is
-- saved; the FK is corrected later when the dimension
-- arrives ("late arriving dimension").
-- =========================================================


-- =========================================================
-- 1. DEFAULT DIMENSION ROWS (key = -1)
-- =========================================================

-- dim_customer
INSERT INTO dim_customer (
    customer_key, customer_id, customer_name, customer_email,
    customer_city, customer_state, customer_zip, customer_segment,
    effective_date, expiry_date, is_current
)
OVERRIDING SYSTEM VALUE
VALUES (
    -1, 'UNKNOWN', 'Unknown Customer', NULL,
    'Unknown', 'Unknown', 'Unknown', 'Unknown',
    DATE '1900-01-01', DATE '9999-12-31', TRUE
)
ON CONFLICT (customer_key) DO NOTHING;


-- dim_product
INSERT INTO dim_product (
    product_key, product_id, product_name, category
)
OVERRIDING SYSTEM VALUE
VALUES (
    -1, 'UNKNOWN', 'Unknown Product', 'Unknown'
)
ON CONFLICT (product_key) DO NOTHING;


-- dim_seller
INSERT INTO dim_seller (
    seller_key, seller_id, seller_city, seller_state, seller_zip
)
OVERRIDING SYSTEM VALUE
VALUES (
    -1, 'UNKNOWN', 'Unknown', 'Unknown', 'Unknown'
)
ON CONFLICT (seller_key) DO NOTHING;


-- dim_date
-- Date key -1 represents an unknown or missing date.
INSERT INTO dim_date (
    date_key, full_date, day_of_week, day_name, day_of_month,
    month, month_name, quarter, year, is_weekend, is_holiday
)
VALUES (
    -1, DATE '1900-01-01', 1, 'Unknown', 1,
    1, 'Unknown', 1, 1900, FALSE, FALSE
)
ON CONFLICT (date_key) DO NOTHING;


-- =========================================================
-- 2. VERIFICATION: FIND FACTS WITH UNKNOWN DIMENSIONS
--
-- In a healthy warehouse, these counts should be zero
-- or trending toward zero as late dimensions arrive.
-- =========================================================

-- Count fact rows pointing to Unknown customer
SELECT
    'Unknown Customer' AS issue,
    COUNT(*) AS affected_rows
FROM fact_sales
WHERE customer_key = -1

UNION ALL

-- Count fact rows pointing to Unknown product
SELECT
    'Unknown Product',
    COUNT(*)
FROM fact_sales
WHERE product_key = -1

UNION ALL

-- Count fact rows pointing to Unknown seller
SELECT
    'Unknown Seller',
    COUNT(*)
FROM fact_sales
WHERE seller_key = -1

UNION ALL

-- Count fact rows pointing to Unknown date
SELECT
    'Unknown Date',
    COUNT(*)
FROM fact_sales
WHERE date_key = -1

ORDER BY affected_rows DESC;


-- =========================================================
-- 3. LATE ARRIVING DIMENSION — FIX WORKFLOW
--
-- When the real dimension data arrives later, update
-- the fact rows that were pointing to the Unknown row.
--
-- Example: CUST099 arrives in source system after the
-- fact was already loaded with customer_key = -1.
-- =========================================================

-- Step 1: Insert the real dimension row
-- INSERT INTO dim_customer (customer_id, customer_name, ...)
-- VALUES ('CUST099', 'New Customer', ...);

-- Step 2: Fix fact rows that were pointing to Unknown
-- UPDATE fact_sales f
-- SET customer_key = c.customer_key
-- FROM dim_customer c
-- WHERE c.customer_id = 'CUST099'
--   AND f.customer_key = -1
--   AND f.order_id IN (
--       -- identify which orders belong to CUST099
--       -- from a staging/lookup table
--   );