import pandas as pd
import boto3
from io import BytesIO
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

def extract_from_minio(bucket: str, key: str) -> pd.DataFrame:
    s3 = boto3.client(
        "s3",
        endpoint_url="http://localhost:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin"
    )
    response = s3.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(BytesIO(response["Body"].read()), sep=";")
    log.info(f"Extracted {len(df)} rows from MinIO: {bucket}/{key}")
    return df

def extract(file_path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(file_path, sep=";")
    except Exception as e:
        log.error(f"Error occurred while extracting data from {file_path}: {e}")
        raise e
    log.info(f"Extracted {len(df)} rows from local file: {file_path}")
    return df