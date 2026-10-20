import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
import os

user = os.environ["DWH_USER"]
password = os.environ["DWH_PASSWORD"]

    
ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = Path("/mnt/c/DE/week_4/week4_olist/data/raw")

files = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
}
def main():
    engine = create_engine(f"postgresql+psycopg2://{user}:{password}@localhost:5433/de_week9")

    for table, filename in files.items():
        df = pd.read_csv(RAW_DIR / filename)
        df.to_sql(table, engine, schema="raw", if_exists="replace", index=False)
        print(f"raw.{table}: {len(df)} rows")

if __name__ == "__main__":
    main()