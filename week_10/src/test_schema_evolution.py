from datetime import date
import pandas as pd
from bronze_ingest import make_fs, ingest_to_bronze, CSV, bucket
import pyarrow.dataset as ds
import pyarrow as pa

fs = make_fs()
root = f"{bucket}/bronze/order_items"

# Ghi một partition có thêm cột
df = pd.read_csv(CSV)
df["discount"] = 0.15
tmp = CSV.parent / "_tmp_with_discount.csv"
df.to_csv(tmp, index=False)
ingest_to_bronze(tmp, "order_items", fs, bucket, date(2026, 11, 15))


# Đọc toàn bộ dataset
fragments = ds.dataset(root, filesystem=fs, format="parquet", partitioning="hive").get_fragments()
unified = pa.unify_schemas([f.physical_schema for f in fragments])
dataset = ds.dataset(root, filesystem=fs, format="parquet",
                     partitioning="hive", schema=unified)
out = dataset.to_table().to_pandas()
print(out.shape)
print(out["discount"].isna().mean())