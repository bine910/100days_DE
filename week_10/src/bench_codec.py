import time, os
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from bench_read import bench, CSV

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "week_10/data"

df = pd.read_csv(CSV)
CODECS = [None, "snappy", "gzip", "zstd"]

results = []
for codec in CODECS:
    name = codec or "none"
    path = DATA / f"items_{name}.parquet"

    t = time.perf_counter()
    df.to_parquet(path, engine="pyarrow", compression=codec)
    write_ms = (time.perf_counter() - t) * 1000

    read_ms = bench(f"Parquet read  {name:<6}", lambda: pq.read_table(path), runs=4)

    size_mb = os.path.getsize(path) / 1024 / 1024
    rg = pq.ParquetFile(path).metadata.row_group(0)
    print(f"\n--- {codec} ---")
    for i in range(rg.num_columns):
        col = rg.column(i)
        print(f"{col.path_in_schema:<22} {col.total_compressed_size/1024:>8.1f} KB")
    results.append((name, write_ms, size_mb))

print("\nCodec      Write (ms)  Size (MB)")
for name, write_ms, size_mb in results:
    print(f"{name:<10} {write_ms:>10.1f} {size_mb:>10.1f}")