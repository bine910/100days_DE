from datetime import timedelta
import pendulum
import pandas as pd
from airflow.sdk import dag, task,get_current_context
from etl.extract import extract
from etl.transform import transform
from etl.load import load

RAW_FILE = "/opt/airflow/data/raw/XAU_1d_data.csv"
STAGING = "/opt/airflow/data/staging"


@dag(
   dag_id="etl_daily",
        catchup=False,
        tags=["week11", "etl"],
        start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
        default_args={"retries": 2, "retry_delay": timedelta(minutes=1)},
        schedule="0 2 * * *"
)
def etl_daily():

    @task
    def extract_gold_price() -> str:
        ctx = get_current_context()
        start_date = ctx["data_interval_start"]
        df = extract(RAW_FILE)
        out = f"{STAGING}/raw_{start_date.date()}.parquet"
        df.to_parquet(out)
        return out

    @task
    def transform_gold_price(raw_path: str) -> str:
        ctx = get_current_context()
        logical_date = ctx["logical_date"]
        df = pd.read_parquet(raw_path)
        df = transform(df, logical_date)
        out = f"{STAGING}/clean_{logical_date.date()}.parquet"
        df.to_parquet(out)
        return out

    @task
    def load_gold_price(clean_path: str) -> int:
        df = pd.read_parquet(clean_path)
        loaded_rows = load(df)
        return loaded_rows

    raw_path = extract_gold_price()
    clean_path = transform_gold_price(raw_path)
    load_gold_price(clean_path)

etl_daily()