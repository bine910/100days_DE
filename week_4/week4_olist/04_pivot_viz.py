import pandas as pd
import matplotlib.pyplot as plt

# Load and merge (reuse Day 3 logic)
orders = pd.read_csv('data/raw/olist_orders_dataset.csv')
order_items = pd.read_csv('data/raw/olist_order_items_dataset.csv')
products = pd.read_csv('data/raw/olist_products_dataset.csv')
categories = pd.read_csv('data/raw/product_category_name_translation.csv')

sales = (
    orders
    .merge(order_items, on='order_id')
    .merge(products, on='product_id')
    .merge(categories, on='product_category_name', how='left')
)
sales['order_purchase_timestamp'] = pd.to_datetime(sales['order_purchase_timestamp'])
sales['year_month'] = sales['order_purchase_timestamp'].dt.to_period('M')

print(f"Sales dataset: {sales.shape}")
# print(sales.columns.to_list())

# Task 1 — Revenue by category
category_revenue= (
    sales.groupby('product_category_name_english')['price']
    .sum()
    .sort_values(ascending=False)
)
print(category_revenue)
# Task 2 — Bar chart top 10
# Task 2 — Bar chart top 10
import os
os.makedirs('output', exist_ok=True)
top10 = category_revenue.head(10)
top10.plot(kind='bar', title='Top 10 Categories by Revenue')
plt.ylabel('Revenue (BRL)')
plt.tight_layout()
plt.savefig('output/revenue_by_category.png')
plt.close()
print("Saved: output/revenue_by_category.png")

# Task 3 — Monthly revenue
monthly_revenue= sales.groupby('year_month')['price'].sum().head(10)

# Task 4 — Line chart
monthly_revenue.plot(kind='line',title="Doanh thu thang")
plt.ylabel('Revenue (BRL)')
plt.xlabel('Month')
plt.savefig('output/monthly_revenue_trend.png')
plt.close()
print("Saved: output/monthly_revenue_trend.png")

# Task 5 — Pivot: month x category (top 5 categories only)
top5_categories = category_revenue.head(5).index.tolist()
sales_top5 = sales[sales['product_category_name_english'].isin(top5_categories)]
pivot = sales_top5.pivot_table(
    values='price',
    index='year_month',
    columns='product_category_name_english',
    aggfunc='sum',
    fill_value=0
)
print("\n===== PIVOT: MONTH x TOP 5 CATEGORY =====")
print(pivot)

# Task 8 — Export reports
category_summary = (
    sales
    .groupby('product_category_name_english')['price']
    .agg(['sum', 'mean', 'count'])
    .sort_values('sum', ascending=False)
)
category_summary.to_csv('output/category_summary.csv')
pivot.to_csv('output/monthly_category_report.csv')

print("Saved: output/category_summary.csv")
print("Saved: output/monthly_category_report.csv")