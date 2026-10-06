from importlib.resources import path
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
import shutil

from format_benchmark import bench, print_table

SIZES = [5_000, 20_000, 112_650]
ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "week_4/week4_olist/data/raw/olist_order_items_dataset.csv"
OUT = ROOT / "week_10/data/bench_rowgroup"
def measure_row_groups(df: pd.DataFrame, out_dir: Path, sizes: list[int]) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for n in sizes:
        path = out_dir / f"items_rg{n}.parquet"
        df.to_parquet(path, engine="pyarrow", compression="zstd", row_group_size=n)
        md = pq.ParquetFile(path).metadata
        rows.append({
            "row_group_size": n,
            "num_row_groups": md.num_row_groups,
            "size_mb": path.stat().st_size / 1024 / 1024,
            "filter_ms": bench(lambda: pq.read_table(path, filters=[("price", ">", 1000)])),
            "full_ms": bench(lambda: pq.read_table(path)),
        })
    return rows

def check_row_group_sizes( out_dir: Path, sizes: list[int]) -> None:
    """Check that the row group sizes are as expected."""
    for n in sizes:
        pf = pq.ParquetFile(out_dir / f"items_rg{n}.parquet")
        print(f"Row group size for {n} rows: {pf.metadata.row_group(0).num_rows} rows")
        for i in range(pf.num_row_groups):
            rg = pf.metadata.row_group(i).column(5).statistics
            print(f"Row group {i} has {rg.min} to {rg.max} values.")

def measure_partition(df: pd.DataFrame, out_dir: Path) -> list[dict]:
    """So partitioned vs flat khi query 1 tháng cụ thể."""
    df = df.copy()
    df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"])
    df["year"] = df["shipping_limit_date"].dt.year
    df["month"] = df["shipping_limit_date"].dt.month

    flat = out_dir / "items_flat.parquet"
    part = out_dir / "bronze_partitioned"
    shutil.rmtree(part, ignore_errors=True)
    df.to_parquet(flat, engine="pyarrow", compression="zstd")
    df.to_parquet(part, engine="pyarrow", compression="zstd",
                  partition_cols=["year", "month"])

    filt = [("year", "==", 2017), ("month", "==", 9)]

    return [
        {
            "layout": "flat",
            "files": 1,
            "size_mb": flat.stat().st_size / 1024 / 1024,
            "query_1month_ms": bench(lambda: pq.read_table(flat, filters=filt)),
        },
        {
            "layout": "partitioned",
            "files":  len(list(part.rglob("*.parquet"))),     
            "size_mb": sum(f.stat().st_size for f in part.rglob("*.parquet")) / 1024 / 1024,    
            "query_1month_ms": bench(lambda: pq.read_table(part, filters=filt))  
        },
    ]

def main() -> None:
    df = pd.read_csv(CSV)
    print_table(measure_row_groups(df.sort_values("price"), OUT, SIZES), "[1] Row group (sorted by price)")
    # check_row_group_sizes(OUT, SIZES)
    print_table(measure_partition(df, OUT), "[2] Partition pruning")

if __name__ == "__main__":
    main()