from airflow.sdk import dag, task
import pendulum

@dag(
    dag_id="hello_taskflow",
    schedule=None,
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    tags=["week11", "learning"],
)
def hello_taskflow():

    @task
    def extract() -> list[int]:
        return [12, 45, 7, 103, 88]

    @task
    def transform(data: list[int]) -> dict[str, int]:
        return {"count": len(data), "total": sum(data), "max": max(data)}

    @task
    def load(data: dict[str, int]) -> None:
        print(f"Count: {data['count']}, Total: {data['total']}, Max: {data['max']}")

    data = extract()            # ← gọi BÊN TRONG: nối task, dựng đồ thị
    stats = transform(data)
    load(stats)

hello_taskflow()  