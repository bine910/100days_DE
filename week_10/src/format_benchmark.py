import time
import pandas as pd
from pathlib import Path
import argparse
from pyarrow import parquet as pq
    
ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "week_4/week4_olist/data/raw/olist_order_items_dataset.csv"
PARQUET = ROOT / "week_10/data/items.parquet"
DEFAULT_OUT = ROOT / "week_10/data/bench"
CODECS = [None, "snappy", "gzip", "zstd"]


def load_dataset(csv_path:str, rows=None) -> pd.DataFrame:
    """Load the dataset from a CSV file."""
    return pd.read_csv(csv_path, nrows=rows)

def write_variants(df, out_dir, codecs, runs=3) -> list[dict]:
    """Ghi df ra Parquet theo từng codec, đo write time và size."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for codec in codecs:
        name = codec or "none"
        path = out_dir / f"items_{name}.parquet"
        write_ms = bench(lambda: df.to_parquet(path, engine="pyarrow", compression=codec), runs=runs)
        rows.append({
            "codec": name,
            "path": path,
            "write_ms": write_ms,
            "size_mb": path.stat().st_size / 1024 / 1024,
        })
    return rows

def measure_columns (paths: dict[str, Path]) -> list[dict]:
    rows = []
    for r in paths:
        rg=pq.ParquetFile(r["path"]).metadata.row_group(0)
        for i in range(rg.num_columns):
            col = rg.column(i)
            rows.append({
                "codec":r["codec"],
                "column": col.path_in_schema,
                "compressed_kb": col.total_compressed_size / 1024,
                "uncompressed_kb": col.total_uncompressed_size / 1024,
                "physical_type": col.physical_type,
                "num_values": col.num_values,
            })
    return rows

def bench(fn, runs: int = 4) -> float:
    """Chạy fn nhiều lần, trả thời gian trung bình (ms). Bỏ lần đầu vì page cache."""
    times = []
    for _ in range(runs):
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
    if len(times) > 1:
        times = times[1:]
    return sum(times) / len(times) * 1000

def measure_codecs(rows: list[dict], runs: int = 4) -> list[dict]:
    """Đo read time cho từng codec."""
    for r in rows:
        r["read_ms"] = bench(lambda: pd.read_parquet(r["path"]), runs=runs)
    return rows

def fmt(v) -> str:
    return f"{v:.1f}" if isinstance(v, float) else str(v)


def print_table(rows: list[dict], title: str) -> None:
    if not rows:
        print(f"\n=== {title} === (no data)")
        return

    cols = [k for k in rows[0] if k != "path"]
    widths = {c: max(len(c), max(len(fmt(r[c])) for r in rows)) for c in cols}

    print(f"\n=== {title} ===")
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print("-" * (sum(widths.values()) + 2 * (len(cols) - 1)))
    for r in rows:
        print("  ".join(fmt(r[c]).rjust(widths[c]) for c in cols))

def measure_overview(csv_path: Path, parquet_path: Path, col: str, runs: int = 4) -> list[dict]:
    """CSV vs Parquet: size, read full, read 1 cột."""
    return [
        {
            "format": "CSV",
            "size_mb": csv_path.stat().st_size / 1024 / 1024,
            "read_full_ms": bench(lambda: pd.read_csv(csv_path), runs=runs),
            "read_1col_ms": bench(lambda: pd.read_csv(csv_path, usecols=[col]), runs=runs)
        },
        {
            "format": "Parquet",
            "size_mb": parquet_path.stat().st_size / 1024 / 1024,
            "read_full_ms": bench(lambda: pd.read_parquet(parquet_path), runs=runs),
            "read_1col_ms": bench(lambda: pd.read_parquet(parquet_path, columns=[col]), runs=runs)
        }
    ]
def measure_dtype(csv_path: Path, out_dir: Path, codec: str = "zstd") -> list[dict]:
    """So per-column size: v1 (dtype thô) vs v2 (ép dtype)."""
    out_dir.mkdir(parents=True, exist_ok=True)

    v1 = pd.read_csv(csv_path)
    v2 = pd.read_csv(
        csv_path,
        parse_dates=["shipping_limit_date"],
        dtype={"order_item_id": "int8", "seller_id": "category", "product_id": "category"},
    )

    sizes = {}
    for name, df in [("v1", v1), ("v2", v2)]:
        path = out_dir / f"items_{name}.parquet"
        df.to_parquet(path, engine="pyarrow", compression=codec)
        rg = pq.ParquetFile(path).metadata.row_group(0)
        sizes[name] = {
            rg.column(i).path_in_schema: rg.column(i).total_compressed_size / 1024
            for i in range(rg.num_columns)
        }

    out = []
    for col in sizes["v1"]:
        v1_kb = sizes["v1"][col]
        v2_kb = sizes["v2"][col]
        out.append({
            "column": col,
            "v1_kb": v1_kb,
            "v2_kb": v2_kb,
            "delta_pct": (v2_kb - v1_kb) / v1_kb * 100,
        })
        out.sort(key=lambda r: r["delta_pct"])
    return out 

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=CSV)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--runs", type=int, default=4)
    ap.add_argument("--col", default="price", help="cột dùng cho phép đo 1-column")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    print(f"dataset: {args.csv.name}  rows={len(df):,}  cols={len(df.columns)}")

    rows = measure_codecs(write_variants(df, args.out, CODECS, runs=args.runs), runs=args.runs)
    parquet_path = next(r["path"] for r in rows if r["codec"] == "snappy")
    print_table(measure_overview(args.csv,parquet_path, args.col, runs=args.runs), "[1] CSV vs Parquet")
    print_table(rows, "[2] Codec comparison")
    print_table(measure_columns(rows), "[3] Per-column size")
    print_table(measure_dtype(args.csv, args.out), "[4] Dtype impact")


if __name__ == "__main__":
    main()
