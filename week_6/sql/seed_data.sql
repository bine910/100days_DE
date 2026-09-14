BEGIN;

-- =========================================================
-- 0. SCHEMA PATCH
-- Required for customer segmentation analysis.
-- =========================================================

ALTER TABLE dim_customer
ADD COLUMN IF NOT EXISTS customer_segment VARCHAR(50);


-- =========================================================
-- 1. DIM_CUSTOMER
-- 6 customers, 3 cities, 3 segments
-- =========================================================

INSERT INTO dim_customer (
    customer_id,
    customer_name,
    customer_email,
    customer_city,
    customer_state,
    customer_zip,
    customer_segment
)
VALUES
    ('CUST001', 'Nguyen An',   'an.nguyen@example.com',   'Hanoi',            'HN',  '100000', 'Consumer'),
    ('CUST002', 'Tran Binh',   'binh.tran@example.com',   'Hanoi',            'HN',  '100000', 'Corporate'),
    ('CUST003', 'Le Chi',      'chi.le@example.com',      'Da Nang',          'DN',  '550000', 'Consumer'),
    ('CUST004', 'Pham Dung',   'dung.pham@example.com',   'Da Nang',          'DN',  '550000', 'Home Office'),
    ('CUST005', 'Hoang Giang', 'giang.hoang@example.com', 'Ho Chi Minh City', 'HCM', '700000', 'Corporate'),
    ('CUST006', 'Vo Hanh',     'hanh.vo@example.com',     'Ho Chi Minh City', 'HCM', '700000', 'Consumer')
ON CONFLICT (customer_id) DO UPDATE
SET
    customer_name = EXCLUDED.customer_name,
    customer_email = EXCLUDED.customer_email,
    customer_city = EXCLUDED.customer_city,
    customer_state = EXCLUDED.customer_state,
    customer_zip = EXCLUDED.customer_zip,
    customer_segment = EXCLUDED.customer_segment;


-- =========================================================
-- 2. DIM_PRODUCT
-- 6 products, 4 categories
-- =========================================================

INSERT INTO dim_product (
    product_id,
    product_name,
    category
)
VALUES
    ('PROD001', 'Mechanical Keyboard', 'Electronics'),
    ('PROD002', 'Wireless Mouse',      'Electronics'),
    ('PROD003', 'Office Chair',        'Furniture'),
    ('PROD004', 'Standing Desk',       'Furniture'),
    ('PROD005', 'Coffee Maker',        'Home Appliances'),
    ('PROD006', 'Notebook Set',        'Stationery')
ON CONFLICT (product_id) DO UPDATE
SET
    product_name = EXCLUDED.product_name,
    category = EXCLUDED.category;


-- =========================================================
-- 3. DIM_SELLER
-- 4 sellers
-- =========================================================

INSERT INTO dim_seller (
    seller_id,
    seller_city,
    seller_state,
    seller_zip
)
VALUES
    ('SELL001', 'Hanoi',            'HN',  '100000'),
    ('SELL002', 'Da Nang',          'DN',  '550000'),
    ('SELL003', 'Ho Chi Minh City', 'HCM', '700000'),
    ('SELL004', 'Hai Phong',        'HP',  '180000')
ON CONFLICT (seller_id) DO UPDATE
SET
    seller_city = EXCLUDED.seller_city,
    seller_state = EXCLUDED.seller_state,
    seller_zip = EXCLUDED.seller_zip;


-- =========================================================
-- 4. FACT_SALES
-- Grain:
-- one row = one product line item within one order.
--
-- Total: 20 rows.
-- ORD019 has 3 line items.
-- ORD020 has 2 line items.
--
-- payment_value is stored at item grain and may differ from
-- quantity * unit_price because of discounts, vouchers,
-- shipping allocation, or other order adjustments.
-- =========================================================

INSERT INTO fact_sales (
    customer_key,
    product_key,
    date_key,
    seller_key,
    order_id,
    order_item_id,
    order_status,
    quantity,
    unit_price,
    payment_value
)
SELECT
    c.customer_key,
    p.product_key,
    d.date_key,
    s.seller_key,
    v.order_id,
    v.order_item_id,
    v.order_status,
    v.quantity,
    v.unit_price,
    v.payment_value
FROM (
    VALUES
        -- Q1 2025
        ('ORD001', 1, 'delivered', 1, 1200000.00::NUMERIC(12,2), 1200000.00::NUMERIC(12,2),
         'CUST001', 'PROD001', 'SELL001', DATE '2025-01-10'),

        ('ORD002', 1, 'delivered', 2,  350000.00::NUMERIC(12,2),  700000.00::NUMERIC(12,2),
         'CUST002', 'PROD002', 'SELL002', DATE '2025-02-14'),

        ('ORD003', 1, 'delivered', 1, 2500000.00::NUMERIC(12,2), 2500000.00::NUMERIC(12,2),
         'CUST003', 'PROD003', 'SELL003', DATE '2025-03-22'),

        -- Q2 2025
        ('ORD004', 1, 'delivered', 1, 4200000.00::NUMERIC(12,2), 4200000.00::NUMERIC(12,2),
         'CUST004', 'PROD004', 'SELL004', DATE '2025-04-05'),

        ('ORD005', 1, 'delivered', 1, 1800000.00::NUMERIC(12,2), 1800000.00::NUMERIC(12,2),
         'CUST005', 'PROD005', 'SELL001', DATE '2025-05-19'),

        ('ORD006', 1, 'delivered', 3,  120000.00::NUMERIC(12,2),  360000.00::NUMERIC(12,2),
         'CUST006', 'PROD006', 'SELL002', DATE '2025-06-27'),

        -- Q3 2025
        ('ORD007', 1, 'delivered', 1, 1200000.00::NUMERIC(12,2), 1200000.00::NUMERIC(12,2),
         'CUST002', 'PROD001', 'SELL003', DATE '2025-07-08'),

        ('ORD008', 1, 'delivered', 2,  350000.00::NUMERIC(12,2),  700000.00::NUMERIC(12,2),
         'CUST003', 'PROD002', 'SELL004', DATE '2025-08-16'),

        ('ORD009', 1, 'delivered', 1, 2500000.00::NUMERIC(12,2), 2500000.00::NUMERIC(12,2),
         'CUST005', 'PROD003', 'SELL001', DATE '2025-09-30'),

        -- Q4 2025
        ('ORD010', 1, 'delivered', 1, 4200000.00::NUMERIC(12,2), 4200000.00::NUMERIC(12,2),
         'CUST001', 'PROD004', 'SELL002', DATE '2025-10-12'),

        ('ORD011', 1, 'delivered', 1, 1800000.00::NUMERIC(12,2), 1800000.00::NUMERIC(12,2),
         'CUST004', 'PROD005', 'SELL003', DATE '2025-11-24'),

        ('ORD012', 1, 'canceled',  2,  120000.00::NUMERIC(12,2),  240000.00::NUMERIC(12,2),
         'CUST006', 'PROD006', 'SELL004', DATE '2025-12-18'),

        -- Q1 2026
        ('ORD013', 1, 'delivered', 2, 1200000.00::NUMERIC(12,2), 2400000.00::NUMERIC(12,2),
         'CUST003', 'PROD001', 'SELL001', DATE '2026-01-15'),

        ('ORD014', 1, 'shipped',   1,  350000.00::NUMERIC(12,2),  350000.00::NUMERIC(12,2),
         'CUST005', 'PROD002', 'SELL002', DATE '2026-02-09'),

        ('ORD015', 1, 'delivered', 1, 2500000.00::NUMERIC(12,2), 2500000.00::NUMERIC(12,2),
         'CUST001', 'PROD003', 'SELL003', DATE '2026-03-28'),

        -- Q3 2026
        -- ORD019: 1 order, 3 line items -> demonstrates item-level grain
        ('ORD019', 1, 'delivered', 1, 1200000.00::NUMERIC(12,2), 1200000.00::NUMERIC(12,2),
         'CUST001', 'PROD001', 'SELL001', DATE '2026-07-10'),

        ('ORD019', 2, 'delivered', 3,  120000.00::NUMERIC(12,2),  360000.00::NUMERIC(12,2),
         'CUST001', 'PROD006', 'SELL001', DATE '2026-07-10'),

        ('ORD019', 3, 'delivered', 1, 2500000.00::NUMERIC(12,2), 2500000.00::NUMERIC(12,2),
         'CUST001', 'PROD003', 'SELL001', DATE '2026-07-10'),

        -- ORD020: 1 order, 2 line items.
        -- Item 1: 2 * 350,000 = 700,000, but payment = 600,000
        -- because of a 100,000 discount/voucher.
        ('ORD020', 1, 'delivered', 2,  350000.00::NUMERIC(12,2),  600000.00::NUMERIC(12,2),
         'CUST005', 'PROD002', 'SELL002', DATE '2026-08-21'),

        -- Item 2 also demonstrates payment != quantity * unit_price.
        -- 1 * 1,800,000 = 1,800,000, payment = 1,850,000
        -- e.g. allocated shipping fee.
        ('ORD020', 2, 'delivered', 1, 1800000.00::NUMERIC(12,2), 1850000.00::NUMERIC(12,2),
         'CUST005', 'PROD005', 'SELL003', DATE '2026-08-21')
) AS v (
    order_id,
    order_item_id,
    order_status,
    quantity,
    unit_price,
    payment_value,
    customer_id,
    product_id,
    seller_id,
    full_date
)
JOIN dim_customer c
    ON c.customer_id = v.customer_id
JOIN dim_product p
    ON p.product_id = v.product_id
JOIN dim_seller s
    ON s.seller_id = v.seller_id
JOIN dim_date d
    ON d.full_date = v.full_date
ON CONFLICT (order_id, order_item_id) DO UPDATE
SET
    customer_key = EXCLUDED.customer_key,
    product_key = EXCLUDED.product_key,
    date_key = EXCLUDED.date_key,
    seller_key = EXCLUDED.seller_key,
    order_status = EXCLUDED.order_status,
    quantity = EXCLUDED.quantity,
    unit_price = EXCLUDED.unit_price,
    payment_value = EXCLUDED.payment_value;

COMMIT;