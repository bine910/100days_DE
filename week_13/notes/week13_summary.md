# Tuần 13 — Cloud cơ bản: GCS / BigQuery / IAM / chi phí

**Quan trọng · 20h · Tháng 4 — Cloud**
Project `bine910` (US) · Track B: BigQuery sandbox + MinIO thay GCS
Nguồn: marts tuần 12 (Olist) trong `postgres-dwh`, db `de_week9`
26/10 → 05/11/2026

---

## Kiến trúc sau tuần 13

```
analytics_marts.{fct_orders, dim_customers, dim_products}   [Postgres de_week9]
   │
   │  export_marts.py --run-date {{ ds }}      ← Airflow: dbt_daily task 2
   ▼
week_13/export/marts/
   ├── fct_orders/dt=YYYY-MM-DD/part-000.parquet    fact: partition theo NGÀY DỮ LIỆU
   ├── dim_customers/part-000.parquet                dimension: snapshot, ghi đè
   └── dim_products/part-000.parquet
   │
   │  upload_to_lake.py --run-date {{ ds }}    ← Airflow: dbt_daily task 3
   ▼
s3://de-marts/marts/...                        [MinIO · GCS khi billing thông]
   │
   │  bq load --source_format=PARQUET
   ▼
bine910.olist_marts.{fct_orders, dim_customers, dim_products}   [BigQuery US]

Airflow:  etl_daily (2h)  →  dbt_daily (3h): dbt_build >> export_marts >> upload_to_lake
```

---

## Nghiệm thu (theo sheet)

| Tiêu chí | Bằng chứng |
|---|---|
| Dùng service account đúng | `de-pipeline@bine910` với **2 binding ở 2 mức**: `jobUser` ở project + `WRITER` ở dataset. Test chứng minh bị chặn: `compute instances list` → denied, `bq mk -d` → `bigquery.datasets.create` denied |
| Query BigQuery được | 3 bảng nạp đủ: 891 / 99.441 / 32.951. `query_bigquery.sql` có 5 phép đo bytes + 3 câu business |
| Biết tránh tốn phí | 18 query trong 14 ngày = **0,0586 GB billed** = 0,006% free tier. Đo được pruning giảm 39,5×, biết sàn 10MB, dùng `--dry_run` làm phản xạ |

**Output bắt buộc:** `cloud_quickstart.md` ✓ · `query_bigquery.sql` ✓

**Output thêm:** `iam_notes.md` · `storage_layout.md` · `bigquery_notes.md` · `cost_notes.md` · `local_vs_cloud.md` · `export_marts.py` · `upload_to_lake.py` · `export_shifted.py` · `dbt_daily.py` (3 task)

---

## Bảy ngày

| Day | Nội dung | Kết quả |
|---|---|---|
| 1 | Resource hierarchy, project, billing, location | Project `bine910`, location US, billing `OPEN: False` → Track B |
| 2 | IAM, service account, least privilege | 2 binding đúng mức, 3 test chứng minh bị chặn |
| 3 | Object storage: layout, policy | Layout Hive, bucket `de-marts`, policy 1 bucket |
| 4 | Nạp BigQuery, bytes scanned | 891 dòng, 5 phép đo, 3 lỗi câm |
| 5 | Cost: pruning, dry-run, audit | Pruning 39,5×, phát hiện `DATE()` vẫn prune |
| 6 | Nối Airflow | `{{ ds }}` → `--run-date 2018-01-15` trong log thật |
| 7 | Dọn dẹp, nghiệm thu | 3 bảng còn lại, hoá đơn $0 |

---

## Năm câu tự kiểm — đáp án tham khảo

> Tự viết lại bằng lời của mình. Đọc đáp án rồi gật đầu không phải là biết.

**1. External table tiết kiệm gì, đánh đổi gì?**

Tiết kiệm: **storage** (dữ liệu nằm ở data lake, không nhân bản vào BigQuery) và **bước copy** (file đổi là query thấy ngay, không cần reload).

Đánh đổi: không có statistics, không cache, **mỗi query scan lại từ đầu**. Không có partition thật — chỉ dựa vào Hive path. Chậm hơn và khó tối ưu hơn native table.

Dùng khi: dữ liệu đổi liên tục, hoặc query thưa đến mức không đáng copy. Không dùng cho bảng chạy dashboard.

**2. Vì sao tách compute khỏi storage là điều kiện để có BigQuery?**

Postgres (OLTP) gắn chặt compute với storage: muốn query nhanh hơn thì nâng cả máy, và dữ liệu nằm trên disk của chính máy đó. Trần mở rộng là trần của một server.

BigQuery tách hai thứ: dữ liệu nằm ở Colossus, compute là cụm máy tạm thời được cấp khi có query rồi trả lại. Hệ quả:

- **Scale độc lập** — 100TB dữ liệu mà mỗi tháng query một lần thì chỉ trả tiền storage
- **Tính tiền theo bytes scanned mới có nghĩa** — vì compute không thuộc về ai, nó được đo theo lượng dùng
- **Không có "máy chủ của mình"** để tune — tối ưu duy nhất là giảm dữ liệu phải đọc

Đây là lý do mọi bài học Day 4–5 đều xoay quanh "đọc ít đi", không phải "chạy nhanh hơn".

**3. SA key nguy hiểm hơn mật khẩu Gmail ở điểm nào?**

| | Mật khẩu Gmail | SA key JSON |
|---|---|---|
| Hết hạn | có thể đổi, có chính sách | **9999-12-31** — không bao giờ |
| 2FA | có | **không** |
| Phát hiện lạm dụng | cảnh báo đăng nhập lạ | không có gì |
| Khi lộ | đổi mật khẩu là xong | **phải revoke key**, xoá file không cứu được |

Ai cầm file là **trở thành** service account đó, không cần biết gì thêm. Và vì nó dùng cho máy nên không ai để ý nó đăng nhập lúc 3h sáng.

**4. Query trả về 10 dòng vẫn tốn 50GB — giải thích bằng cơ chế**

BigQuery lưu **theo cột**, không theo dòng. Khi query đến, engine phải đọc toàn bộ dữ liệu của những cột được nhắc tới, trong những partition không bị loại, **rồi mới** lọc và cắt.

`LIMIT 10` là phép cắt ở **cuối** pipeline, sau khi scan đã xong. Nó không nói gì cho engine về việc đọc ít đi.

Số dòng trả về là output; bytes scanned là input. Tiền tính theo input.

Bằng chứng đo được: `SELECT *` = 120.085 bytes, `SELECT * LIMIT 10` = **120.085 bytes**, giống hệt.

**5. Khi nào KHÔNG nên đưa pipeline này lên cloud?**

- **Dữ liệu nhỏ và cố định.** Olist 99.441 dòng chạy trên Postgres local là đủ. Cloud thêm độ trễ mạng, thêm chi phí, thêm một hệ IAM phải học.
- **Query thưa nhưng dữ liệu lớn.** Trả tiền storage quanh năm cho thứ mỗi quý đọc một lần — rẻ hơn nếu để trên ổ cứng.
- **Ràng buộc pháp lý.** Dữ liệu cá nhân, y tế, tài chính có thể bị cấm rời khỏi lãnh thổ.
- **Không có ai quản chi phí.** Cloud không tự dừng khi hết tiền. Không có người theo dõi hoá đơn thì một query sai đốt tiền âm thầm.
- **Team chưa biết debug nó.** Pipeline chạy được trên cloud nhưng không ai đọc nổi lỗi IAM thì nó là nợ kỹ thuật, không phải tài sản.

Câu trả lời ngắn: **cloud giải bài toán quy mô và chia sẻ, không giải bài toán "trông cho hiện đại".**

---

## Bài học kỹ thuật

### Grain của partition

Partition `dt=X` phải chứa **những dòng thuộc về ngày X**, không phải **ảnh chụp toàn bảng tại ngày X**.

Lỗi gặp phải: `run_date` chỉ dùng đặt tên thư mục, SQL vẫn `SELECT *` không điều kiện → mọi partition chứa toàn bộ 99.441 dòng, nạp 2 partition thành 198.882. Script chạy xanh, layout đúng chuẩn, test idempotency vẫn pass — mà dữ liệu sai.

| | Snapshot | Incremental |
|---|---|---|
| Partition chứa | toàn bộ bảng | chỉ dòng của ngày đó |
| Đọc nhiều partition | **nhân bản** | cộng dồn đúng |
| Hợp với | dimension | fact |
| Hiện ra thành | `--replace` | append |

### Idempotency trong object storage

**Tên object là hàm của DỮ LIỆU, không phải của lần chạy.** `dt={run_date}/part-000.parquet` chạy lại thì đè lên chính nó; `part-{timestamp}.parquet` mất idempotency dù layout nhìn vẫn đẹp.

Cùng bài toán đã giải bằng UPSERT ở T9 và `unique_key` ở T12.

### Logical date, không phải now()

`{{ ds }}` render thành ngày mà lần chạy **đại diện**. Chạy lệnh ngày 2026-11-05, ghi vào `dt=2018-01-15`. Dùng `date.today()` thì backfill 5 ngày đè cả 5 vào một chỗ.

### Tiền trên BigQuery

| Kỹ thuật | Giảm | Trần |
|---|---|---|
| Column pruning | số cột | tối đa N lần (N = số cột) |
| Partition pruning | số ngày | **không có trần** |

Bảng 3 năm, 10 cột: kết hợp cả hai ≈ **10.000 lần**.

Đo được: nopart 4.176.522 bytes → part 105.714 bytes = **39,5×**.

Những thứ khác đã đo:
- `LIMIT` **không** giảm byte nào
- `WHERE` không tốn gì; **đọc thêm cột** mới tốn (40.087 − 30.294 = 9.793 = kích thước cột `status`)
- `count(*)` = **0 byte** (metadata)
- **Sàn 10MB mỗi query** — vừa là đơn vị tính tiền, vừa là sàn của `maximum_bytes_billed`, nên chốt này vô dụng dưới quy mô GB
- 7 partition ≈ **9×** 1 partition, không phải 7× — overhead metadata mỗi partition

**Dashboard là nguồn đốt tiền lớn nhất:** 20 dashboard × 10 widget × mỗi 5 phút = 1.728.000 query/tháng × 10MB = **16,5 TB**, vượt free tier 16 lần.

### Partition expiration tính theo ngày CỦA PARTITION

Không phải ngày nạp. Partition `2018-01-15` với expiration 60 ngày thì **quá hạn 8 năm trước khi load** → BigQuery nhận dữ liệu, tạo partition, thấy hết hạn, xoá luôn, **không báo lỗi**.

Đúng cả ở project có billing: đặt expiration 90 ngày trên bảng chứa dữ liệu lịch sử là mất dữ liệu im lặng.

### Một lý thuyết bị số liệu bác bỏ

Đã ghi ở Day 4: "bọc cột partition trong hàm là mất pruning". Đo ở Day 5:

```
WHERE purchased_at >= '2026-10-15' AND < '2026-10-16'  → 105.714 bytes
WHERE DATE(purchased_at) = '2026-10-15'                → 105.714 bytes
```

BigQuery **vẫn prune** với `DATE()`. Quy tắc "cột đứng trần" vẫn nên theo vì an toàn với mọi engine — nhưng đừng khẳng định khi chưa đo. Trên Postgres thì `DATE(col) = x` **vẫn mất index thật**: hai engine, hai optimizer, không chuyển kết luận qua lại.

### IAM: hai trục quyền

| Hệ | Trục 1 | Trục 2 |
|---|---|---|
| BigQuery | `jobUser` ở **project** (ai được tiêu compute) | `dataEditor` ở **dataset** (ai chạm dữ liệu nào) |
| Object storage | `arn:aws:s3:::de-marts` (thao tác lên bucket) | `arn:aws:s3:::de-marts/*` (thao tác lên object) |

Thiếu trục 1 ở BigQuery → có full quyền trên bảng vẫn không chạy nổi một query.
Thiếu trục 1 ở S3 → `PutObject` chạy ngon nhưng `mc ls` fail.

Cùng một cấu trúc, hai cú pháp.

### Credential vào container

Mount file từ host + env trỏ đường dẫn **trong container**. `COPY` vào Dockerfile là phát tán key vĩnh viễn qua image layer. Set env mà không mount thì container không thấy file — nó có filesystem riêng.

Cùng nguyên lý `minio-lake:9000` thay `localhost:9000`: **bên trong container là một thế giới riêng.**

---

## Sợi chỉ xuyên suốt: lệnh chạy xong ≠ việc đã xảy ra

| Ngày | Triệu chứng | Field thật sự cần đọc |
|---|---|---|
| 1 | `billing projects link` không lỗi | `billingEnabled: false` |
| 3 | `curl -o` tải về "thành công" | kích thước 405 bytes (binary ~25MB) |
| 4 | 5 job `bq load` đều `DONE` | `outputRows: 282` vs `numRows: 0`; `lastModifiedTime` = `creationTime` |

**Đừng tin exit code, đọc field trong output.** Đây là kỹ năng debug của DE, không tutorial nào dạy.

Đối lập: `Source file not found` (đứng sai thư mục) là lỗi **ồn ào** — dễ. Lỗi im lặng mới đắt.

Phụ lục cho IAM: **bảy cổng mỗi API call đi qua** — auth → API enablement → IAM → billing → quota → resource tồn tại → business logic. Lỗi luôn nói về **cổng đầu tiên bị chặn**. `compute instances list` fail ở `serviceusage.services.enable` (cổng 2→3), chưa bao giờ chạm tới cổng IAM của compute.

---

## Bẫy môi trường đã gặp

| Bẫy | Giải |
|---|---|
| `curl -o` ghi file cả khi server trả 410 | `curl -fL` |
| `apt install mc` = Midnight Commander | dùng `mc` trong container MinIO |
| `~/.docker/config.json` có `credsStore: desktop.exe` → mọi `docker pull` fail | `echo '{}' > ~/.docker/config.json` |
| botocore từ chối hostname có `_` | network alias `minio-lake` |
| Khối `networks:` sai thụt lề cắt đứt YAML anchor | `docker compose config` trước khi restart |
| `bq add-iam-policy-binding` → "requires allowlisting" | sửa `access` array + `bq update --source` |
| `airflow dags test` không sinh task instance (3.3) | dùng `airflow tasks test` |
| Đổi `OUT_ROOT` sau khi ghi → cây mồ côi 27MB | layout chốt **trước** khi upload |
| pandas nâng `int64` → `float64` khi có NULL | `dtype_backend="pyarrow"` |

---

## Trạng thái cuối tuần

| | |
|---|---|
| BigQuery | `fct_orders` 891 · `dim_customers` 99.441 · `dim_products` 32.951 — **tự hết hạn ~02/01/2027** |
| MinIO | `s3://de-marts/marts/` — 3 partition fact + 2 dimension |
| Chi phí | 18 query / 14 ngày = 0,0586 GB billed = **0,006%** free tier |
| Billing | `01E795-17CBAE-B4E007`, `OPEN: False` (VN yêu cầu prepayment) |
| SA key | `de-pipeline@bine910`, key `5cc8a72c...` tạo 28/10, hết hạn **9999-12-31**, ở `~/.gcp/de-pipeline.json` |

---

## Việc còn mở

- **Chưa chạm GCS thật.** External table trên object storage, IAM trên bucket GCS, lifecycle rule — học lý thuyết nhưng chưa làm. Khi billing `OPEN: True`:
  ```bash
  gcloud billing projects link bine910 --billing-account=01E795-17CBAE-B4E007
  gcloud billing projects describe bine910   # phải thấy billingEnabled: true
  ```
  Rồi đổi `upload_to_lake.py` từ `boto3` sang `google-cloud-storage`; volume mount `/home/binh/.gcp:/opt/airflow/.gcp:ro` đã chuẩn bị sẵn, DAG giữ nguyên.
- **SA key chưa dùng lần nào** — key không dùng là key chỉ có rủi ro. Cân nhắc revoke, tạo lại mất 10 giây.
- **Task upload chưa có retry/alert riêng.** Việc của T14 hoặc khi lên production.
- **`dim_customers` 99.441 = bằng số đơn** — Olist sinh `customer_id` mới theo từng order. Đếm khách thật phải dùng `customer_unique_id`. **Nhớ trước khi làm dashboard T15.**

---

## Thói quen cần giữ

1. **`--dry_run` trước mọi query trên bảng lớn.** Không phải để tiết kiệm tiền, mà để **biết thay vì đoán**.
2. **Đọc field trong output, không tin exit code.**
3. **Chạy từng lệnh, đọc kết quả, rồi mới chạy lệnh tiếp** — chạy một loạt rồi chỉ xem lệnh cuối là cách bỏ lỡ chỗ hỏng thật.
4. **Liệt kê việc ra trước khi sửa, tick từng dòng.** Nhận 2 ý thì sửa 2 ý; IAM sót một binding thì lỗi hiện ra ở tận 3 ngày sau.
5. **Suy từ nguyên tắc tuần trước, đừng trả lời theo cảm giác.** Câu idempotency đã có đáp án từ T9 và T12.