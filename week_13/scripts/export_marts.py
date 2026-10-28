"""Export analytics_marts → Parquet theo layout data lake."""
import os
from datetime import date
from pathlib import Path
import argparse

import pandas as pd
from sqlalchemy import create_engine

DWH_URL = "postgresql+psycopg2://dwh:dwh@localhost:5433/de_week9"
OUT_ROOT = Path("/mnt/c/DE/week_13/export")

# TODO 1: bảng nào partition theo ngày, bảng nào không?
#   dict: tên bảng -> True/False (có partition hay không)
TABLES = {
    "fct_orders": True,
    "dim_customers": False,
    "dim_products": False,
}


def object_path(table: str, partitioned: bool, run_date: date) -> Path:
    """Trả về đường dẫn file Parquet cho bảng này."""
    # TODO 2: fact -> marts/<table>/dt=YYYY-MM-DD/part-000.parquet
    #         dim  -> marts/<table>/part-000.parquet
    # Nhớ: tên object phải là hàm của DỮ LIỆU, không phải của lần chạy.
    ...
    today = run_date.strftime("%Y-%m-%d")
    if partitioned:
        path = OUT_ROOT / f"marts/{table}/dt={today}/part-000.parquet"
    else:
        path = OUT_ROOT / f"marts/{table}/part-000.parquet"

    return path


def main(run_date: date) -> None:
    engine = create_engine(DWH_URL)
    for table, partitioned in TABLES.items():
        df = pd.read_sql(f"SELECT * FROM analytics_marts.{table}", engine)
        path = object_path(table, partitioned, run_date)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)
        print(f"{table:15} {len(df):>7} rows -> {path}  ({path.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    # TODO 3: lấy ngày từ đâu? Gợi ý: Day 6 sẽ gọi script này từ Airflow,
    #         và backfill ngày 20/10 phải ghi vào dt=2026-10-20.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Ngày dữ liệu (YYYY-MM-DD). Airflow truyền logical date vào đây.",
    )
    args = parser.parse_args()
    main(run_date=args.run_date)