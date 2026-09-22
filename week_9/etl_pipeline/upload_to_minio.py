import boto3
from datetime import date
import logging
import dotenv
from dotenv import load_dotenv
import os


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

dotenv.load_dotenv()

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id=os.getenv("aws_access_key_id"),
    aws_secret_access_key=os.getenv("aws_secret_access_key")
)
try:
    s3.create_bucket(Bucket="gold-price")
    log.info("Created bucket gold-price")
except s3.exceptions.BucketAlreadyOwnedByYou:
    log.info("Bucket gold-price already exists")

bronze_key = f"bronze/{date.today().isoformat()}/XAU_1d_data.csv"
s3.upload_file(
    Filename="../data/raw/XAU_1d_data.csv",
    Bucket="gold-price",
    Key=bronze_key
)
log.info(f"Uploaded raw data to: {bronze_key}")