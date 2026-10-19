# Vì sao cần dbt

> Note Day 1 — Tuần 12. Viết sau khi đã dựng xong dbt project và kết nối `postgres-dwh`.

---

## 1. Ba vấn đề của pipeline tuần 9–11

### Transform chạy ở đâu, ai tiêu RAM?

- `etl_daily` đọc giá vàng từ CSV, xử lý bằng Pandas, ghi vào PostgreSQL.
- Phép transform đó chạy trong **process Python của task, bên trong container `airflow-worker`, trên máy WSL của tôi**. DataFrame nằm trong RAM của container đó.
- Hệ quả: dữ liệu càng lớn thì container càng dễ OOM, trong khi Postgres đang rảnh.
- Tệ hơn nữa là khi nguồn đã nằm sẵn trong warehouse (ví dụ muốn tính `gold_price_weekly` từ `gold_price_daily`): dữ liệu phải kéo từ DWH ra máy chạy script, tính xong đẩy ngược vào DWH — đi một vòng vô ích.
- dbt viết phép biến đổi bằng SQL và chạy thẳng trong DWH, không kéo dữ liệu đi đâu cả.

> Lưu ý tên gọi: `gold_price_daily` — "gold" ở đây là **vàng (XAU)**, không phải tầng Gold của Medallion. Bảng này đã clean + UPSERT nên thực chất gần **Silver**. Bảng Gold đúng nghĩa là thứ trả lời câu hỏi business — ví dụ `gold_price_weekly`.

### Người mới muốn biết bảng sinh ra từ đâu thì phải làm gì?

- Phải tự đọc code Python và SQL, tìm câu tạo bảng, lần theo thứ tự chạy.
- Không có lineage thì không biết bảng nào phụ thuộc bảng nào.
- Nghĩa là **không ai ngoài tôi trả lời được** — kể cả analyst, người cần câu trả lời đó nhiều nhất.
- dbt quản lý model + dependency, sinh ra documentation và lineage graph.

### Muốn thêm `gold_price_weekly` thì ai đảm bảo thứ tự chạy?

- Làm theo cách cũ: tôi tự nhớ phải chạy `gold_price_daily` trước. Không có hệ thống nào kiểm hộ.
- Chạy sai thứ tự thì bảng weekly tính trên dữ liệu cũ — **không báo lỗi**, chỉ sai số liệu.
- dbt đọc `ref()` trong SQL rồi tự dựng thứ tự chạy. Airflow vẫn cần, nhưng để **lập lịch và điều phối pipeline**, không phải để nhớ thứ tự model.

---

## 2. dbt làm gì, không làm gì

**dbt làm:**
- Biến đổi dữ liệu bằng SQL ngay trong DWH.
- Quản lý model, dependency, thứ tự thực thi.
- Test chất lượng dữ liệu, documentation, lineage.

**dbt KHÔNG làm — và ai làm thay:**

| Việc | Ai làm trong hệ của tôi |
|---|---|
| **E** — lấy dữ liệu từ nguồn | Python script / Airflow task |
| **L** — đưa dữ liệu vào warehouse | Python script / Airflow task (tuần này: `scripts/load_raw.py` nạp Olist vào schema `raw`) |
| **Schedule** — quyết định khi nào chạy | Airflow |

Nhớ: nếu có lúc tôi muốn dbt đi gọi API hay đọc file CSV, nghĩa là tôi đang dùng sai công cụ.

**Cơ chế:** dbt là một compiler, không phải runtime. Nó compile Jinja + SQL thành SQL thuần (xem ở `target/compiled/`), bọc thêm DDL theo materialization, rồi gửi **chữ** xuống Postgres. Postgres chạy và trả về số dòng đã ghi. Không có dòng dữ liệu nào đi qua máy tôi.

---

## 3. `ref()` đổi được gì

```sql
select
    date_trunc('week', price_date) as week_start,
    avg(close_price)               as avg_close
from {{ ref('gold_price_daily') }}
group by 1
```

Một dòng `{{ ref(...) }}` cho 4 thứ:

1. **Thứ tự chạy** — dbt biết weekly phụ thuộc daily, tự chạy daily trước. Không ai phải nhớ.
2. **Lineage** — graph tự sinh, analyst click vào xem được.
3. **Tài liệu** — câu trả lời cho "bảng này từ đâu ra" nằm ngay trong file SQL.
4. **Đổi môi trường** — cùng code chạy dev/prod, `ref()` tự phân giải đúng schema.

Hardcode tên bảng thì vẫn chạy đúng, nhưng mất sạch 4 thứ trên — và **sai lầm đó im lặng**, không có lỗi nào báo.

---

## 4. table vs view

| | `table` | `view` |
|---|---|---|
| dbt sinh ra | `create table as select ...` | `create view as select ...` |
| Lúc build | Postgres **chạy** SELECT, ghi kết quả xuống đĩa | Postgres **không chạy gì**, chỉ lưu lại câu SQL |
| Lúc có người query | Đọc dữ liệu đã ghi sẵn | Mở câu SQL ra chạy, **tại thời điểm query** |
| Chứa dữ liệu? | Có | Không |

Cốt lõi: **view không đọc và không lưu dữ liệu, nên nó chỉ có thể execute câu query mà nó lưu — vào lúc bị query.**

### Tình huống 3 mốc

- **9h** — `dbt run`. Câu SELECT chạy **một lần duy nhất** (nếu là table), kết quả thành dữ liệu vật lý. Từ giây đó bảng không còn liên hệ gì với raw.
- **10h** — raw thay đổi: thêm 500 order mới, sửa status 1 order cũ.
- **11h05** — analyst query.

| | `table` | `view` |
|---|---|---|
| 500 order thêm lúc 10h | **không thấy** | thấy |
| status sửa lúc 10h30 | **không thấy** | thấy |
| Dữ liệu nhìn thấy | của **9h** | của **11h05** |

Không có chuyện "tự update realtime". Postgres không theo dõi raw để sửa bảng hộ. Muốn table tươi lại thì phải chạy lại `dbt run` (materialized view có `REFRESH` gọi tay — khác hẳn, đã học ở T2).

### Kết luận

**Materialization là quyết định trả cái giá tính toán ở thời điểm nào: lúc build, hay lúc đọc.**

- `table` — trả lúc build. Query nhanh, nhưng dữ liệu chỉ tươi bằng lần `dbt run` gần nhất. **Độ tươi của dashboard = tần suất DAG**, không phải tần suất data về.
- `view` — trả lúc đọc. Luôn tươi, không tốn dung lượng, nhưng mỗi lượt query là chạy lại toàn bộ chuỗi JOIN bên dưới. 20 người mở dashboard = 20 lần JOIN.
- `dbt run` toàn view chạy gần như tức thì vì **không làm việc gì thật cả** — công việc bị dời sang cho người query gánh.

Nên: `staging: view` (mỏng, không ai query trực tiếp), `marts: table` (dày, bị query liên tục).

---

## Setup đã dựng

```
/mnt/c/DE/week_12/
├── .venv/                      # dbt-core 1.12.6 + dbt-postgres 1.11.0
├── notes/why_dbt.md
└── olist_dwh/
    ├── dbt_project.yml         # profile: olist_dwh; staging=view, intermediate=ephemeral, marts=table
    ├── profiles.yml.example
    └── models/{staging/olist, intermediate, marts}/
```

Kết nối: `localhost:5433` → `postgres-dwh`, db `de_week9`, schema mặc định `analytics`
(tách khỏi `public`, nơi Airflow ghi `gold_price_daily`).

`~/.dbt/profiles.yml` nằm **ngoài repo**, dùng `env_var('DWH_USER')` / `env_var('DWH_PASSWORD')` — không còn password trong file nào.

**Lệnh hay dùng**
```bash
cd /mnt/c/DE/week_12 && source .venv/bin/activate   # mở terminal mới là phải làm
cd olist_dwh
dbt debug     # kiểm tra kết nối
dbt parse     # kiểm tra cú pháp + dựng graph, KHÔNG đụng database
dbt run
```

Mọi lệnh `dbt` phải chạy từ thư mục chứa `dbt_project.yml`.

---

## TODO

- Password của `postgres-dwh` đang trùng username → xử lý ở **T13** (IAM, secrets management, quyền truy cập tối thiểu, thay mật khẩu yếu bằng secret phù hợp). Không commit thông tin đăng nhập vào Git.