import pandas as pd
import os
import pyarrow.parquet as pq


CSV = '../../week_4/week4_olist/data/raw/olist_order_items_dataset.csv'
PARQUET = '../data/items.parquet'

# df = pd.read_csv(CSV)
# print(df.dtypes)
# print(f"rows: {len(df)}")

# df.to_parquet(PARQUET, engine='pyarrow', compression='snappy')

# csv_size = os.path.getsize(CSV)
# pq_size = os.path.getsize(PARQUET)
# print(f"CSV:     {csv_size/1024/1024:.2f} MB")
# print(f"Parquet: {pq_size/1024/1024:.2f} MB")
# print(f"Ratio:   {csv_size/pq_size:.2f}x")

pf = pq.ParquetFile(PARQUET)
print(pf.metadata)
print(f"num_row_groups: {pf.metadata.num_row_groups}")

rg = pf.metadata.row_group(0)
for i in range(rg.num_columns):
    col = rg.column(i)
    print(f"col.path_in_schema: {col.path_in_schema}, col.physical_type: {col.physical_type}, col.encodings: {col.encodings}, col.total_compressed_size: {col.total_compressed_size}, col.total_uncompressed_size: {col.total_uncompressed_size}, col.statistics.min: {col.statistics.min}, col.statistics.max: {col.statistics.max}")