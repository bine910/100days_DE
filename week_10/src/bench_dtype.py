import time
import pandas as pd
from pathlib import Path
import pyarrow.parquet as pq
from bench_codec import DATA

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "week_4/week4_olist/data/raw/olist_order_items_dataset.csv"
PARQUET = ROOT / "week_10/data/items.parquet"


df1 = pd.read_csv(CSV)
df1.to_parquet(DATA / "items_v1.parquet", compression="zstd")

# v2 — ép dtype
df2 = pd.read_csv(
    CSV,
    parse_dates=["shipping_limit_date"],
    dtype={"order_item_id": "int8", "seller_id": "category", "product_id": "category"},
)
df2.to_parquet(DATA / "items_v2.parquet", compression="zstd")

rg1= pq.ParquetFile(DATA / "items_v1.parquet").metadata.row_group(0)
rg2= pq.ParquetFile(DATA / "items_v2.parquet").metadata.row_group(0)
for i in range(rg1.num_columns):
    col = rg1.column(i)
    print(f"col.path_in_schema v1: {col.path_in_schema}, col.physical_type: {col.physical_type}, col.encodings: {col.encodings}, col.total_compressed_size: {col.total_compressed_size}, col.total_uncompressed_size: {col.total_uncompressed_size}, col.statistics.min: {col.statistics.min}, col.statistics.max: {col.statistics.max}")

for i in range(rg2.num_columns):
    col = rg2.column(i)
    print(f"col.path_in_schema v2: {col.path_in_schema}, col.physical_type: {col.physical_type}, col.encodings: {col.encodings}, col.total_compressed_size: {col.total_compressed_size}, col.total_uncompressed_size: {col.total_uncompressed_size}, col.statistics.min: {col.statistics.min}, col.statistics.max: {col.statistics.max}")