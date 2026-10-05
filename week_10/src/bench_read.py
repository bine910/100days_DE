import time
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "week_4/week4_olist/data/raw/olist_order_items_dataset.csv"
PARQUET = ROOT / "week_10/data/items.parquet"

def bench(label, fn, runs=4):
    times = []
    for _ in range(runs):
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
    if len(times) > 1:
        times = times[1:]                      # bỏ lần đầu: page cache
    avg_ms = sum(times) / len(times) * 1000
    print(f"{label:<32} {avg_ms:>8.1f} ms")
    return avg_ms

bench("CSV  full",        lambda: pd.read_csv(CSV))
bench("Parquet full",     lambda: pd.read_parquet(PARQUET))
bench("Parquet 1 col",    lambda: pd.read_parquet(PARQUET, columns=["price"]))
bench("CSV  1 col",       lambda: pd.read_csv(CSV, usecols=["price"]))