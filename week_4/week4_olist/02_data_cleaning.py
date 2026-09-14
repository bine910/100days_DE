import pandas as pd


# Cleaning Pipeline — thứ tự quan trọng

# Luôn clean theo thứ tự:

# Inspect — hiểu data trước (Day 1 đã làm)
# Convert types — datetime, numeric đúng type
# Handle nulls — drop/fill/giữ tùy context
# Remove duplicates — sau khi type đúng
# Validate — kiểm tra kết quả sau clean

df = pd.read_csv('data/raw/olist_orders_dataset.csv')


# Task 1 — Quantify missing values
# SQL: SELECT COUNT(*) - COUNT(col) AS null_count FROM orders

print("===== MISSING VALUES =====")
print(df.isnull().sum())
print( f"\n tỉ lệ NUll: {((df.isnull().sum()/len(df))*100).round(2)}")

# Task 2 — Convert datetime columns
# SQL: CAST(col AS TIMESTAMP)

datetime_cols = [
    'order_purchase_timestamp',
    'order_approved_at', 
    'order_delivered_carrier_date',
    'order_delivered_customer_date',
    'order_estimated_delivery_date'
]

for col in datetime_cols:
    df[col]=pd.to_datetime(df[col])

print("\n===== AFTER DATETIME CONVERSION =====")
print(df.dtypes)
print(df[datetime_cols].head())

# Task 3 — Investigate nulls vs order_status
# SQL: SELECT order_status, COUNT(*) - COUNT(order_delivered_customer_date) AS null_delivery
#      FROM orders GROUP BY order_status

print("\n===== NULL DELIVERY DATE BY STATUS =====")
null_delivery= df[df['order_delivered_customer_date'].isnull()]
print(null_delivery['order_status'].value_counts())

print("\n===== NON-NULL DELIVERY DATE BY STATUS =====")
has_delivery=df[df['order_delivered_customer_date'].notna()]
print(has_delivery['order_status'].value_counts())

# Task 4 — Check duplicates
# Exact duplicate rows
print("\n===== DUPLICATES =====")
print(f"Exact duplicate rows: {df.duplicated().sum()}")

# Duplicate order_id (PK should be unique)
# SQL: SELECT order_id, COUNT(*) FROM orders GROUP BY order_id HAVING COUNT(*) > 1
print(f"Duplicate order_id:  {df['order_id'].duplicated().sum()}")

# Task 5 — Suspicious values
# Check time range after datetime conversion

print("\n===== TIME RANGE =====")
print(f"Earliest: {df['order_purchase_timestamp'].min()}")
print(f"Latest: {df['order_purchase_timestamp'].max()}")

# Check: any delivery before purchase? (should be impossible)
# SQL: SELECT * FROM orders WHERE order_delivered_customer_date < order_purchase_timestamp
delivered_before_purchase = df[df['order_delivered_customer_date'] < df['order_purchase_timestamp']]
print(f"\nDelivered BEFORE purchase: {len(delivered_before_purchase)}")

df['delivery_days'] = (df['order_delivered_customer_date'] - df['order_purchase_timestamp']).dt.days
print(f"\nDelivery days stats:")
print(df['delivery_days'].describe())
# Task 6 — Clean function
def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Clean olist orders dataset.
    
    Steps:
    1. Convert datetime columns
    2. Keep nulls as-is (they have business meaning)
    3. No duplicates found, but check defensively
    """
    df = df.copy()
    
    # Convert datetime
    datetime_cols = [
        'order_purchase_timestamp',
        'order_approved_at',
        'order_delivered_carrier_date',
        'order_delivered_customer_date',
        'order_estimated_delivery_date'
    ]
    for col in datetime_cols:
        df[col] = pd.to_datetime(df[col])
    
    # Remove exact duplicates (defensive)
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    print(f"Duplicates removed: {before - after}")
    
    return df

# Test the function
df_clean = clean_orders(df)
print(f"\n===== AFTER CLEANING =====")
print(f"Rows: {len(df_clean)}")
print(df_clean.dtypes)