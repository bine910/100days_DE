"""Export toàn bộ fct_orders, dịch purchased_at về 30 ngày gần đây.
Chỉ để học partition pruning — dữ liệu đã bị bóp méo, không dùng phân tích.
"""
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

DWH_URL = "postgresql+psycopg2://dwh:dwh@localhost:5433/de_week9"
OUT = Path("/mnt/c/DE/week_13/export/shifted")

SQL = """
SELECT
    order_id, customer_id, status,
    (CURRENT_DATE - INTERVAL '55 days')
      + (purchased_at - (SELECT min(purchased_at) FROM analytics_marts.fct_orders))
        * (55.0 / EXTRACT(EPOCH FROM (
             (SELECT max(purchased_at) FROM analytics_marts.fct_orders)
           - (SELECT min(purchased_at) FROM analytics_marts.fct_orders)
          )) * 86400)
      AS purchased_at,
    delivered_customer_at, estimated_delivery_at,
    item_count, total_revenue, total_payment_value, payment_count
FROM analytics_marts.fct_orders
"""

engine = create_engine(DWH_URL)
with engine.connect() as conn:
    df = pd.read_sql(text(SQL), conn, dtype_backend="pyarrow")

OUT.mkdir(parents=True, exist_ok=True)
p = OUT / "fct_orders_shifted.parquet"
df.to_parquet(p, engine="pyarrow", compression="snappy", index=False)
print(f"{len(df)} rows -> {p} ({p.stat().st_size/1e6:.1f} MB)")
print("range:", df.purchased_at.min(), "->", df.purchased_at.max())
