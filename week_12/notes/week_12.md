# Tuần 12 — dbt core: staging / intermediate / mart + tests + docs

**Bắt buộc · 24h · Tháng 3 — Transform**
Nguồn dữ liệu: Olist Brazilian E-Commerce (tái dùng từ T4)
Warehouse: `postgres-dwh` (container tuần 11), database `de_week9`

---

## Kiến trúc sau tuần 12

```
CSV Olist (5 file)
   │
   │  scripts/load_raw.py          ← chữ L, Python làm
   ▼
raw.{orders, order_items, customers, products, order_payments}     [5 table]
   │
   │  ════════ RANH GIỚI EL | T ════════
   │  dbt: {{ source('olist', ...) }}
   ▼
analytics_staging.stg_olist__*                                      [5 view]
   │     rename · cast · chuẩn hoá · lọc rác kỹ thuật
   │     KHÔNG join, KHÔNG aggregate, KHÔNG business logic
   │  {{ ref() }}
   ▼
int_order_items_enriched, int_order_payments_agg      [ephemeral — KHÔNG có trong DB]
   │     logic dùng lại bởi nhiều mart
   │  {{ ref() }}
   ▼
analytics_marts.{fct_orders, dim_customers, dim_products}           [3 table]
   │     fct_orders: incremental, unique_key='order_id'
   ▼
T15: Metabase dashboard

────────────────────────────────────────────────────────
Airflow:   etl_daily (2h)  ──lệch giờ──▶  dbt_daily (3h)  ──▶  dbt build
```

### Ranh giới EL / T nằm ở đâu, và vì sao đặt ở đó

Ranh giới là **`source()`**: từ `raw` trở lên là việc của Python/Airflow, từ `raw` trở xuống
là việc của dbt.

*(← viết 2–3 câu lý do của riêng mình vào đây: vì sao transform nên xảy ra TRONG warehouse
chứ không phải trong container worker. Nhắc lại từ note Day 1: ai tiêu RAM, ai trả lời được
câu "bảng này từ đâu ra", ai đảm bảo thứ tự chạy.)*

---

## Nghiệm thu

| Tiêu chí (theo sheet) | Kết quả |
|---|---|
| `dbt run` / `dbt test` pass | 8 model, 24 test, 1 WARN có ghi lý do |
| ≥ 5 model qua 3 tầng | 8 (5 staging + 2 intermediate + 3 mart) |
| ≥ 10 test, ≥ 1 singular | 24 test, 2 singular |
| Lineage không có đường tắt | xác nhận bằng graph — không source nào nối thẳng lên mart |
| 1 model incremental chạy 2 lần không nhân đôi | `fct_orders`: 99.441 / 99.441 |
| Mart phục vụ dashboard | sẵn sàng cho T15 |
| Mart trả lời 3 câu hỏi business | → `business_questions.sql` |

---

## Các bài học rải rác trong tuần

### dbt

- **Mọi test dbt là một câu SELECT tìm dòng sai.** Rỗng = pass. Generic test là SQL
  dbt sinh hộ, singular test là SQL mình viết — cùng một cơ chế. Đọc được ở
  `target/compiled/.../<tên_test>.sql`.
- **`unique` bỏ qua NULL** (`where <cột> is not null`). Vì thế khoá chính luôn cần
  **cả hai**: `unique` VÀ `not_null`. Thiếu `not_null`, một cột toàn NULL vẫn pass `unique`.
- **dbt áp config theo THƯ MỤC, không theo tên file.** Đặt `int_*.sql` trong
  `models/staging/` thì nó ăn config của staging → tạo view ở sai schema, mà vẫn chạy xanh.
- **`ephemeral` không tạo gì trong DB** — nó được dán vào model dùng nó dưới dạng
  `__dbt__cte__<tên>`. Nếu chưa ai `ref()` tới, `dbt run` không làm gì cả
  (`Finished running` với danh sách rỗng).
- **Custom schema được NỐI vào target schema**: `+schema: staging` với target `analytics`
  cho ra `analytics_staging`, không phải `staging`.
- **Đổi schema/materialization không dọn object cũ.** dbt chỉ quản nơi nó đang build;
  view/table ở chỗ cũ phải drop tay.
- **YAML dùng `#` để comment, không phải `//`.** Viết `//` thì nó bị nuốt vào giá trị:
  `materialized: 'ephemeral //ghi chú...'` → `No materialization found`.
- **Test có tham số (`to`, `field`, `values`) phải nest dưới `arguments:`** từ dbt 1.12.
  Cách cũ vẫn chạy nhưng in deprecation warning. Sửa ngay lúc gặp, đừng dồn.
- **`accepted_values` bắt được thứ mình không biết là mình không biết** —
  `payment_type` có `not_defined` (3 dòng) mà mình không hề liệt kê.

### Phương pháp

- **Khi test đỏ: NHÌN DỮ LIỆU trước khi sửa test.** 303 ca lệch revenue/payment
  → tìm ra nguyên nhân là lãi trả góp → thu hẹp phạm vi test → còn 29.
  Nếu nới ngưỡng cho hết đỏ thì mất luôn khả năng phát hiện lỗi thật.
- **Test phải kiểm một BẤT BIẾN thật.** "Revenue = payment" không phải bất biến
  (có trả góp, có voucher). "Revenue = payment khi không trả góp" thì gần hơn.
- **`severity: warn` giữ nguyên điều kiện kiểm, chỉ đổi mức nghiêm trọng.**
  Nếu mai 29 nhảy lên 3000 thì vẫn thấy. Nới ngưỡng thì không.
- **Test chưa bao giờ đỏ là test chưa được kiểm chứng.** Phá dữ liệu một lần
  để biết nó thật sự bắt được lỗi.
- **Mỗi lần sửa một mục đích.** Trộn "thêm description" với "thêm test" vào một vòng
  thì khi đỏ không biết lỗi từ đâu.

### Git / môi trường

- **Dataset KHÔNG commit vào git.** Git lưu toàn bộ lịch sử — mỗi lần CSV đổi là một
  bản sao mới, repo phình vĩnh viễn và không bao giờ nhỏ lại. Data thô thuộc về
  object storage (MinIO), cùng hạng với `.venv` / `target` / `logs`.
  Đã phải dùng `git filter-repo` dọn: **141MB → 38MB**.
- **`.gitignore` viết TRƯỚC lệnh đầu tiên**, không phải sau khi file đã lọt vào.
  `.gitignore` chỉ chặn file **chưa** được track; file đã commit phải `git rm --cached`.
- **Ba loại lỗi kết nối, đọc dòng CUỐI traceback là biết:**

  | Thông báo | Nghĩa | Sửa ở đâu |
  |---|---|---|
  | `Connection refused` | không ai nghe ở port đó | container tắt / sai port |
  | `password authentication failed` | có server, sai credentials | biến môi trường |
  | `could not translate host name` | không phân giải được tên | **sai mạng** (xem dưới) |
  | `database/schema does not exist` | vào được, thiếu object | chạy lệnh tạo |

- **`localhost` trong container là chính container đó.** Từ trong mạng Docker Compose,
  gọi service bằng **tên service** và **port thật bên trong** (`postgres-dwh:5432`),
  không phải port map ra host (`localhost:5433`).
- **Anchor YAML**: `&tên` định nghĩa khối, `<<: *tên` dán khối đó vào chỗ khác.
  Biến đặt ngoài khối được đặt tên thì không đi theo — dù nằm cùng file.
- **Lỗi "sửa một nửa"**: nhận nhiều điểm cần sửa, sửa chỗ được chỉ tận nơi, bỏ chỗ
  phải tự suy ra. Lặp 5 lần trong tuần. Cách chặn: **liệt kê từng việc ra trước khi gõ,
  gạch khi xong.**

### Airflow

- **DAG không có task vẫn báo "success".** Python không lỗi, Airflow không lỗi —
  chỉ `run_duration` bất thường lộ ra (0,1s thay vì 35s).
  Phản xạ: sau `dags test` luôn đếm số dòng `starting task_id`. Không dòng nào = không chạy gì.
- `@task` và Operator là **hai cách viết khác nhau, không lồng vào nhau**.
  `@task` bọc một hàm Python; `BashOperator` tự nó đã là một task, khai báo ở thân hàm DAG.
- DAG mới mặc định **paused**.

---

## Lệnh hay dùng

```bash
# môi trường
cd /mnt/c/DE/week_11/airflow && docker compose up -d postgres-dwh
cd /mnt/c/DE/week_12 && source .venv/bin/activate && cd olist_dwh

# dbt
dbt debug                      # kiểm kết nối
dbt parse                      # kiểm cú pháp, KHÔNG đụng database
dbt compile --select <model>   # xem SQL sinh ra
dbt build                      # run + test xen kẽ theo graph  ← dùng cái này
dbt run --select <model>+      # model này + downstream
dbt run --select +<model>      # model này + upstream
dbt ls   --select +<model>     # chỉ liệt kê, không chạy
dbt run --select <model> --full-refresh
dbt docs generate && dbt docs serve --port 8081

# trong Airflow
docker compose run --rm airflow-cli bash -c \
  "cd /opt/airflow/dbt && dbt debug --target airflow --profiles-dir /opt/airflow/.dbt"
docker compose run --rm airflow-cli tasks list dbt_daily
docker compose run --rm airflow-cli dags test dbt_daily 2026-10-25 2>&1 \
  | grep -E "starting task_id|PASS=|Command exited"
```

**Mọi lệnh `dbt` phải chạy từ thư mục chứa `dbt_project.yml`.**

---

## Cấu hình

| | |
|---|---|
| dbt | `dbt-core 1.12.6` + `dbt-postgres 1.11.0` (cả hai, từ 1.8 adapter tách khỏi core) |
| profile | `~/.dbt/profiles.yml` — **ngoài repo**, dùng `env_var()` |
| target `dev` | `localhost:5433` — chạy từ WSL |
| target `airflow` | `postgres-dwh:5432` — chạy trong container |
| schema | `raw` → `analytics_staging` → `analytics_marts` |

```yaml
# dbt_project.yml
models:
  olist_dwh:
    staging:      {+materialized: view,      +schema: staging}
    intermediate: {+materialized: ephemeral}
    marts:        {+materialized: table,     +schema: marts}
```

---

## Backlog (cố ý không làm tuần này)

| Chủ đề | Vì sao để sau |
|---|---|
| `dbt_utils` và các package | Dễ copy macro mà không hiểu SQL bên dưới |
| Snapshots (SCD2 kiểu dbt) | Đã làm SCD2 bằng SQL tay ở T6, chưa cần lớp trừu tượng |
| Exposures, macro tự viết | Chưa có nhu cầu thật |
| dbt-cosmos / DockerOperator | Mỗi model một task Airflow — graph đúng, retry từng model. Tối ưu, không phải nền |
| `ExternalTaskSensor` / Assets | `dbt_daily` hiện chạy lệch giờ với `etl_daily`, chưa có phụ thuộc thật |
| 29 ca lệch revenue/payment | Nghi voucher/giảm giá, chưa xác minh. Đang `severity: warn` |

## TODO kỹ thuật

- [ ] Password `postgres-dwh` trùng username (`dwh`/`dwh`), container mở `0.0.0.0:5433`
      → xử lý ở **T13** (IAM, secrets, least privilege). Không commit credentials vào git.
- [ ] `_tmp_with_discount.csv` còn lẫn trong `week_4/.../data/raw/` — file tạm, không
      thuộc về thư mục raw.
- [ ] Xoá `/mnt/c/DE_backup_20261020` (818MB) sau khi chắc chắn repo ổn.