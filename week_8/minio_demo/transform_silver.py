import boto3
import json
from datetime import date
import pandas as pd

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin123",
    )

#Read raw data from bronze layer
today = date.today().isoformat()
bronze_key= f"bronze/{today}/data.json"

response = s3.get_object(Bucket="datalake", Key=bronze_key)
raw_data = json.loads(response['Body'].read().decode('utf-8'))
print(f"Read raw data from: {bronze_key}")

rows = []
for order in raw_data["orders"]:
    for item in order["items"]:
        rows.append({
            "order_id": order["id"],
            "customer_name": order["customer"]["name"],
            "customer_email": order["customer"]["email"],
            "customer_address": order["customer"]["address"],
            "product": item["product"],
            "qty": item["qty"],
            "price": item["price"],
            "order_total": order["total"],
            "status": order["status"],
            "created_at": order["created_at"],
        })

df = pd.DataFrame(rows)
print(f"Flattened to {len(df)} rows")
print(df.dtypes)
print()

df["created_at"] = pd.to_datetime(df["created_at"])
df["order_total"] = df["order_total"].astype(int)
df["price"] = df["price"].astype(int)
print ("cast type")

null_count = df["customer_address"].isna().sum()
df["customer_address"] = df["customer_address"].fillna("unknown")
print(f"Filled {null_count} null values in customer_address with 'unknown'")

before = len(df)
df = df.drop_duplicates()
after = len(df)
print(f"Deduped: {before} → {after} rows (removed {before - after})")

parquet_file = "orders_cleaned.parquet"
df.to_parquet(parquet_file, index=False)

silver_key = f"silver/{today}/orders_cleaned.parquet"
s3.upload_file(
    Filename=parquet_file,
    Bucket="datalake",
    Key=silver_key,
    )
print(f"\nUploaded cleaned data to: {silver_key}")
print(f"Final data:")
print(df.to_string(index=False))