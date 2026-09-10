CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,

    full_date DATE NOT NULL UNIQUE,

    day_of_week SMALLINT NOT NULL,
    day_name VARCHAR(10) NOT NULL,
    day_of_month SMALLINT NOT NULL,

    month SMALLINT NOT NULL,
    month_name VARCHAR(20) NOT NULL,

    quarter SMALLINT NOT NULL,
    year SMALLINT NOT NULL,

    is_weekend BOOLEAN NOT NULL DEFAULT FALSE,
    is_holiday BOOLEAN NOT NULL DEFAULT FALSE,

    CHECK (day_of_week BETWEEN 1 AND 7),
    CHECK (day_of_month BETWEEN 1 AND 31),
    CHECK (month BETWEEN 1 AND 12),
    CHECK (quarter BETWEEN 1 AND 4)
);
CREATE TABLE dim_product (
    product_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Business Key
    product_id VARCHAR(64) NOT NULL UNIQUE,

    product_name VARCHAR(255),

    -- Flattened into dim_product
    -- instead of creating dim_category
    category VARCHAR(255)
);
CREATE TABLE dim_seller (
    seller_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    seller_id VARCHAR(64) NOT NULL UNIQUE,

    seller_city VARCHAR(100),
    seller_state VARCHAR(100),
    seller_zip VARCHAR(20)
);
CREATE TABLE dim_customer (
    customer_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    customer_id VARCHAR(64) NOT NULL UNIQUE,

    customer_name VARCHAR(255),
    customer_email VARCHAR(255),

    customer_city VARCHAR(100),
    customer_state VARCHAR(100),
    customer_zip VARCHAR(20)
);
CREATE TABLE fact_sales (
    sales_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Dimension Foreign Keys
    customer_key BIGINT NOT NULL,
    product_key BIGINT NOT NULL,
    date_key INTEGER NOT NULL,
    seller_key BIGINT NOT NULL,

    -- Degenerate Dimensions
    order_id VARCHAR(64) NOT NULL,
    order_item_id INTEGER NOT NULL,
    order_status VARCHAR(32) NOT NULL,

    -- Measures
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,

    -- Must already be allocated to item grain
    -- if original payment exists at order level
    payment_value NUMERIC(12, 2),

    CONSTRAINT fk_sales_customer
        FOREIGN KEY (customer_key)
        REFERENCES dim_customer(customer_key),

    CONSTRAINT fk_sales_product
        FOREIGN KEY (product_key)
        REFERENCES dim_product(product_key),

    CONSTRAINT fk_sales_date
        FOREIGN KEY (date_key)
        REFERENCES dim_date(date_key),

    CONSTRAINT fk_sales_seller
        FOREIGN KEY (seller_key)
        REFERENCES dim_seller(seller_key),

    CONSTRAINT chk_quantity_positive
        CHECK (quantity > 0),

    CONSTRAINT chk_unit_price_non_negative
        CHECK (unit_price >= 0),

    CONSTRAINT chk_payment_non_negative
        CHECK (
            payment_value IS NULL
            OR payment_value >= 0
        ),

    -- Enforce the declared grain:
    -- one order item should appear once
    CONSTRAINT uq_fact_sales_order_item
        UNIQUE (order_id, order_item_id)
);