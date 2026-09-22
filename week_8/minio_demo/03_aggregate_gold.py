import boto3
import pandas as pd
from datetime import date

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin123",
)

# ========== 1. Đọc Silver parquet ==========
today = date.today().isoformat()
silver_key = f"silver/{today}/orders_cleaned.parquet"

s3.download_file("datalake", silver_key, "temp_silver.parquet")
df = pd.read_parquet("temp_silver.parquet")
print(f"Read {len(df)} rows from Silver")
print(df)
print()

# ========== 2. Gold: Doanh thu theo sản phẩm ==========
revenue_by_product = (
    df.groupby("product")
    .agg(
        total_revenue=("price", lambda x: (x * df.loc[x.index, "qty"]).sum()),
        total_qty=("qty", "sum"),
        total_orders=("order_id", "nunique"),
    )
    .reset_index()
    .sort_values("total_revenue", ascending=False)
)

print("Gold: Revenue by Product")
print(revenue_by_product.to_string(index=False))
print()

# ========== 3. Upload Gold ==========
gold_file = "revenue_by_product.parquet"
revenue_by_product.to_parquet(gold_file, index=False)

gold_key = f"gold/{today}/revenue_by_product.parquet"
s3.upload_file(
    Filename=gold_file,
    Bucket="datalake",
    Key=gold_key,
)

print(f"🚀 Uploaded to: {gold_key}")
