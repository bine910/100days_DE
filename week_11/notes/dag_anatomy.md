# DAG Anatomy — Week 11 / Day 2

> Viết DAG đầu tiên: `hello_classic` (classic operators) và `hello_taskflow` (TaskFlow API). Airflow 3.3.2.

---

## 1. Tham số của DAG

| Tham số | Ý nghĩa | Bẫy |
|---|---|---|
| `dag_id` | Định danh duy nhất trong cả hệ thống | Đổi `dag_id` = tạo DAG mới, **mất sạch lịch sử run** của DAG cũ. Hai file cùng `dag_id` = xung đột |
| `schedule` | Lịch chạy: cron string, `timedelta`, hoặc `None` | Airflow 3 dùng `schedule=`, **không phải** `schedule_interval=` (cú pháp 2.x) |
| `start_date` | Mốc bắt đầu tính interval | Phải là **hằng số cố định**. `datetime.now()` ở đây là lỗi kinh điển — mỗi lần parse ra một giá trị khác, scheduler loạn |
| `catchup` | Có chạy bù các interval quá khứ chưa chạy không | Airflow 3 mặc định `False` |
| `tags` | Nhãn để **nhóm nhiều DAG** trong UI | Không phải để mô tả một DAG. Đừng lặp lại `dag_id` làm tag |
| `default_args` | Dict áp cho **mọi task**: `retries`, `retry_delay`, `owner`, `execution_timeout` | — |

---

## 2. Hai cách viết DAG

### Classic — `with DAG(...)`

```python
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
import pendulum

with DAG(
    dag_id="hello_classic",
    schedule=None,
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    tags=["week11", "learning"],
) as dag:
    start = EmptyOperator(task_id="start")
    check_disk = BashOperator(task_id="check_disk", bash_command="df -h")
    print_date = BashOperator(task_id="print_date", bash_command="date")
    end = EmptyOperator(task_id="end")

    start >> [check_disk, print_date] >> end
```

Thứ tự khai báo **tường minh** bằng `>>`:
- `a >> b` — a xong rồi tới b
- `a >> [b, c] >> d` — fan-out rồi fan-in

> **Bẫy đã mắc:** `start >> check_disk , print_date >> end`
> Python đọc thành **tuple 2 phần tử** → hai nhánh rời nhau, `print_date` không chờ `start`.
> Dấu phẩy KHÔNG gộp task. **List** mới gộp.

### TaskFlow — `@dag` + `@task`

```python
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

hello_taskflow()                # ← gọi BÊN NGOÀI: tạo object DAG
```

**Hai lời gọi khác nhau, đừng nhầm:**
- `data = extract()` — trong hàm, để dựng đồ thị.
- `hello_taskflow()` — ngoài cùng, để sinh object DAG.

`@dag` chỉ tạo ra một **hàm factory**; phải gọi nó thì object DAG mới ra đời.
Quên dòng cuối = file không có DAG nào, `dags list` không thấy gì.
(Khác với `with DAG(...)`: object sinh ra ngay lúc vào khối `with`.)

---

## 3. Bốn điều rút ra

### 3.1 TaskFlow suy thứ tự từ **luồng dữ liệu**, không phải thứ tự dòng code

`extract()` khi gọi **không chạy hàm** — nó trả về một "phiếu hẹn" (XComArg) đại diện cho output tương lai của task. Truyền phiếu đó vào `transform` ⇒ Airflow ghi nhận cạnh `extract → transform`.

Hệ quả: **task nào không nhận output của task khác thì chạy song song.**

```python
data = extract()
a = analyze_a(data)
b = analyze_b(data)   # a và b độc lập → SONG SONG, không tuần tự
```

### 3.2 `dags test` ≠ chạy thật

```bash
docker compose run --rm airflow-cli dags test hello_classic 2026-10-01
```

Log cho thấy `check_disk` xong mới tới `print_date`, **dù đã khai báo `[check_disk, print_date]`**.
Lý do: `dags test` chạy toàn bộ DAG trong **một process duy nhất**, không qua scheduler/worker/Celery.

→ Dùng để debug nhanh. Muốn thấy song song thật thì trigger qua UI.

### 3.3 DAG success ≠ data correct ⚠️

Bài học lớn nhất Day 2. DAG xanh toàn tập, cả 4 task `success`, nhưng log in ra:

```
Count: {data['count']}, Total: {data['total']}, Max: {data['max']}
```

(quên chữ `f` ở f-string)

> **Airflow chỉ biết task có raise exception hay không. Nó KHÔNG biết dữ liệu đúng hay sai.**

Một pipeline xanh mướt vẫn có thể bơm rác vào warehouse 3 tháng mà không ai hay — đúng kiểu "sai dữ liệu trong im lặng" đã nêu ở Day 1 khi nói về cron.
→ Đây là lý do T14 có hẳn một tuần cho Data Quality.
→ **Đọc log, đừng chỉ nhìn màu.**

### 3.4 XCom = metadata, KHÔNG phải data

**XCom** = *cross-communication*: cơ chế task này đưa dữ liệu cho task kia. TaskFlow tự động push giá trị `return` và pull ở task sau (thấy dòng `Pushing xcom` trong log).

**Lưu ở đâu:** một dòng trong bảng `xcom` của **metadata DB (PostgreSQL)** — cùng chỗ với `dag_run`, `task_instance`. Kiểm chứng:

```bash
docker compose exec postgres psql -U airflow -d airflow -c "SELECT dag_id, task_id, key FROM xcom;"
```

**Vì sao không truyền DataFrame:**
1. Nó bị serialize và nhét vào một cell → metadata DB phình to theo thời gian.
2. Vi phạm nguyên tắc Day 1: *metadata DB là nội tạng của Airflow, không phải warehouse*.
3. Metadata DB phình ⇒ **scheduler chậm theo** (nó query bảng này liên tục) ⇒ ảnh hưởng cả những DAG không liên quan.

**Pattern đúng — truyền con trỏ, không truyền dữ liệu:**

```python
@task
def extract() -> str:
    df = call_api(...)
    path = "/opt/airflow/data/raw/orders_2026-10-01.parquet"
    df.to_parquet(path)
    return path                     # XCom chỉ chứa ~50 ký tự

@task
def transform(raw_path: str) -> str:
    df = pd.read_parquet(raw_path)
    ...
    return out_path
```

> **Quy tắc: XCom cho metadata (path, số dòng, ngày xử lý). Filesystem / object storage cho data.**
> Vài chục byte thì được. Vài MB trở lên thì không bao giờ.

Ghép với T10 (Parquet + layout `year/month/day`) và T8 (MinIO) — đây chính là chỗ chúng vào pipeline.

---

## 4. Import của Airflow 3

Chỗ hầu hết tutorial trên mạng còn sai vì viết cho 2.x:

```python
from airflow.sdk import dag, task, DAG        # KHÔNG phải airflow.decorators / airflow.models
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import PythonOperator
```

Quy tắc: **Airflow 3 đẩy operator ra provider package**, core chỉ còn `airflow.sdk`.

**Chỉ import thứ thực sự dùng.** File DAG được dag-processor parse lại vài chục giây một lần — import rác là chi phí thật, không phải chuyện thẩm mỹ.

Không cần cài gì trên máy: code DAG chạy **trong container** `apache/airflow:3.3.2`, đã có sẵn airflow + pendulum + pandas + provider chuẩn. Máy host chỉ đóng vai trò ổ đĩa qua mount `./dags:/opt/airflow/dags`.

---

## 5. Thói quen code cần giữ

- **Không dùng `lambda` trong `python_callable`** — không có tên nên log khó đọc, không test được, không pickle được ở vài executor. Dùng `def` đặt tên tử tế.
- **f-string phải có placeholder.** `f"count"` là thừa; `print("Count: {x}")` thiếu `f` thì in ra nguyên dấu ngoặc. (Thói quen mang từ JS sang.)
- **Task đặt tên theo động từ + đối tượng**: `extract_orders`, không phải `task_1`.

---

## 6. Lệnh dùng trong ngày

```bash
docker compose run --rm airflow-cli dags list
docker compose run --rm airflow-cli dags list | grep hello      # WSL
docker compose run --rm airflow-cli dags test hello_taskflow 2026-10-01
docker compose exec postgres psql -U airflow -d airflow -c "SELECT * FROM xcom;"
```

**Lưu ý:** `docker compose run` chỉ dựng các service nó phụ thuộc (postgres, redis), **không dựng api-server** → chạy xong mà mở `localhost:8080` sẽ `ERR_CONNECTION_REFUSED`. Phải `docker compose up -d`.

Khi `up`, các service đứng ở `Created` chờ `airflow-init` chạy xong — đúng mô hình `depends_on` + healthcheck đã học ở T7. Đợi 1–2 phút.

---




## 7. Tự kiểm tra

- [ ] Khác nhau giữa `data = extract()` và `hello_taskflow()`?
- [ ] Vì sao `a >> b, c >> d` không làm được việc bạn tưởng?
- [ ] `dags test` khác chạy qua scheduler ở điểm nào?
- [ ] XCom lưu vật lý ở đâu? Truyền DataFrame qua đó hỏng chuyện gì — nêu 3 hệ quả.
- [ ] Task `extract` nên return cái gì thay vì DataFrame?