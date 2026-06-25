"""
dags/product_pipeline_dag.py

Hourly orchestration: extract (SerpAPI -> bronze) then load
(bronze -> silver -> gold).
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from etl.extract import run_extract
from etl.load import run_load

default_args = {
    "owner": "junwei",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="product_pipeline_dag",
    description="Track Amazon product price/ranking trends via SerpAPI",
    schedule_interval="@hourly",
    start_date=datetime(2026, 6, 22),
    catchup=False,
    default_args=default_args,
    tags=["product-intelligence", "serpapi"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_from_serpapi",
        python_callable=run_extract,
    )

    load_task = PythonOperator(
        task_id="load_bronze_to_gold",
        python_callable=run_load,
    )

    extract_task >> load_task
