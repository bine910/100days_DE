-- ============================================
-- Week 5 — E-commerce Schema (3NF)
-- Drop order: con trước, cha sau
-- ============================================

DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS sellers CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- ============================================
-- 1. categories (không FK)
-- ============================================
CREATE TABLE categories (
    category_id INT PRIMARY KEY,
    category_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2. customers (không FK)
-- ============================================
CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 3. sellers (không FK)
-- ============================================
CREATE TABLE sellers (
    seller_id INT PRIMARY KEY,
    seller_name TEXT NOT NULL,
    seller_city TEXT,
    seller_state TEXT,
    seller_zip_code TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 4. products (FK → categories)
-- ============================================
CREATE TABLE products (
    product_id INT PRIMARY KEY,
    category_id INT NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    product_name TEXT NOT NULL,
    weight NUMERIC(8,2),
    length NUMERIC(8,2),
    height NUMERIC(8,2),
    width NUMERIC(8,2),
    CHECK (weight > 0),
    CHECK (length > 0),
    CHECK (height > 0),
    CHECK (width > 0)
);

-- ============================================
-- 5. orders (FK → customers)
-- ============================================
CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    order_date TIMESTAMPTZ NOT NULL,
    order_status TEXT NOT NULL DEFAULT 'pending',
    CHECK (order_status IN ('pending', 'shipped', 'delivered', 'cancelled'))
);

-- ============================================
-- 6. order_items (FK → orders, products, sellers)
--    Composite PK: (order_id, product_id)
-- ============================================
CREATE TABLE order_items (
    order_id INT REFERENCES orders(order_id) ON DELETE RESTRICT,
    product_id INT REFERENCES products(product_id) ON DELETE RESTRICT,
    seller_id INT NOT NULL REFERENCES sellers(seller_id) ON DELETE RESTRICT,
    quantity INT NOT NULL,
    unit_price NUMERIC(12,2) NOT NULL,
    PRIMARY KEY (order_id, product_id),
    CHECK (quantity >= 1),
    CHECK (unit_price > 0)
);

-- ============================================
-- 7. payments (FK → orders)
-- ============================================
CREATE TABLE payments (
    payment_id INT PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(order_id) ON DELETE RESTRICT,
    payment_type TEXT NOT NULL,
    payment_installments INT NOT NULL DEFAULT 1,
    payment_value NUMERIC(12,2) NOT NULL,
    CHECK (payment_type IN ('credit_card', 'debit_card', 'boleto', 'voucher', 'pix')),
    CHECK (payment_installments >= 1),
    CHECK (payment_value > 0)
);

-- ============================================
-- 8. reviews (FK → orders)
--    UNIQUE(order_id) → mỗi order tối đa 1 review
-- ============================================
CREATE TABLE reviews (
    review_id INT PRIMARY KEY,
    order_id INT NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE RESTRICT,
    review_score INT NOT NULL,
    review_comment TEXT,
    review_created_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (review_score BETWEEN 1 AND 5)
);