import pandas as pd

# Task 1 — Load datasets:

orders= pd.read_csv("data/raw/olist_orders_dataset.csv")
order_items = pd.read_csv("data/raw/olist_order_items_dataset.csv")
products = pd.read_csv("data/raw/olist_products_dataset.csv")
categories = pd.read_csv("data/raw/product_category_name_translation.csv")

print (f"\n====check====")
print (f" orders : {orders.shape}")
print (f" order_items : {order_items.shape}")
print (f" products : {products.shape}")
print (f" categories : {categories.shape}")

print("\n===== COLUMNS =====")
for name, df in [('orders', orders), ('order_items', order_items), ('products', products), ('categories', categories)]:
    print(f"\n{name}: {df.columns.tolist()}")

# Task 2 — Check grain


print("\n===== GRAIN CHECK =====")
for name, df, key in [
    ('orders', orders, 'order_id'),
    ('order_items', order_items, 'order_id'),
    ('products', products, 'product_id'),
    ('categories', categories, 'product_category_name')
]:
    unique = df[key].nunique()
    total = len(df)
    print(f"{name}: {unique} unique {key} / {total} rows = {unique/total:.4f}")
# Composite key check: order_id + order_item_id
composite = order_items.groupby(['order_id', 'order_item_id']).size()
print(f"Composite (order_id + order_item_id): {len(composite)} unique / {len(order_items)} rows")

# Task 3 — Merge orders + order_items
# SQL: SELECT * FROM orders o INNER JOIN order_items oi ON o.order_id = oi.order_id

orders_items = pd.merge(orders, order_items, on='order_id', how='inner')
print(f"\n===== MERGE: ORDERS + ORDER_ITEMS =====")
print(f"orders rows: {len(orders)}")
print(f"order_items rows: {len(order_items)}")
print(f"merged rows: {len(orders_items)}")

# Verify: 1 order with multiple items
sample_order = orders_items[orders_items['order_id'] == orders_items['order_id'].iloc[0]]
print(f"\nSample order items:")
print(sample_order[['order_id', 'order_item_id', 'product_id', 'price']])

# Task 4 — Merge + products
# SQL: ... JOIN products p ON oi.product_id = p.product_id
sales = pd.merge(orders_items, products, on='product_id', how='left')
print(f"\n===== MERGE: + PRODUCTS =====")
print(f"Before: {len(orders_items)} rows")
print(f"After: {len(sales)} rows")


# Task 5 — Merge + category translation
# SQL: ... JOIN category_translation ct ON p.product_category_name = ct.product_category_name

sales=pd.merge(sales,categories,on='product_category_name',how='left')
print(f"\n===== MERGE: + categories =====")
print(f" {len(sales)} rows")
print(f"Null category_english: {sales['product_category_name_english'].isnull().sum()}")
print(f"\nSample columns:")
print(sales[['order_id', 'price', 'product_category_name_english', 'order_purchase_timestamp']].head())

# Demo nhanh sự khác biệt
print(f"INNER: {len(pd.merge(orders, order_items, on='order_id', how='inner'))}")
print(f"LEFT:  {len(pd.merge(orders, order_items, on='order_id', how='left'))}")

# Task 6 — Revenue by category
# SQL: SELECT product_category_name_english, SUM(price) as total_revenue,
#        AVG(price) as avg_price, COUNT(*) as item_count
#      FROM sales GROUP BY product_category_name_english ORDER BY total_revenue DESC

category_summary = (
    sales
    .groupby('product_category_name_english')['price']
    .agg(['sum', 'mean', 'count'])
    .sort_values('sum', ascending=False)
)
print("\n===== TOP 10 CATEGORIES BY REVENUE =====")
print(category_summary.head(10))
# Task 7 — Revenue by month
# Convert timestamp first
sales['order_purchase_timestamp'] = pd.to_datetime(sales['order_purchase_timestamp'])
sales['year_month'] = sales['order_purchase_timestamp'].dt.to_period('M')

# SQL: SELECT DATE_TRUNC('month', order_purchase_timestamp), SUM(price)
#      FROM sales GROUP BY 1 ORDER BY 1
monthly_revenue = sales.groupby('year_month')['price'].sum()
print("\n===== MONTHLY REVENUE =====")
print(monthly_revenue)

# Task 8 — Revenue by month + category
# SQL: SELECT year_month, category, SUM(price)
#      FROM sales GROUP BY year_month, category

monthly_category=(
    sales.groupby(['year_month','product_category_name_english'])['price'].sum().sort_values(ascending=False)

)
print(monthly_category.head(10))