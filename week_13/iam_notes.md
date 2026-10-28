# IAM — Week 13 Day 2

Project: `bine910` · Dataset: `olist_marts` (US) · Track B (BigQuery sandbox)
Ngày: 2026-10-28

---

## 1. Binding là gì

Một **binding** là bộ ba:

```
resource :  dataset bine910:olist_marts
role     :  roles/bigquery.dataEditor
member   :  serviceAccount:de-pipeline@bine910.iam.gserviceaccount.com
```

Đọc: *trên resource này, member này được cấp role này.*
Tập hợp binding gắn trên một resource = **allow policy** của resource đó.

Ba điểm cốt lõi:

- **Không gán permission trực tiếp cho ai.** Permission (`bigquery.jobs.create`) chỉ nằm bên trong role. Bạn gán *role*, role mang theo gói permission.
- **Binding gắn vào resource, resource con thừa kế từ cha.** Gán ở project → áp lên mọi dataset, kể cả dataset tạo sau. Gán ở dataset → chỉ dataset đó. Nguyên tắc: **gán ở mức thấp nhất mà việc vẫn chạy.**
- **Member không chỉ là người:** `user:`, `serviceAccount:`, `group:`, `allUsers` (cái cuối = public, nguồn gốc của phần lớn vụ lộ dữ liệu trên object storage).

Ba loại role: **basic** (owner/editor/viewer — không dùng cho SA, owner tự sửa IAM cho chính mình được), **predefined** (dùng 95% thời gian), **custom** (chỉ khi predefined quá rộng).

Đối chiếu NestJS: role ≈ `@Roles()`, binding ≈ dòng cấu hình nói role nào áp lên route nào, service account ≈ API key của service-to-service call, user account ≈ session người dùng.

---

## 2. Hai trục quyền của BigQuery — tách rời nhau

| Trục | Role | Gán ở | Trả lời | Thiếu thì lỗi |
|---|---|---|---|---|
| Chạy job | `roles/bigquery.jobUser` | **project** | Ai được tiêu compute? | `does not have bigquery.jobs.create` |
| Chạm dữ liệu | `roles/bigquery.dataEditor` | **dataset** | Ai đọc/ghi bảng nào? | `Access Denied` trên bảng |

Vì query là **job tiêu tiền của project**, không phải thao tác lên bảng. Có full quyền trên bảng mà thiếu `jobUser` thì không chạy nổi một câu query.

> Đây là chỗ mình gán sót hôm nay: trả lời "1 binding là đủ" trong khi cần 2, ở 2 mức resource khác nhau.

---

## 3. Service account `de-pipeline@bine910.iam.gserviceaccount.com`

SA là danh tính của **máy**. Nó vừa là *principal* (gán role cho nó) vừa là *resource* (gán quyền cho người khác dùng nó) — khác user account ở điểm này.

**Binding đã gán:**

```bash
# Trục 1 — project level
gcloud projects add-iam-policy-binding bine910 \
  --member="serviceAccount:de-pipeline@bine910.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

# Trục 2 — dataset level (bq add-iam-policy-binding bị allowlist,
# phải sửa access array rồi update)
bq show --format=prettyjson bine910:olist_marts > ds.json
# thêm vào mảng access:
#   { "role": "WRITER", "userByEmail": "de-pipeline@bine910.iam.gserviceaccount.com" }
bq update --source ds.json bine910:olist_marts
```

**Key:** `~/.gcp/de-pipeline.json` — nằm **ngoài** `/mnt/c/DE/`, `chmod 600`, thư mục `chmod 700`.
Đường dẫn khai trong `.env`: `GOOGLE_APPLICATION_CREDENTIALS=/home/binh/.gcp/de-pipeline.json`

Để key ngoài repo mạnh hơn `.gitignore`: không có đường nào lọt vào git kể cả khi `git add -A`.

---

## 4. Bằng chứng least privilege

Test bằng chính SA (`gcloud auth activate-service-account`):

| Test | Dự đoán | Kết quả | Permission bị chặn |
|---|---|---|---|
| `SELECT 1 AS ok` | pass | **pass** | — (chứng minh có `jobs.create`) |
| `gcloud compute instances list` | denied | **denied** | `serviceusage.services.enable` |
| `bq mk -d bine910:should_fail` | denied | **denied** | `bigquery.datasets.create` |

Test 3 là bằng chứng quan trọng nhất: `dataEditor` trên **một** dataset không leo lên thành quyền tạo dataset mới. Nếu hôm đó gán `dataEditor` ở project cho nhanh, lệnh này đã chạy được và mình không bao giờ biết mình mở quá rộng.

---

## 5. Nếu key JSON bị lộ (vd. push nhầm lên GitHub)

Sửa lịch sử git **không cứu được gì** — bot quét secret crawl GitHub public liên tục, thời gian từ push đến khi bị lấy tính bằng giây. Key vẫn sống và vẫn dùng được sau khi file biến mất khỏi repo.

Thứ tự bắt buộc:

1. **Revoke key ngay** — bước duy nhất thật sự cứu được tình hình:
   ```bash
   gcloud iam service-accounts keys list --iam-account=<SA_EMAIL>
   gcloud iam service-accounts keys delete <KEY_ID> --iam-account=<SA_EMAIL>
   ```
2. Tạo key mới, cập nhật `.env`
3. Kiểm Cloud Logging xem key cũ đã bị dùng chưa
4. *Sau đó* mới dọn lịch sử git

**Quy tắc:** secret đã rời khỏi máy thì coi như lộ vĩnh viễn — chỉ có **revoke**, không có **xoá**.

Khác với vụ `git filter-repo` tuần 12: file CSV 325MB là dữ liệu, xoá khỏi lịch sử là xong. Secret thì không.

Key JSON nguy hiểm hơn mật khẩu Gmail: **không hết hạn, không có 2FA chặn**. Ai cầm file là trở thành SA đó.

---

## 6. Bảy cổng mỗi API call phải đi qua

Fail ở cổng nào thì dừng ở đó — lỗi luôn nói về **cổng đầu tiên bị chặn**, không phải về ý định của mình.

| # | Cổng | Câu hỏi | Lỗi điển hình |
|---|---|---|---|
| 1 | Authentication | Bạn là ai? Token còn sống? | `invalid_grant`, `Reauthentication required` |
| 2 | API enablement | Service đã bật trên project chưa? | `API [x.googleapis.com] not enabled` |
| 3 | Authorization (IAM) | Có permission trên resource này? | `PERMISSION_DENIED` + field `permission:` |
| 4 | Billing | Billing account hợp lệ? | `billing account is not open` |
| 5 | Quota / limit | Còn hạn mức? | `Quota exceeded`, `429` |
| 6 | Resource tồn tại | Bảng/bucket có thật? | `Not found: Table ...` |
| 7 | Business logic | SQL đúng cú pháp, schema khớp? | `Syntax error`, `Field not found` |

Chuyện đã xảy ra với `compute instances list`:

```
cổng 1: OK (SA đã auth)
cổng 2: compute API chưa bật → gcloud đề nghị bật, bấm y
        → lệnh bật API cũng là một API call, đi lại từ đầu:
          cổng 3: SA thiếu serviceusage.services.enable  ← DỪNG Ở ĐÂY
cổng 3 của compute.instances.list: chưa bao giờ chạy tới
```

→ Chưa hề chứng minh được SA không xem được VM, chỉ chứng minh nó không bật được API.

---

## 7. Bẫy đã gặp Day 2

- **`bq add-iam-policy-binding` → "This feature requires allowlisting"** — dataset-level IAM qua `bq` bị khoá. Đường vòng: sửa mảng `access` trong JSON rồi `bq update --source`.
- **SA trong access array dùng key `userByEmail`**, không phải `serviceAccount` — định dạng legacy của BigQuery.
- **`roles/bigquery.dataEditor` hiển thị thành `WRITER`** trong access array. Thấy `WRITER` là đúng, không phải gán nhầm.
- **`grep -A10 jobUser` đọc sai policy** — mảng `members` nằm *phía trên* dòng `role`. Dùng `--flatten` + `--filter` thay vì grep.
- **`\` nối dòng phải đứng ngay trước Enter**, không có ký tự nào sau. `de-pipeline\ --display-name=...` biến cả chuỗi thành account ID.
- **gcloud hỏi `enable and retry? (y/N)` → mặc định N có lý do.** Trên project có billing, một cú `y` vô thức có thể bật API tính tiền. Đọc trước khi gõ `y`.
- **`defaultTableExpirationMs: 5184000000` = 60 ngày** — dấu hiệu sandbox. Mọi bảng tạo trong dataset này tự hết hạn.

---

## 8. Nhớ cho Day 3+

- Day 3 sẽ gặp lại **cổng 4 (billing)**: GCS không chạy được vì billing chưa `OPEN`, không phải vì IAM. Đừng debug nhầm sang IAM.
- Khi debug: đọc field `permission:` trong lỗi, **đừng đoán từ tên lệnh**.
- Hết phiên test bằng SA thì nhớ quay về tài khoản của mình:
  ```bash
  gcloud config set account hdbinh2005@gmail.com
  ```