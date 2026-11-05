FROM apache/airflow:3.3.2

USER airflow
RUN pip install --no-cache-dir dbt-core==1.12.6 dbt-postgres==1.11.0
RUN pip install --no-cache-dir boto3
