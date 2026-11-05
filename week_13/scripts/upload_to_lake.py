"""Upload Parquet đã export lên MinIO, giữ nguyên layout."""
import argparse, os
from datetime import date
from pathlib import Path

import boto3

EXPORT_ROOT = Path(os.environ.get("EXPORT_ROOT", "/mnt/c/DE/week_13/export"))
BUCKET = os.environ.get("MINIO_BUCKET", "de-marts")


def main(run_date: date) -> None:
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    )
    root = EXPORT_ROOT / "marts"
    n = 0
    for p in iter_files(run_date):
        key = str(p.relative_to(EXPORT_ROOT))
        s3.upload_file(str(p), BUCKET, key)
        print(f"-> s3://{BUCKET}/{key}  ({p.stat().st_size/1e6:.1f} MB)")
        n += 1
    print(f"{n} object(s) uploaded for run_date={run_date}")

def iter_files(run_date: date):
    root = EXPORT_ROOT / "marts"
    # partition đúng ngày
    yield from root.glob(f"*/dt={run_date:%Y-%m-%d}/*.parquet")
    # dimension (không partition) — snapshot, luôn đẩy lại
    yield from root.glob("*/part-*.parquet")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-date", type=date.fromisoformat, default=date.today())
    main(ap.parse_args().run_date)