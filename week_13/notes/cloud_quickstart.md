# Cloud Quickstart — Week 13 (T13: GCS / BigQuery / IAM / Cost)

Ngày: 2026-10-26
Máy: WSL Ubuntu, /mnt/c/DE

## 1. Quyết định đã chốt

| Mục | Giá trị | Ghi chú |
|---|---|---|
| Project ID | `bine910` | Global unique, **không đổi được** — nhúng trong mọi resource name, URL, IAM binding |
| Project name | Week 13 | Đổi thoải mái, chỉ là nhãn hiển thị |
| Location | `US` (multi-region) | ← *viết lý do + bạn đánh đổi gì khi không chọn asia-southeast1* |
| Billing | Chưa kích hoạt | Account `01E795-17CBAE-B4E007`, `OPEN: False` — VN yêu cầu prepayment |
| Track | **B** — BigQuery sandbox | Lên Track A khi billing `OPEN: True` |

### Giới hạn của Track B
- 10 GB active storage, 1 TB query/tháng
- Mọi bảng/view/partition **tự hết hạn sau 60 ngày**
- **Không dùng được GCS** → Day 3 thay bằng MinIO, Day 4 `bq load` thay cho external table

### Khi nào lên Track A
```bash
gcloud billing accounts list          # chờ OPEN: True
gcloud billing projects link bine910 --billing-account=01E795-17CBAE-B4E007
gcloud billing projects describe bine910   # phải thấy billingEnabled: true
```

## 2. Dựng lại từ máy trắng

```bash
# Cài gcloud CLI
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates gnupg curl
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install -y google-cloud-cli
gcloud version        # SDK 590.0.1, bq 2.1.41, gsutil 5.38

# Đăng nhập (WSL2 dùng chung localhost với Windows nên bản thường chạy được)
gcloud auth login
gcloud auth list

# Tạo project
gcloud projects create bine910 --name="Week 13"
gcloud config set project bine910
gcloud config list

# Bật API (BigQuery bật được không cần billing)
gcloud services enable bigquery.googleapis.com --project=bine910
bq --project_id=bine910 ls    # rỗng = chưa có dataset, không phải lỗi
```

## 3. Bẫy đã gặp

| Triệu chứng | Nguyên nhân | Cách xử |
|---|---|---|
| `INVALID_ARGUMENT: display_name contains invalid characters` | `--name` không nhận dấu gạch dưới | Dùng dấu cách: `"Week 13"` |
| `billing projects link` chạy xong không báo lỗi | ← *điền: output thật sự nói gì, và vì sao đây là bẫy* | Luôn đọc field trong output, không tin exit code |
| Console mở nhầm "My First Project" | Google tự tạo project mặc định | Kiểm project selector trước mỗi thao tác |

## 4. Bài học Day 1

- Project là đơn vị gom mọi resource + quota + IAM. Xoá project = dọn sạch, đây là nút cleanup của Day 7.
- Location của bucket và dataset phải trùng nhau, **chọn một lần không sửa được**. BigQuery từ chối thẳng job cross-location, không phải chạy chậm hơn.
- Tiền BigQuery tính theo **bytes scanned**, không theo số lần gọi API và không theo số dòng trả về. Lưu trữ và query là hai khoản tách rời.
- ← *gạch thứ 4: bài học rút ra từ dòng `billingEnabled: false`*