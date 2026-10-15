from datetime import date
from pathlib import Path

import pandas as pd
import s3fs

from dotenv import load_dotenv
import os

import pyarrow as pa
import pyarrow.parquet as pq
import argparse

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "week_4/week4_olist/data/raw/olist_order_items_dataset.csv"


load_dotenv()
bucket = os.getenv("BUCKET")

def make_fs() -> s3fs.S3FileSystem:
    key=os.getenv("key")
    secret=os.getenv("secret")
    endpoint=os.getenv("ENDPOINT")
    if not all([key, secret, endpoint]):
        raise RuntimeError("Thiếu biến MinIO trong .env — xem .env.example")
    return s3fs.S3FileSystem(
        key=key, secret=secret,
        client_kwargs={"endpoint_url": endpoint},
    )

def ingest_to_bronze(
    csv_path: Path,
    table: str,
    fs: s3fs.S3FileSystem,
    bucket: str,
    ingestion_date: date | None = None,
) -> str:
    """Đọc CSV, ghi nguyên trạng vào bronze layer, partition theo ingestion_date."""
    ingestion_date = ingestion_date or date.today()

    df = pd.read_csv(csv_path)                    # KHÔNG clean, KHÔNG ép dtype
    df["ingestion_date"] = ingestion_date.isoformat()

    root = f"{bucket}/bronze/{table}"
    pq.write_to_dataset(
        pa.Table.from_pandas(df, preserve_index=False),
        root_path=root,
        filesystem=fs,
        partition_cols=["ingestion_date"],
        compression="zstd",
        existing_data_behavior="delete_matching",
    )
    return root
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=CSV)
    ap.add_argument("--table", default="order_items")
    ap.add_argument("--date", type=date.fromisoformat, default=None,
                    help="ingestion_date (YYYY-MM-DD), mặc định hôm nay")
    args = ap.parse_args()

    fs = make_fs()
    root = ingest_to_bronze(args.csv, args.table, fs, bucket, args.date)

    files = fs.find(root)
    df = pd.read_parquet(root, filesystem=fs)
    print(len(df))
    print(df["ingestion_date"].value_counts())
    print(f"wrote {len(files)} file(s) to s3://{root}")
    for f in files:
        print(" ", f)


if __name__ == "__main__":
    main()
