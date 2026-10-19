# Retry, Timeout & Alerting — Week 11 / Day 5

> Làm pipeline **hỏng một cách có kiểm soát**. Phần tách người biết dùng Airflow khỏi người chỉ biết viết DAG.

---

## 1. Các tham số độ tin cậy

```python
default_args={
    "retries": 3,
    "retry_delay": timedelta(seconds=30),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=10),
}
```

| Tham số | Ý nghĩa |
|---|---|
| `retries` | Số lần thử **lại** (ngoài lần đầu). `retries=3` → tối đa 4 lần chạy |
| `retry_delay` | Chờ bao lâu giữa các lần |
| `retry_exponential_backoff` | `True` → delay tăng dần thay vì đều |
| `max_retry_delay` | Chặn trên cho backoff |
| `execution_timeout` | Quá thời gian này → kill task, đánh fail |

`default_args` áp cho **mọi task** trong DAG. Khai báo hai lần trong cùng `@dag(...)` → `SyntaxError: keyword argument repeated`.

---

## 2. Retry cứu được lỗi nào?

| Loại lỗi | Ví dụ | Retry có giúp? |
|---|---|---|
| **Transient** (tạm thời) | 503 Service Unavailable, timeout mạng, DB restart, disk busy | **CÓ** — nguyên nhân ngoài code, có thể tự hết |
| **Logic** | `KeyError: 'price'` do API đổi schema, lỗi cú pháp SQL, chia cho 0 | **KHÔNG** — chạy 100 lần vẫn sai |

> Với lỗi logic, retry còn **làm chậm phát hiện vấn đề**: thay vì đỏ ngay, task đỏ sau 4 phút.

### Exponential backoff

Log thật từ run hôm nay:

```
10:25:02  attempt 1  ──┐
                       │  31s
10:25:33  attempt 2  ──┤
                       │  71s
10:26:44  attempt 3  ──┤
                       │  195s
10:29:59  attempt 4  ──┘
```

Với `retry_exponential_backoff=False` thì cả 3 khoảng đều đúng 30s.

**Vì sao cần backoff:** nếu API đang quá tải, retry dồn dập mỗi 30 giây chỉ làm nó tệ thêm. Giãn dần cho hệ thống kia thời gian hồi phục.

---

## 3. Retry chỉ an toàn khi task idempotent ⚠️

**Nguyên tắc quan trọng nhất của Day 5.**

> Bật `retries` mà task không idempotent là **tự làm hỏng dữ liệu** — và Airflow vẫn báo xanh.

### Hai lớp bảo vệ của `load_gold_price`

```python
with hook.get_conn() as conn:
    with conn.cursor() as cursor:
        cursor.executemany(INSERT_SQL, rows)   # ①
    conn.commit()                              # ②
```

| Fail ở đâu | Cơ chế bảo vệ | Kết quả |
|---|---|---|
| Trước `commit()` | **Transaction rollback** | Không ghi gì, retry chạy sạch |
| Sau `commit()` | **`ON CONFLICT (date) DO UPDATE`** | Ghi đè, không nhân bản |

**Lớp 1 — transaction.** Postgres mặc định chạy trong transaction: mọi `INSERT` trước `commit()` chỉ tồn tại trong vùng nháp, chưa ai nhìn thấy, chưa ghi cố định. Nếu ① raise ở dòng thứ 3000, ② không bao giờ chạy tới → connection đóng khi có exception → **rollback** → 3000 dòng đó biến mất hoàn toàn, bảng về đúng trạng thái trước khi task chạy.

Đây là **atomicity** — chữ A trong ACID. Hoặc tất cả, hoặc không gì cả.

**Lớp 2 — UPSERT.** Giả sử đã commit xong 5000 dòng rồi mới chết (mất mạng lúc đóng connection). Retry chạy lại toàn bộ: với mỗi dòng Postgres kiểm tra `date` đã tồn tại chưa (nhờ `PRIMARY KEY` = unique index) → chưa có thì INSERT, đã có thì **UPDATE đè lên**, không tạo dòng thứ hai.

→ Chạy 1 lần hay 10 lần, bảng vẫn đúng 5000 dòng.

### Vì sao lỗi raise ở dòng 3000 chứ không phải dòng 1?

Lỗi **cú pháp SQL** lộ ngay dòng đầu. Lỗi **dữ liệu** chỉ lộ khi gặp đúng dòng gây lỗi:
- dòng 3000 có `volume = 5_000_000_000` → vượt `INTEGER` (max ~2.1 tỷ)
- dòng 3000 có `close = NULL` trong khi cột `NOT NULL`
- giá 5 chữ số vào `NUMERIC(5,1)` → tràn

Hoặc không phải lỗi dữ liệu: mạng đứt, Postgres restart, disk đầy — ở bất kỳ thời điểm nào.

### Giải thích từng dòng

| Dòng | Việc nó làm |
|---|---|
| `hook.get_conn()` | Mở kết nối Postgres bằng thông tin trong Connection `postgres_dwh` |
| `with ... as conn` | Context manager — ra khỏi khối `with` thì Python tự dọn dẹp, dù thoát bình thường hay vì exception. Giống `try/finally` nhưng gọn |
| `conn.cursor()` | Cursor = "con trỏ làm việc" trên connection: nơi gửi SQL và đọc kết quả |
| `cursor.executemany(SQL, rows)` | Chạy câu SQL một lần cho **mỗi** tuple trong `rows`, gửi theo lô |
| `conn.commit()` | **Chốt transaction** — chỗ quan trọng nhất |

---

## 4. execution_timeout — vì sao cần

Task treo **chiếm một slot worker vĩnh viễn**, không trả lại. Worker của bạn có `concurrency: 16` (thấy trong log Day 1).

Hôm nay một task treo → còn 15 slot. Mai thêm một → 14. Sau 16 ngày → hết sạch slot, task mới xếp hàng `queued` mãi. Nhìn bên ngoài giống Airflow chết, thực ra chỉ là slot bị giữ.

### "Sao không đẩy việc qua 15 luồng còn trống?"

Airflow **có làm vậy** — 15 slot trống thì task mới vào bình thường. Vấn đề không phải nghẽn, mà là slot **không bao giờ được trả lại**.

Và quan trọng hơn: **không thể chuyển một task đang chạy dở sang worker khác.** Task đang giữ state — file đang ghi, transaction đang mở, HTTP request đang chờ. Chuyển đi nghĩa là chạy lại từ đầu, tức là retry. Mà retry chỉ xảy ra sau khi task **kết thúc** (fail hoặc timeout).

> **Task treo thì chưa kết thúc — Airflow không biết nó hỏng, vì nó trông y hệt một task chạy lâu.**
> `execution_timeout` chính là cách nói: *"quá X phút thì coi như hỏng"*.

---

## 5. Trigger rules

Mặc định là `all_success`: task chỉ chạy khi **mọi** task cha đều xanh. Đó là lý do khi `transform` đỏ thì `load_gold_price` không bao giờ chạy.

| Rule | Chạy khi |
|---|---|
| `all_success` (mặc định) | Mọi task cha thành công |
| `all_failed` | **Mọi** task cha đều fail |
| `one_failed` | **Có ít nhất một** task cha fail |
| `one_success` | Có ít nhất một task cha thành công |
| `all_done` | Mọi task cha đã kết thúc, bất kể kết quả |
| `none_failed` | Không có task cha nào fail (cho phép skipped) |

### Task cảnh báo

```python
    @task(trigger_rule="one_failed")
    def notify_failure():
        log.error("Pipeline etl_daily thất bại — kiểm tra log task đỏ")
```

**Vì sao `one_failed` chứ không phải `all_failed`:** trong tình huống thật (`extract` xanh, `transform` đỏ, `load` skipped), `all_failed` yêu cầu *mọi* task cha fail — `extract` xanh nên điều kiện không thoả, cảnh báo không chạy.

### skipped ≠ success ≠ failed

Khi pipeline chạy thành công, `notify_failure` ở trạng thái **`skipped`**, không phải `success`.

- `success` = task **đã chạy** và xong tốt
- `skipped` = task **không hề chạy** vì trigger rule không thoả

Trong UI `skipped` hiện màu hồng nhạt. DAG run thành công sẽ có 3 ô xanh + 1 ô hồng — **bình thường, không phải lỗi**.

Hệ quả: task `skipped` **không** làm DAG run thành `failed`. Ngược lại, nếu `notify_failure` chạy xong êm thì DAG run **vẫn** `failed` — vì `transform` đỏ.

### Nối task không có dữ liệu đi kèm

```python
    raw_path = extract_gold_price()
    clean_path = transform_gold_price(raw_path)
    rows = load_gold_price(clean_path)

    rows >> notify_failure()
```

`notify_failure` không nhận output của ai → không nối được kiểu TaskFlow.

> Đây là **trường hợp hợp lệ duy nhất** để trộn `>>` vào TaskFlow: khi phụ thuộc là **thứ tự thuần tuý**, không có dữ liệu đi kèm.

---

## 6. Airflow Variable — bật/tắt không cần sửa code

```python
from airflow.sdk import dag, task, get_current_context, Variable

@task
def transform_gold_price(raw_path: str) -> str:
    if Variable.get("force_fail", default_var="false") == "true":
        raise ValueError("Cố tình fail để test retry")
    ...
```

Variable = cặp key-value lưu trong metadata DB, chỉnh từ UI (**Admin → Variables**) hoặc CLI:

```bash
docker compose run --rm airflow-cli variables set force_fail true
docker compose run --rm airflow-cli variables set force_fail false
```

Bật/tắt mà **không đụng code**, không phải chờ dag-processor parse lại.

Dùng thật về sau: API key, tên bucket, cờ bật/tắt tính năng, danh sách cấu hình.

> Luôn truyền `default_var` — nếu Variable chưa tồn tại mà không có default thì task fail với `KeyError`.

**Nhớ trả `force_fail` về `false`** trước khi đóng máy, không thì hôm sau mở lên thấy `transform` đỏ và mất vài phút tự hỏi vì sao.

---

## 7. Bẫy: IDE tự thêm import sai ⚠️

```
ImportError: libtk8.6.so: cannot open shared object file
  File "/opt/airflow/dags/etl_daily.py", line 2
    from tkinter import Variable
```

IDE thấy gõ `Variable`, tìm trong thư viện có sẵn, chọn nhầm **`tkinter`** (thư viện giao diện đồ hoạ, không liên quan gì).

Đúng là:
```python
from airflow.sdk import dag, task, get_current_context, Variable
```

**Lần thứ hai IDE autocomplete gây lỗi trong tuần** (lần trước: `from week_11.airflow.dags.etl.extract import extract` — note Day 3 mục 8).

> **Thói quen cần có: sau khi IDE tự thêm import, nhìn lại dòng nó vừa thêm.**
> Trong file DAG, import đúng chỉ có 3 nguồn — `airflow.*`, thư viện chuẩn/bên thứ ba (`pandas`, `pendulum`), và `etl.*` của mình. Thấy gì khác là sai.

---

## 8. Quy trình test

```bash
# đảm bảo stack đang chạy (docker compose run chỉ dựng postgres + redis)
docker compose up -d

# kịch bản 1: fail → notify_failure phải CHẠY
docker compose run --rm airflow-cli variables set force_fail true
docker compose run --rm airflow-cli dags test etl_daily 2026-01-12 2>&1 \
  | tee /tmp/retry.log | grep -E "starting task_id|Task failed|thất bại"

# kịch bản 2: thành công → notify_failure phải SKIPPED
docker compose run --rm airflow-cli variables set force_fail false
docker compose run --rm airflow-cli dags test etl_daily 2026-01-12 2>&1 \
  | grep -E "starting task_id|skipped|Loaded"
```

Trong UI: **Grid view** → bấm ô task đỏ → tab **Logs** → dropdown chọn attempt 1/2/3/4.
Đó là thứ tenacity **không** cho bạn thấy — chính là lý do Day 3 ta bỏ nó đi.

> Thấy `Network airflow_default Created` khi chạy `docker compose run` nghĩa là stack đang tắt — nó chỉ dựng postgres + redis, không có scheduler/worker.

---

## 9. Tự kiểm tra

- [ ] Lỗi nào retry cứu được, lỗi nào không? Retry gây hại gì với loại thứ hai?
- [ ] Vì sao cần exponential backoff thay vì delay đều?
- [ ] `load` fail giữa chừng khi đang ghi 3000/5000 dòng — bảng còn lại gì?
- [ ] Hai lớp bảo vệ khiến retry an toàn là gì?
- [ ] Task treo gây hại thế nào? Vì sao Airflow không tự phát hiện?
- [ ] `one_failed` khác `all_failed` ở đâu? Tình huống nào `all_failed` không chạy?
- [ ] Pipeline chạy thành công thì `notify_failure` ở trạng thái gì?
- [ ] Khi nào được dùng `>>` trong DAG viết bằng TaskFlow?