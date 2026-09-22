import boto3
import json
from datetime import date

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin123"
)

today = date.today().isoformat()
bronze_path = f"bronze/{today}/data.json"

s3.upload_file(
    Filename="sample_orders.json",
    Bucket="datalake",
    Key=bronze_path
)

print(f"Uploaded raw data to: {bronze_path}")