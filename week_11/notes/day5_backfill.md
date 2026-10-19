# Catchup & Backfill — Week 11 / Day 6

> Tiêu chí chấm chính của tuần: *"backfill được; không duplicate"*.
> Kết quả: 7 dòng (05/01 → 13/01), chạy backfill 2 lần vẫn đúng 7 dòng, 0 ngày trùng.

---

## 1. Catchup ≠ Backfill

| | Ai kích hoạt | Điều khiển bằng |
|---|---|---|
| **Catchup** | Scheduler **tự động** tạo run cho các interval quá khứ chưa chạy, khi DAG được bật | `catchup=True/False` trong `@dag` |
| **Backfill** | Bạn **chủ động** yêu cầu chạy lại một khoảng ngày cụ thể | CLI `backfill create` hoặc nút trong UI |

Airflow 3 mặc định `catchup_by_default=False`. Airflow 2 mặc định `True` — nơi nhiều người bật DAG lên rồi bị hàng trăm run đồng loạt khởi động.

### Ba trạng thái dễ lẫn

| Cấu hình | Scheduler tạo run nào |
|---|---|
| `schedule=None` | **Không bao giờ** tự tạo run |
| `catchup=False` | Chỉ interval **gần nhất** trở đi (1 run khi bật) |
| `catchup=True` | **Mọi** interval từ `start_date` |

### Tính trước số run ⚠️

`start_date=2026-01-01`, `schedule="0 2 * * *"`, hôm nay 19/10, bật `catchup=True`:
→ **~291 run** được tạo cùng lúc.

> Đây là cách phổ biến nhất để người mới làm nghẽn Airflow của chính mình.
> **Luôn đếm số run trước khi bật `catchup=True`.**

### Hai giới hạn chồng nhau

| Giới hạn | Khống chế | Mặc định |
|---|---|---|
| `max_active_runs` | Số **dag run** chạy đồng thời | 16 |
| `concurrency` của Celery worker | Số **task instance** chạy đồng thời | 16 |

16 run × 3 task = 48 task muốn chạy, worker chỉ có 16 slot → phần còn lại ở `queued`.

---

## 2. Chạy backfill

```bash
docker compose run --rm airflow-cli backfill create \
  --dag-id etl_daily \
  --from-date 2026-01-05 \
  --to-date 2026-01-12
```

Khác `dags test`: backfill đi qua **scheduler/worker thật**, nên xem được tiến trình trong UI và chạy song song được.

Run tạo ra có `run_id` dạng `backfill__2026-01-05T02:00:00+00:00` và `backfill_id` riêng.

> `logical_date` của chúng là **02:00**, khớp `schedule="0 2 * * *"` — khác `00:00` khi chạy `dags test` thủ công.
> Backfill tạo run **đúng theo timetable**, không tuỳ tiện. Vì `transform` lọc theo `logical_date.date()` nên phần giờ không ảnh hưởng — đúng lý do chọn phương án A ở Day 4.

**DAG phải được unpause trước**, nếu không run nằm `queued` mãi (scheduler bỏ qua hoàn toàn DAG paused — bài học Day 1):

```bash
docker compose run --rm airflow-cli dags unpause etl_daily
```

### Cờ đáng nhớ

`backfill create --run-on-latest-version` — bắt run dùng **phiên bản code mới nhất** thay vì version gắn với lúc tạo. Xem mục 4.

```bash
docker compose run --rm airflow-cli backfill create --help
```

### CLI Airflow 3 chỉ có `backfill create`

`backfill list` / `backfill cancel` **không tồn tại** ở CLI — quản lý backfill qua UI hoặc REST API.

---

## 3. Song song thật

```
backfill__2026-01-05 | running | 2026-10-19 02:21:41.963829+00
backfill__2026-01-06 | running | 2026-10-19 02:21:41.967915+00
backfill__2026-01-07 | running | 2026-10-19 02:21:41.972181+00
...
backfill__2026-01-11 | running | 2026-10-19 02:21:41.986737+00
```

7 run khởi động cách nhau **23 mili-giây**. Không tuần tự.

> Đây là khác biệt cốt lõi so với script T9: `python main.py --start-date ... --end-date ...` chạy 7 ngày **tuần tự trong một process**.
> Airflow coi mỗi ngày là một **đơn vị độc lập** nên chạy được đồng thời.

Chính là câu hỏi a.3 ở Day 1: *"muốn chạy 5 ngày song song, script làm được không?"*

---

## 4. Dag version — bài học lớn nhất hôm nay ⚠️⚠️

**Triệu chứng:** sửa code xong, clear task cho chạy lại, nhưng attempt mới **vẫn báo lỗi cũ**.

```
attempt=4.log → "exc_value": "Variable.get() got an unexpected keyword argument 'default_var'"
```
dù file trong container đã đúng:
```bash
docker compose exec airflow-worker grep -n "Variable.get" /opt/airflow/dags/etl_daily.py
# 43:  if Variable.get("force_fail", default="false") == "true":
```

**Nguyên nhân:** Airflow 3 gắn mỗi dag run vào một **dag version** cụ thể. Manh mối trong log: `dag_version_id=UUID('01a14450-...')` — cùng ID với các attempt trước khi sửa.

> **Sửa code KHÔNG ảnh hưởng tới run đã tồn tại.** Run cũ tiếp tục dùng bản serialize cũ, kể cả khi file đã thay đổi.

Đây là **tính năng**, không phải bug — nó đảm bảo một run chạy nhất quán một phiên bản code. Nhưng nó giữ luôn cả bug.

**Hai cách xử lý:**
1. `backfill create --run-on-latest-version` (cách đúng, nhẹ)
2. Xoá DAG rồi tạo lại run mới:
```bash
docker compose run --rm airflow-cli dags delete etl_daily -y
# đợi ~45-60s cho dag-processor đăng ký lại TỪ FILE MỚI
docker compose run --rm airflow-cli tasks list etl_daily    # xác nhận DAG đã quay lại
docker compose run --rm airflow-cli dags unpause etl_daily
docker compose run --rm airflow-cli backfill create --dag-id etl_daily --from-date ... --to-date ...
```

`dags delete` xoá mọi dag run (gồm backfill dang dở) và bản serialize. **File không bị đụng.** Dữ liệu trong `postgres-dwh` cũng không.

> Chạy `backfill create` quá sớm sau `dags delete` → `DagNotFound: Could not find dag etl_daily`. Phải chờ dag-processor.

---

## 5. `tasks clear` — chạy lại không cần backfill mới

```bash
docker compose run --rm airflow-cli tasks clear etl_daily \
  --start-date 2026-01-05 --end-date 2026-10-19 -y
```

Xoá trạng thái task instance → scheduler lên lịch chạy lại chúng. Cách sửa lỗi rồi chạy lại mà **không** phải tạo backfill mới.

(Nhưng vẫn dính vấn đề dag version ở mục 4 — clear không đổi version của run.)

---

## 6. Test idempotency — phần quyết định

```bash
# chạy backfill lần 2, ĐÚNG khoảng cũ
docker compose run --rm airflow-cli backfill create \
  --dag-id etl_daily --from-date 2026-01-05 --to-date 2026-01-12

# count phải KHÔNG ĐỔI
docker compose exec postgres-dwh psql -U dwh -d de_week9 -c "
SELECT count(*), min(date), max(date) FROM gold_price_daily;"

# và không ngày nào xuất hiện 2 lần
docker compose exec postgres-dwh psql -U dwh -d de_week9 -c "
SELECT date, count(*) FROM gold_price_daily GROUP BY date HAVING count(*) > 1;"
```

Kết quả:
```
 count |    min     |    max
-------+------------+------------
     7 | 2026-01-05 | 2026-01-13

 date | count
------+-------
(0 rows)
```

Câu thứ hai bắt được cả trường hợp trùng mà `count` tổng không lộ ra.

> Hai con số này là **bằng chứng của toàn bộ tuần**: pipeline chạy lại bao nhiêu lần cũng ra cùng một kết quả.
> Cơ chế đằng sau: transaction rollback + `ON CONFLICT (date) DO UPDATE` (note Day 5 mục 3).

### Dữ liệu thiếu ngày là bình thường

6 dòng cho 8 ngày lịch (05/01–12/01) — 2 ngày thiếu là **cuối tuần**, thị trường vàng nghỉ.
Một số run load 0 dòng mà vẫn xanh. Đúng nguyên tắc Day 4: **không có dữ liệu ≠ lỗi**.

---

## 7. Lệnh theo dõi backfill

CLI `dags list-runs -d` là cú pháp **Airflow 2**, cờ `-d` đã bị bỏ. Hỏi thẳng metadata DB chắc chắn hơn:

```bash
# trạng thái các dag run
docker compose exec postgres psql -U airflow -d airflow -c "
SELECT run_id, state, start_date, end_date FROM dag_run
WHERE dag_id='etl_daily' ORDER BY logical_date;"

# tổng hợp theo state
docker compose exec postgres psql -U airflow -d airflow -c "
SELECT state, count(*) FROM dag_run WHERE dag_id='etl_daily' GROUP BY state;"

# task nào đang kẹt ở đâu
docker compose exec postgres psql -U airflow -d airflow -c "
SELECT task_id, state, count(*) FROM task_instance
WHERE dag_id='etl_daily' GROUP BY task_id, state ORDER BY task_id;"

# DAG có đang paused không
docker compose exec postgres psql -U airflow -d airflow -c "
SELECT dag_id, is_paused FROM dag WHERE dag_id='etl_daily';"
```

`postgres` = metadata DB của Airflow. `postgres-dwh` = warehouse. Đừng nhầm.

### Đọc log của một task cụ thể

```bash
docker compose exec airflow-worker sh -c "cat '/opt/airflow/logs/dag_id=etl_daily/run_id=backfill__2026-01-09T02:00:00+00:00/task_id=transform_gold_price/attempt=4.log'" \
  | grep -o '"exc_value":"[^"]*"'
```

Log Airflow 3 ở dạng JSON mỗi dòng → `grep -o '"exc_value":"[^"]*"'` lấy nhanh thông điệp lỗi.

**Log attempt cũ không bị ghi đè.** Xem nhầm attempt cũ sẽ chẩn đoán sai. Liệt kê attempt có sẵn:
```bash
docker compose exec airflow-worker sh -c "ls -t /opt/airflow/logs/dag_id=etl_daily/run_id=backfill__2026-01-06*/task_id=transform_gold_price/"
```

---

## 8. Bẫy chẩn đoán hôm nay

### "Chậm" thực ra là "đang fail và retry"

8 run `running` 5 phút mà DB chưa có dòng nào → tưởng tải nặng. Thực ra:
```
duration=0.79  exit_code=0  final_state=up_for_retry
```
Task chỉ chạy 0.5–0.8 giây rồi fail. Thời gian trôi qua là `retry_exponential_backoff` chờ giữa các lần.

Và vì lỗi là `TypeError` (**lỗi logic**), retry không bao giờ cứu được — nhưng vẫn thử 3 lần, tốn gần 4 phút. 8 run cùng lúc nên nhìn từ ngoài giống "hệ thống chậm".

> Đúng điều đã học Day 5: *với lỗi logic, retry làm chậm phát hiện vấn đề*. Hôm nay trải nghiệm thật.
> **Khi nhiều run `running` lâu bất thường — ĐỌC LOG TASK TRƯỚC**, đừng cho rằng đó là tải nặng.

### `dags list-import-errors` phải là lệnh ĐẦU TIÊN

DAG biến mất sau `dags delete` → đã đi qua restart, delete lại, chờ đợi… 10 phút.
Nguyên nhân thật: `IndentationError` ở dòng 43 — lộ ra trong 5 giây bằng:
```bash
docker compose run --rm airflow-cli dags list-import-errors
```

Câu này đã ghi trong note Day 3 mục 11 mà vẫn quên dùng.

**Kiểm tra cú pháp không cần Airflow:**
```bash
docker compose exec airflow-worker python -c "import ast; ast.parse(open('/opt/airflow/dags/etl_daily.py').read()); print('OK')"
```

### Lỗi do sửa code vội

```python
if Variable.get("force_fail", default="false") == "true":
ctx = get_current_context()          # ← IndentationError: khối if không có thân
```
Sửa dòng `if` nhưng xoá mất dòng `raise` bên dưới. Đúng phải là:
```python
        if Variable.get("force_fail", default="false") == "true":
            raise ValueError("Cố tình fail để test retry")

        ctx = get_current_context()
```

### `Variable.get` ở Airflow 3

```python
Variable.get("force_fail", default="false")       # ĐÚNG — airflow.sdk
Variable.get("force_fail", default_var="false")   # SAI — cú pháp Airflow 2
```

---

## 9. Kết quả Day 6 — tiêu chí T11

| Tiêu chí | Trạng thái |
|---|---|
| DAG chạy xanh | ✓ 8 run `success` |
| Task tên rõ nghĩa | ✓ `extract_gold_price` / `transform_gold_price` / `load_gold_price` / `notify_failure` |
| Backfill được | ✓ 7 run, song song, đúng timetable |
| Không duplicate | ✓ chạy 2 lần vẫn 7 dòng, 0 ngày trùng |
| Lỗi có log để debug | ✓ (dùng khá nhiều hôm nay) |

---

## 10. Tự kiểm tra

- [ ] `catchup=False` tạo bao nhiêu run khi bật DAG? Khác `schedule=None` thế nào?
- [ ] `start_date` lùi 10 tháng + `catchup=True` = bao nhiêu run? Hai giới hạn nào khống chế chúng?
- [ ] Backfill khác `dags test` ở điểm nào?
- [ ] Vì sao sửa code mà run cũ vẫn chạy bản lỗi? Hai cách xử lý?
- [ ] Hai câu SQL chứng minh pipeline idempotent là gì?
- [ ] Nhiều run `running` lâu bất thường — việc đầu tiên cần làm?
- [ ] DAG không hiện trong `dags list` — lệnh đầu tiên?