from datetime import timedelta
import pendulum
import pandas as pd
from airflow.sdk import dag, task,get_current_context, Variable
from etl.extract import extract
from etl.transform import transform
from etl.load import load
import logging 

log = logging.getLogger(__name__)

RAW_FILE = "/opt/airflow/data/raw/XAU_1d_data.csv"
STAGING = "/opt/airflow/data/staging"


@dag(
   dag_id="etl_daily",
        catchup=False,
        tags=["week11", "etl"],
        start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
        schedule="0 2 * * *",
        default_args={
            "retries": 3,
            "retry_delay": timedelta(seconds=30),
            "retry_exponential_backoff": True,
            "max_retry_delay": timedelta(minutes=5),
            "execution_timeout": timedelta(minutes=10),
        }
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
        if Variable.get("force_fail", default="false") == "true":raise ValueError("Cố tình fail để test retry")
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
    @task(trigger_rule="one_failed")
    def notify_failure():
        log.error("Pipeline etl_daily thất bại — kiểm tra log task đỏ")

    raw_path = extract_gold_price()
    clean_path = transform_gold_price(raw_path)
    rows = load_gold_price(clean_path)

    rows >> notify_failure()

etl_daily()