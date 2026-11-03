"""Export analytics_marts → Parquet theo layout data lake.

Fact: partition theo NGÀY DỮ LIỆU (purchased_at), mỗi partition chỉ chứa
dòng thuộc ngày đó. Dimension: ghi đè toàn bộ, không partition.
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

DWH_URL = "postgresql+psycopg2://dwh:dwh@localhost:5433/de_week9"
OUT_ROOT = Path("/mnt/c/DE/week_13/export")

# tên bảng -> cột ngày dùng để partition (None = snapshot, ghi đè)
TABLES = {
    "fct_orders": "purchased_at",
    "dim_customers": None,
    "dim_products": None,
}


def object_path(table: str, date_col: str | None, run_date: date) -> Path:
    """Đường dẫn object. Tên là hàm của DỮ LIỆU, không phải của lần chạy."""
    if date_col:
        return OUT_ROOT / f"marts/{table}/dt={run_date:%Y-%m-%d}/part-000.parquet"
    return OUT_ROOT / f"marts/{table}/part-000.parquet"


def build_query(table: str, date_col: str | None) -> str:
    """Fact lọc theo [run_date, run_date+1). Cột để trần -> dùng được index."""
    if date_col:
        return (
            f"SELECT * FROM analytics_marts.{table} "
            f"WHERE {date_col} >= :d_from AND {date_col} < :d_to"
        )
    return f"SELECT * FROM analytics_marts.{table}"


def main(run_date: date) -> None:
    engine = create_engine(DWH_URL)
    params = {"d_from": run_date, "d_to": run_date + timedelta(days=1)}

    for table, date_col in TABLES.items():
        sql = build_query(table, date_col)
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params if date_col else None,
                 dtype_backend="pyarrow")

        if date_col and df.empty:
            print(f"{table:15} {0:>7} rows -> bỏ qua (không có dữ liệu ngày {run_date})")
            continue

        path = object_path(table, date_col, run_date)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)
        size_mb = path.stat().st_size / 1e6
        print(f"{table:15} {len(df):>7} rows -> {path}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Ngày dữ liệu (YYYY-MM-DD). Airflow truyền logical date vào đây.",
    )
    args = parser.parse_args()
    main(run_date=args.run_date)