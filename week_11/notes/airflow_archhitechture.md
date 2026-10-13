# Airflow Architecture — Week 11 / Day 1

> Ghi chú học Airflow 3.3.2 (Docker Compose). Nguồn: tự rút ra trong buổi học + docs chính thức.

---

## 1. Vì sao cần Orchestrator (không dùng cron + script)

Tình huống gốc: pipeline T9 chạy bằng `cron` + `python main.py`, log đổ dồn vào một file.
Sếp hỏi "thiếu data ngày 9 và 10" → lộ ra các vấn đề sau:

| # | Vấn đề | Cron + script | Airflow |
|---|---|---|---|
| 1 | Không có lịch sử run | Không biết tối 9/10 job có chạy không, chết giữa chừng hay không chạy | Bảng `dag_run` / `task_instance` lưu state từng ngày |
| 2 | Fail trong im lặng | Job chết lúc 2h sáng, phát hiện khi **người dùng cuối báo** | UI hiện task đỏ + alert/callback |
| 3 | Log không truy vấn được | 1 file 400MB trộn 3 tuần | Log tách theo task / theo run / theo attempt |
| 4 | Không có đường phục hồi | Data mất luôn, phải tự nghĩ cách lấp | Backfill / clear task |
| 5 | Không biết ngày nào thiếu | Phải `grep` log bằng mắt | Query metadata DB |
| 6 | Backfill thủ công | Dừng giữa chừng không biết ở đâu, không chạy song song được | Scheduler quản lý từng run riêng, có `max_active_runs` |
| 7 | Phụ thuộc giữa pipeline | Chỉ hẹn được *giờ*, không hẹn được *điều kiện* → A chậm thì B chạy trên data cũ mà **không báo lỗi** | B chờ A thành công |
| 8 | Không có metric | Không biết job chạy mất bao lâu, có chậm dần không | `duration` lưu theo từng run |
| 9 | Không có nơi quan sát tập trung | 20 pipeline / 3 server = ssh 3 lần, đọc 20 crontab | Một UI duy nhất |

---

## 2. Ba câu chốt

1. **Cron lập lịch *thời điểm*. Orchestrator quản lý *trạng thái*.**
   Airflow lưu state của từng task, từng ngày vào Postgres thay vì để nó trôi trong file log.
   → Nguyên tắc đã học ở T9 áp lên chính Airflow: **state phải nằm ở nơi query được, không phải trong log.**

2. **Tách task = thu nhỏ đơn vị retry.**
   `main()` gọi 3 hàm: `transform` fail → chạy lại cả 3, gọi lại API đã thành công, tốn quota + thời gian.
   3 task rời: Airflow biết `extract` đã success → retry **chỉ** `transform`, rồi đi tiếp `load`.

3. **DAG = Directed Acyclic Graph.**
   - *Directed*: cạnh có mũi tên → biết thứ tự.
   - *Acyclic*: không chu trình → không deadlock.
   Nếu cho A → B → A: A chờ B, B chờ A, không ai chạy được. Airflow bắt lỗi này ngay lúc **dag-processor parse file** (`Cycle detected`), DAG không bao giờ được schedule.

---

## 3. Kiến trúc Airflow 3

### Component

| Component | Việc nó làm |
|---|---|
| **dag-processor** | Quét `dags/`, parse file `.py` → ghi định nghĩa DAG vào metadata DB. Lặp vài chục giây/lần. |
| **scheduler** | Đọc metadata DB, xét run nào tới hạn, task nào đủ điều kiện → đẩy vào hàng đợi. |
| **worker** | Nhận task từ hàng đợi và thực thi code. `concurrency: 16` = chạy được 16 task song song. |
| **api-server** | UI (port 8080) + REST API. |
| **triggerer** | Cho deferrable task (chờ sự kiện mà không chiếm worker). Chưa dùng tuần này. |
| **metadata DB** (Postgres) | Toàn bộ state: `dag_run`, `task_instance`, `xcom`, `connection`. |
| **redis** | Message broker — chỉ cần khi dùng CeleryExecutor. |

### Luồng

```
   sửa file etl_daily.py
            │
            ▼
   ┌─────────────────┐   parse định kỳ
   │  dag-processor  │─────────────────┐
   └─────────────────┘                 │
                                       ▼
                            ┌────────────────────┐
                            │   metadata DB      │
                            │   (PostgreSQL)     │
                            │  dag_run           │
                            │  task_instance     │
                            │  xcom, connection  │
                            └────────────────────┘
                              ▲      │
                   ghi state  │      │  đọc: run nào tới hạn?
                              │      ▼
                            ┌────────────────────┐
                            │    scheduler       │
                            └────────────────────┘
                                     │ đẩy task
                                     ▼
                            ┌────────────────────┐
                            │   redis (queue)    │
                            └────────────────────┘
                                     │ lấy task
                                     ▼
                            ┌────────────────────┐
                            │      worker        │  ← code của mình chạy ở đây
                            └────────────────────┘

   api-server  ──đọc/ghi──▶  metadata DB        (UI :8080 + REST API)
   triggerer   ──────────▶   deferrable tasks
```

### Hai điểm cần khắc

- **dag-processor tách khỏi scheduler** là thay đổi lớn của Airflow 3 (ở 2.x nó nằm trong scheduler).
  Hệ quả: code DAG lỗi cú pháp **không còn làm chết scheduler**.
- **Metadata DB là nội tạng của Airflow, KHÔNG phải warehouse.**
  Day 3 dựng một Postgres thứ hai riêng cho data. Nhầm chỗ này là lỗi kinh điển của người mới.

---

## 4. Những thứ dễ sập bẫy

- **DAG mới mặc định là paused.** Paused = scheduler bỏ qua DAG hoàn toàn (không xét lịch, không tạo run), dù code vẫn được parse bình thường. Không liên quan đến việc DAG đang chạy hay không.
- Ngược lại, bật toggle một DAG có `catchup=True` và `start_date` lùi 7 ngày → scheduler tạo **7 run cùng lúc**. (Giới hạn bằng `max_active_runs`.)
- **Lần đầu `up`: chờ đủ 2–3 phút** rồi mới kết luận có gì hỏng. `airflow-worker` healthy chậm hơn các service khác.
- `airflow-init` ở trạng thái `Exited (0)` là **đúng** — nó chạy một lần (tạo schema + user admin) rồi tắt.
- `FERNET_KEY` rỗng vẫn chạy local được, nhưng nó là khoá mã hoá password trong bảng `connection` → set trước khi tạo Connection ở Day 3.
- `AIRFLOW__CORE__EXECUTOR: CeleryExecutor` là lý do có `redis` + `airflow-worker`. Đổi sang `LocalExecutor` thì bỏ được cả hai (nhẹ RAM hơn).

---

## 5. Setup đã dựng

```
C:\DE\week_11\airflow\
├── docker-compose.yaml      # official, Airflow 3.3.2
├── .env                     # FERNET_KEY, AIRFLOW_UID  (gitignore)
├── .env.example
├── dags/                    # mount → /opt/airflow/dags
├── logs/
├── plugins/
└── config/
```

Mount `./dags:/opt/airflow/dags` ⇒ sửa file trên máy là container thấy ngay, **không cần rebuild image**.

### Lệnh hay dùng

```bash
docker compose up airflow-init          # chạy 1 lần, tạo schema + user admin/admin
docker compose up -d
docker compose ps -a                    # -a để thấy cả container đã exit
docker compose logs airflow-worker --tail 30
docker compose run --rm airflow-cli dags list
docker compose run --rm airflow-cli dags test <dag_id> 2026-10-01
docker compose down --volumes --remove-orphans   # reset sạch
```

UI: http://localhost:8080 — `airflow / airflow`

---

## 6. Tự kiểm tra (trả lời lại sau 1 tuần)

- [ ] Sửa file DAG → component nào biết đầu tiên?
- [ ] DAG paused thì scheduler làm gì?
- [ ] `print("hello")` trong task hiện ở log container nào?
- [ ] Vì sao retry 3 task rời rẻ hơn retry 1 hàm `main()`?
- [ ] Airflow bắt lỗi chu trình ở thời điểm nào — lúc parse hay lúc chạy?