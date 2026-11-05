from datetime import datetime, timedelta
from airflow.sdk import dag
from airflow.providers.standard.operators.bash import BashOperator

DBT_DIR = "/opt/airflow/dbt"
PROFILES_DIR = "/opt/airflow/.dbt"
SCRIPTS = "/opt/airflow/week_13/scripts"

@dag(
    dag_id="dbt_daily",
    schedule="0 3 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["week12", "week13", "dbt", "lake"],
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
)
def dbt_daily():
    build = BashOperator(
        task_id="dbt_build",
        bash_command=f"cd {DBT_DIR} && dbt build --target airflow --profiles-dir {PROFILES_DIR}",
    )

    export = BashOperator(
        task_id="export_marts",
        bash_command=f"python {SCRIPTS}/export_marts.py --run-date {{{{ ds }}}}",
    )

    upload = BashOperator(
        task_id="upload_to_lake",
        bash_command=f"python {SCRIPTS}/upload_to_lake.py --run-date {{{{ ds }}}}",
    )

    build >> export >> upload

dbt_daily()