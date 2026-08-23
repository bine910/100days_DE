import pandas as pd

# Task 1 — Load raw dataset
# SQL equivalent: SELECT * FROM olist_orders
# 1 row = 1 order trên marketplace Olist
# Evidence: columns prefix "order_", có order_id unique, không có product_id/price
df = pd.read_csv('data/raw/olist_orders_dataset.csv')
print(f"Rows: {df.shape[0]}")
print(f"Columns: {df.shape[1]}")
print(f"\nColumn names: {df.columns.tolist()}")
print("\n--- HEAD ---")
print(df.head())
print("\n--- TAIL ---")
print(df.tail())

# Task 2 — Inspect schema
# SQL equivalent: \d orders (PostgreSQL)
# Classification:
#   order_id                        → identifier (PK, UUID/hash)
#   customer_id                     → identifier (FK → customers table)
#   order_status                    → categorical (low cardinality enum)
#   order_purchase_timestamp        → datetime (stored as str)
#   order_approved_at               → datetime (stored as str, has nulls)
#   order_delivered_carrier_date    → datetime (stored as str, has nulls)
#   order_delivered_customer_date   → datetime (stored as str, has nulls)
#   order_estimated_delivery_date   → datetime (stored as str)
#
# Key observations:
# - All columns loaded as str — Pandas does not auto-detect datetime
# - str is storage type, not semantic type. "2017-10-10 21:25:13" is datetime, not text
# - IDs are UUID/hash → keep as string, never convert to int
#   (IDs are not for arithmetic: no AVG(order_id) or order_id + 1)
print("\n--- DTYPES ---")
print(df.dtypes)
print("\n--- INFO ---")
df.info()

# Task 3 — Descriptive statistics
# SQL equivalent: SELECT COUNT(*), COUNT(DISTINCT order_status) FROM orders
# Observation: describe() returns almost nothing useful because orders table
# has NO numeric columns (no price, quantity, freight_value).
# Revenue calculation requires olist_order_items_dataset.csv
print("\n--- DESCRIBE ---")
print(df.describe())

# Task 4 — Column selection
# SQL: SELECT order_id, customer_id, order_status, order_purchase_timestamp FROM orders
print("\n--- SUBSET 1: ORDER OVERVIEW ---")
print(df[["order_id", "customer_id", "order_status", "order_purchase_timestamp"]].head())

# SQL: SELECT order_id, order_purchase_timestamp, order_estimated_delivery_date, order_delivered_customer_date FROM orders
# Useful for: delivery performance analysis
# Metrics: actual delivery time, early/late vs estimate
# Later: correlate with review scores (do late deliveries get lower ratings?)
print("\n--- SUBSET 2: DELIVERY TRACKING ---")
print(df[["order_id", "order_purchase_timestamp", "order_estimated_delivery_date", "order_delivered_customer_date"]].head())

# Task 5 — Filtering
# 5A — Filter by status
# SQL: SELECT * FROM orders WHERE order_status = 'delivered'
delivered = df[df["order_status"] == 'delivered']
print(f"\n--- FILTER A: DELIVERED ---")
print(f"Delivered orders: {len(delivered)}")

# SQL: SELECT order_status, COUNT(*) FROM orders GROUP BY order_status ORDER BY COUNT(*) DESC
print(f"\n--- STATUS DISTRIBUTION ---")
print(df["order_status"].value_counts())

# 5B — Filter by specific customer
# SQL: SELECT * FROM orders WHERE customer_id = '...'
sample_customer = df['customer_id'].iloc[0]
customer_orders = df[df['customer_id'] == sample_customer]
print(f"\n--- FILTER B: CUSTOMER {sample_customer} ---")
print(f"Number of orders: {len(customer_orders)}")

# 5C — Filter by timestamp
# SQL: SELECT * FROM orders WHERE order_purchase_timestamp > '2018-01-01'
# Note: comparison works on str because ISO format sorts lexicographically
orders_2018 = df[df['order_purchase_timestamp'] > '2018-01-01']
print(f"\n--- FILTER C: ORDERS AFTER 2018-01-01 ---")
print(f"Count: {len(orders_2018)}")

# Task 6 — Sorting
# SQL: SELECT * FROM orders ORDER BY order_purchase_timestamp ASC LIMIT 3
print("\n--- SORT: OLDEST FIRST ---")
print(df.sort_values('order_purchase_timestamp').head(3))

# SQL: SELECT * FROM orders ORDER BY order_purchase_timestamp DESC LIMIT 3
print("\n--- SORT: NEWEST FIRST ---")
print(df.sort_values('order_purchase_timestamp', ascending=False).head(3))

# Task 7 — Dataset profiling summary
print("\n===== OLIST ORDERS DATA PROFILE =====")
print(f"Rows: {df.shape[0]}")
print(f"Columns: {df.shape[1]}")
print(f"\nColumn names: {df.columns.tolist()}")
print(f"\nData types:\n{df.dtypes}")
print(f"\nNull counts:\n{df.isnull().sum()}")
print(f"\nOrder status values:\n{df['order_status'].value_counts()}")

sorted_df = df.sort_values('order_purchase_timestamp')
print(f"\nTime range: {sorted_df['order_purchase_timestamp'].iloc[0]} -> {sorted_df['order_purchase_timestamp'].iloc[-1]}")

print("\nPotential issues:")
print("- All datetime columns stored as str, need to_datetime() conversion")
print("- Nulls in: order_approved_at, order_delivered_carrier_date, order_delivered_customer_date")
print("- No price/revenue data — must JOIN with order_items table")

# Task 8 — Cardinality
# SQL: SELECT COUNT(DISTINCT col) FROM orders
print("\n===== CARDINALITY =====")
for col in ['order_id', 'customer_id', 'order_status']:
    unique = df[col].nunique()
    total = len(df)
    print(f"{col}: {unique} unique / {total} total = {unique/total:.4f}")
# order_id ≈ 1.0   → PK, grain = 1 row per order
# customer_id ≈ 1.0 → most customers have only 1 order (or customer_id is per-order)
# order_status ≈ 0.0 → low cardinality, categorical enum

# Task 9 — SQL ↔ Pandas mapping
# df.head()                              → SELECT * FROM orders LIMIT 5
# df[['col1','col2']]                    → SELECT col1, col2 FROM orders
# df[df['status']=='delivered']          → WHERE order_status = 'delivered'
# df.sort_values('col')                  → ORDER BY col ASC
# df.sort_values('col', ascending=False) → ORDER BY col DESC
# df['col'].nunique()                    → SELECT COUNT(DISTINCT col)
# df['col'].value_counts()              → SELECT col, COUNT(*) GROUP BY col
# len(df)                                → SELECT COUNT(*) FROM orders

# Task 10 — DE investigation answers
# Q1: Grain = 1 row = 1 order
# Q2: Primary key = order_id (unique per row)
# Q3: Foreign key = customer_id → olist_customers_dataset.csv
# Q4: 5 timestamp columns need to_datetime() conversion
# Q5: Cannot calculate revenue — no price/quantity columns
# Q6: Need olist_order_items_dataset.csv for revenue
# Q7: Need olist_order_items_dataset.csv for product details
# Q8: 100K orders → 115K after JOIN items = NORMAL (1 order can have multiple items, 1:N relationship)
