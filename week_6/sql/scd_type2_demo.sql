-- =========================================================
-- SCD TYPE 2 DEMO — dim_customer
--
-- Demonstrates Slowly Changing Dimension Type 2:
-- when a dimension attribute changes, the current row is
-- expired and a new row is inserted, preserving full history.
-- =========================================================


-- =========================================================
-- 1. ADD SCD2 COLUMNS TO dim_customer
-- =========================================================

ALTER TABLE dim_customer
ADD COLUMN IF NOT EXISTS effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
ADD COLUMN IF NOT EXISTS expiry_date    DATE NOT NULL DEFAULT DATE '9999-12-31',
ADD COLUMN IF NOT EXISTS is_current     BOOLEAN NOT NULL DEFAULT TRUE;


-- =========================================================
-- 2. BACKFILL SCD2 DEFAULTS FOR EXISTING ROWS
--
-- All existing customers are treated as the first known
-- version, effective from 2025-01-01 (the earliest order
-- date in seed data).
-- =========================================================

UPDATE dim_customer
SET effective_date = DATE '2025-01-01',
    expiry_date    = DATE '9999-12-31',
    is_current     = TRUE
WHERE effective_date = CURRENT_DATE;


-- =========================================================
-- 3. SCD TYPE 2 SCENARIO
--
-- CUST001 (Nguyen An) moves from Hanoi → Ho Chi Minh City
-- on 2025-07-01.
--
-- Step 1: Expire the current row (set end date and flag).
-- Step 2: Insert new version with the updated city.
--
-- After this, CUST001 has 2 rows:
--   Key 101 | Hanoi          | 2025-01-01 → 2025-06-30 | FALSE
--   Key 102 | Ho Chi Minh City | 2025-07-01 → 9999-12-31 | TRUE
--
-- Orders placed before 2025-07-01 still JOIN to the Hanoi
-- row because fact_sales.customer_key points to key 101.
-- =========================================================

BEGIN;

-- Step 1: Expire the current version
UPDATE dim_customer
SET expiry_date = DATE '2025-06-30',
    is_current  = FALSE
WHERE customer_id = 'CUST001'
  AND is_current = TRUE;

-- Step 2: Insert new version
INSERT INTO dim_customer (
    customer_id,
    customer_name,
    customer_email,
    customer_city,
    customer_state,
    customer_zip,
    customer_segment,
    effective_date,
    expiry_date,
    is_current
)
VALUES (
    'CUST001',
    'Nguyen An',
    'an.nguyen@example.com',
    'Ho Chi Minh City',
    'HCM',
    '700000',
    'Consumer',
    DATE '2025-07-01',
    DATE '9999-12-31',
    TRUE
);

COMMIT;


-- =========================================================
-- 4. VERIFICATION QUERIES
-- =========================================================

-- Q1: List all versions of CUST001
-- Expected: 2 rows — Hanoi (expired) + HCM (current)

SELECT
    customer_key,
    customer_id,
    customer_city,
    effective_date,
    expiry_date,
    is_current
FROM dim_customer
WHERE customer_id = 'CUST001'
ORDER BY effective_date;


-- Q2: What city was CUST001 in on 2025-03-15?
-- Expected: Hanoi (falls within 2025-01-01 → 2025-06-30)

SELECT customer_city
FROM dim_customer
WHERE customer_id = 'CUST001'
  AND effective_date <= DATE '2025-03-15'
  AND expiry_date    >= DATE '2025-03-15';


-- Q3: Revenue by customer city
-- Old orders (before 2025-07-01) → customer_key points
-- to the Hanoi version.
-- New orders (after 2025-07-01) → customer_key points
-- to the HCM version.
-- No date logic needed — the FK handles it automatically.

SELECT
    c.customer_city,
    SUM(f.payment_value) AS total_revenue
FROM fact_sales f
JOIN dim_customer c ON c.customer_key = f.customer_key
GROUP BY c.customer_city
ORDER BY total_revenue DESC;