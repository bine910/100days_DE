# Scheduling & Incremental Load — Week 11 / Day 4

> Ngày khó nhất tuần: `logical_date`, `data_interval`, và lọc dữ liệu theo run.
> Kết quả: mỗi run chỉ nạp đúng phần dữ liệu thuộc về nó (1 dòng/ngày), thay vì cả 5531 dòng như Day 3.

---

## 1. logical_date vs thời điểm chạy

Tình huống: DAG `schedule="0 2 * * *"`, chạy lúc **02:00 ngày 15/10**.

**Nó xử lý dữ liệu của ngày 14/10, không phải 15/10.**

Lý do hiển nhiên khi nghĩ kỹ: lúc 2h sáng 15/10, ngày 15/10 mới trôi qua 2 tiếng — chưa có gì để xử lý. Thứ vừa kết thúc trọn vẹn là ngày 14/10.

```
data_interval_start = 14/10 02:00
data_interval_end   = 15/10 02:00
run thực thi lúc    = 15/10 02:00   ← ngay khi khoảng đóng lại
logical_date        = 14/10 02:00   ← = data_interval_start
```

> **Airflow đợi khoảng dữ liệu ĐÓNG LẠI rồi mới chạy run cho khoảng đó.**
> Luôn trễ một chu kỳ. Đây là thứ khiến người mới hoang mang khi thấy run "hôm nay" mang nhãn ngày hôm qua.

### Ba khái niệm

| Tên | Là gì |
|---|---|
| `logical_date` | **Nhãn** của run, bằng `data_interval_start`. Airflow 2 gọi là `execution_date` — cái tên tệ nhất lịch sử Airflow, vì nó *không phải* lúc thực thi |
| `data_interval_start` / `_end` | Cặp mốc xác định **khoảng dữ liệu run này chịu trách nhiệm**. Đây là thứ dùng trong code |
| thời điểm thực thi | Khi worker thực sự chạy. **Không bao giờ dùng trong logic nghiệp vụ** |

Cả ba đều **cố định theo run**. Chạy lại run 15/10 vào năm sau vẫn ra cùng giá trị → idempotent.

### Bài tập kiểm tra

DAG `@hourly`, run thực thi lúc 15/10 14:00:
→ `data_interval_start = 13:00`, `data_interval_end = 14:00`

---

## 2. Vì sao `now()` bị cấm trong pipeline ⚠️

```python
today = pendulum.now().date()        # ← SAI
df = df[df["Date"] == today]
```

Backfill run 15/10 vào ngày 18/10: `now()` trả 18/10 → pipeline lọc dữ liệu ngày 18/10, trong khi lẽ ra phải xử lý dữ liệu của run 15/10.
**Backfill chạy xanh nhưng nạp sai dữ liệu hoàn toàn.**

> **`now()` làm kết quả của một run phụ thuộc vào thời điểm bạn bấm chạy.**
> Chạy lại cùng một run ở hai thời điểm khác nhau ra hai kết quả khác nhau
> ⇒ pipeline **không idempotent** ⇒ backfill trở nên vô nghĩa.

Cùng họ với quy tắc `start_date` phải là hằng số (Day 2): mọi thứ định nghĩa một run phải **tiền định**, không phụ thuộc lúc chạy.

---

## 3. Lấy context trong TaskFlow

**Cách 1 — khai báo tham số (rõ ràng hơn, nên dùng):**
```python
@task
def extract_gold_price(data_interval_start=None, data_interval_end=None) -> str:
    log.info("Xử lý khoảng: %s → %s", data_interval_start, data_interval_end)
```
Lợi: nhìn chữ ký biết task cần gì, test được bằng cách truyền tay.

**Cách 2 — lấy cả context:**
```python
from airflow.sdk import get_current_context

@task
def my_task():
    ctx = get_current_context()
    logical_date = ctx["logical_date"]        # key đúng là "logical_date"
```

> Key sai (`"data_logical_date"`) → `KeyError`.

**Kiểu dữ liệu:** `pendulum.DateTime`, **tz-aware (UTC)**. So sánh thẳng với cột pandas tz-naive → `TypeError: Cannot compare tz-naive and tz-aware`.

---

## 4. Cái bẫy lệch một ngày ⚠️

Với `start = 14/10 02:00`, `end = 15/10 02:00`, dữ liệu daily ở mốc `00:00`:

| Dòng dữ liệu | `start <= Date < end`? |
|---|---|
| `14/10 00:00` | **KHÔNG** — nhỏ hơn start (02:00) |
| `15/10 00:00` | **CÓ** — nằm trong khoảng |

→ Run mang nhãn 14/10 lại nạp dữ liệu ngày 15/10. **Lệch đúng một ngày.**
Pipeline xanh, không lỗi, dữ liệu sai — loại bug mà `data_interval` sinh ra khi dùng ẩu.

### Nửa mở là quy ước chuẩn

`start <= x < end`, **không phải** `<=` ở cả hai đầu.
Dùng `<=` hai đầu: dòng đúng mốc `end` bị lấy bởi **cả run này lẫn run kế tiếp** → trùng lặp.

### Ba phương án xử lý

| | Cách | Khi nào dùng |
|---|---|---|
| **A** | Lọc theo `logical_date.date()` | Grain = ngày. **Đã chọn** |
| **B** | Chuẩn hoá interval về ranh giới ngày, lọc nửa mở | Tổng quát hơn, cần khi grain là giờ |
| **C** | Đổi `schedule` thành `"0 0 * * *"` để interval trùng ranh giới ngày | Né vấn đề, nhưng ràng buộc giờ chạy |

**Chọn A, lý do:**
- Ý định *"run này phụ trách đúng một ngày"* nằm **tường minh** trong code, không phụ thuộc giờ đặt trong cron
- Khớp **grain** của bảng `gold_price_daily` (một dòng một ngày)
- Nhược: chỉ đúng khi grain là ngày. Chuyển sang dữ liệu giờ thì phải viết lại theo B

**Tiện lợi bất ngờ của A:** `.dt.date` trả `datetime.date` thuần (không timezone), `logical_date.date()` cũng vậy → **so sánh không gây lỗi tz**. Tự giải quyết luôn vấn đề mục 3.

---

## 5. Code hoàn chỉnh

### `etl/transform.py`

```python
import pandas as pd
import logging

log = logging.getLogger(__name__)


def transform(df: pd.DataFrame, logical_date=None) -> pd.DataFrame:
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()

    if logical_date is not None:
        df = df[df["Date"].dt.date == logical_date.date()]

    log.info("Số dòng sau transform: %d", len(df))
    return df
```

Ba điểm: `pd.to_datetime` **bắt buộc** (đọc từ parquet vẫn có thể ra string), chỉ **một** dòng lọc, và nó nằm **trong** khối `if`.

### `dags/etl_daily.py` — phần thay đổi

```python
@dag(
    dag_id="etl_daily",
    schedule="0 2 * * *",                                  # Day 4 mới đặt lịch
    catchup=False,                                         # Day 6 mới bật
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),    # phải nằm TRƯỚC vùng dữ liệu
    tags=["week11", "etl"],
    default_args={"retries": 2, "retry_delay": timedelta(minutes=1)},
)
def etl_daily():

    @task
    def extract_gold_price() -> str:
        ctx = get_current_context()
        start_date = ctx["data_interval_start"]
        df = extract(RAW_FILE)
        out = f"{STAGING}/raw_{start_date.date()}.parquet"    # tên file CÓ NGÀY
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
```

**Tên file phải có ngày** — note Day 3 mục 13: tên cố định thì các run ghi đè nhau, Day 6 backfill song song sẽ hỏng.

> `schedule` khai báo hai lần trong cùng `@dag(...)` → `SyntaxError: keyword argument repeated`.

---

## 6. Bẫy vận hành: run "success" với 0 task ⚠️⚠️

Tốn nhiều thời gian nhất hôm nay.

**Triệu chứng:** `dags test` báo `success`, nhưng không task nào chạy.

```
Created dag run ...
Marking run ... successful        ← nhảy thẳng, cách nhau 50ms
run_duration=23596264.900031      ← ~273 ngày, bất thường
```

**Nguyên nhân: `logical_date` nằm TRƯỚC `start_date` của DAG.**

```bash
dags test etl_daily 2026-01-15     # logical_date = 2026-01-15
start_date = pendulum.datetime(2026, 10, 1)   # ← SAU đó
```

Airflow tạo được dag run, nhưng không task instance nào hợp lệ — task kế thừa `start_date` của DAG, và task không thể chạy cho thời điểm trước khi nó tồn tại. Run bị đánh `success` ngay với 0 task. **Không một lỗi nào được báo.**

**Dấu hiệu nhận biết:**
- log nhảy từ `Created dag run` thẳng sang `Marking run successful`
- `run_duration` lớn bất thường (= khoảng cách giữa `logical_date` và lúc chạy thật)
- `data_interval_start == data_interval_end`
- không có dòng `starting task_id=...` nào

**Cách chẩn đoán nhanh:**
```bash
docker compose run --rm airflow-cli dags test <dag_id> <date> 2>&1 \
  | grep -E "starting task_id|Task failed"
```
Rỗng = không task nào chạy.

→ **`start_date` phải nằm trước vùng dữ liệu bạn định xử lý.** Đặt nó ở thời điểm dữ liệu bắt đầu tồn tại.

### Những cách KHÔNG phải nguyên nhân (đã thử, mất ~30 phút)

- `docker compose restart airflow-dag-processor airflow-scheduler`
- `dags delete etl_daily -y`
- `docker compose down --volumes` + init lại

Cảnh báo `Multiple rows returned with uselist=False for 'DagRun.serialized_dag'` có xuất hiện (nhiều bản serialize chồng nhau sau mỗi lần sửa file) — nhưng **không phải** nguyên nhân chính.

---

## 7. Ba bẫy công cụ khác

### `tasks test` không kéo XCom

```bash
docker compose run --rm airflow-cli tasks test etl_daily transform_gold_price 2026-01-15
# → TypeError: Expected a path-like ... instead of the given type: NoneType
```

`tasks test` chạy **một task biệt lập**, không có DAG run thật phía sau → không pull XCom từ task trước → `raw_path = None`.

→ Chỉ dùng được cho task **đứng đầu chuỗi** (không nhận đầu vào). Đây là giới hạn thật, không phải bug.

### `down --volumes` xoá cả warehouse ⚠️

```bash
docker compose down --volumes       # xoá MỌI volume, gồm postgres-dwh-volume
```
→ Mất sạch 5531 dòng dữ liệu đã load hôm qua, mất cả bảng.

Dấu hiệu nhận ra sau khi `up`: `Volume airflow_postgres-dwh-volume **Created**` (không phải "Running").

→ Dùng `docker compose down` không cờ, hoặc chỉ định volume cụ thể cần xoá.
→ Reset metadata Airflow mà vẫn giữ data: chỉ xoá volume của `postgres` (metadata), không đụng `postgres-dwh-volume`.

### `.dt` accessor cần cột đã là datetime

```
AttributeError: Can only use .dt accessor with datetimelike values
```
Đọc từ parquet/CSV ra có thể vẫn là string → luôn `pd.to_datetime()` trước khi dùng `.dt`.

### `retries` khi debug

`retries: 2` + fail = chờ 2 phút mỗi lần thử. Khi đang sửa code, tạm để `retries: 0`, nhớ trả về sau.

---

## 8. Dữ liệu rỗng ≠ lỗi

Run ngày `2026-01-15` cho `Số dòng sau transform: 0`.

Kiểm chứng:
```bash
docker compose exec airflow-scheduler grep "2026.01.1" /opt/airflow/data/raw/XAU_1d_data.csv
# 2026.01.12 ...
# 2026.01.13 ...      ← không có 01.15
```

File chỉ có dữ liệu đến 13/01. **0 dòng là đúng**, không phải bug.

`load.py` đã chuẩn bị sẵn:
```python
if df.empty:
    log.warning("DataFrame rỗng — không có gì để load")
    return 0
```
→ Task xanh, load 0 dòng, không crash. **Không có dữ liệu ≠ lỗi.**

> Lưu ý: file `XAU_1d_data.csv` là **lịch sử tĩnh**, không tự sinh dòng mới mỗi ngày. Incremental ở đây là *lọc từ file*, không phải *đọc file mới*.

---

## 9. Kết quả Day 4

```bash
docker compose run --rm airflow-cli dags test etl_daily 2026-01-12 2>&1 | grep -E "Số dòng|Loaded"
# Số dòng sau transform: 1
# Loaded 1 rows into gold_price_daily
```

```
    date    |   open    |   high    |    low    |   close   | volume
------------+-----------+-----------+-----------+-----------+---------
 2026-01-12 | 4511.1400 | 4630.2300 | 4511.1400 | 4598.5300 | 1360186
```

Khớp chính xác dòng `2026.01.12 00:00;4511.14;4630.23;4511.14;4598.53;1360186` trong file nguồn.

**Khác biệt cốt lõi so với Day 3:** hôm qua mỗi run nạp cả 5531 dòng; hôm nay mỗi run chỉ nạp phần dữ liệu **thuộc về nó**. Đó là incremental load.

### Ghi chú về NUMERIC

Giá vàng 2026 đã lên ~4500 với **2 chữ số thập phân** (`4511.14`). `NUMERIC(5,1)` ban đầu sẽ làm tròn thành `4511.1` — mất dữ liệu âm thầm. `NUMERIC(12,4)` giữ nguyên.
→ Lại một lần nữa: **đối chiếu kiểu cột với dữ liệu thật**, và chọn dư.

---

## 10. Điểm cần cải thiện (chưa làm)

`extract_gold_price` đang đọc **toàn bộ** CSV rồi ghi parquet — mỗi run một bản copy giống hệt, 5531 dòng. Lọc chỉ xảy ra ở `transform`.

Với file 297KB thì không sao. Với `XAU_1m_data.csv` (348MB) thì mỗi run ghi 348MB rác xuống đĩa.

→ Trong hệ thống thật, lọc nên đẩy **càng gần nguồn càng tốt** — gọi là **predicate pushdown**, và Parquet hỗ trợ rất tốt (T10).

---

## 11. Tự kiểm tra

- [ ] DAG `0 2 * * *` chạy lúc 02:00 ngày 20/3 xử lý dữ liệu ngày nào?
- [ ] `logical_date` bằng `data_interval_start` hay `_end`?
- [ ] Vì sao `pendulum.now()` phá vỡ backfill?
- [ ] `start <= x <= end` gây vấn đề gì so với `start <= x < end`?
- [ ] Run báo success nhưng 0 task — nguyên nhân phổ biến nhất là gì? Dấu hiệu nhận biết?
- [ ] `tasks test` dùng được cho task nào, không dùng được cho task nào?
- [ ] Lọc 0 dòng — khi nào là bug, khi nào là đúng?