# Week 3 — Python cho ETL + Linux/Terminal

## Mô tả
2 script Python thực hành extract data từ API và validate data quality.

## Scripts

### python_api_extract.py
- Gọi GitHub API lấy danh sách repos của user
- Lưu kết quả ra JSON và CSV
- Có logging, error handling, config từ .env

### python_file_validate.py
- Đọc file CSV output từ script 1
- Validate: thiếu field, giá trị rỗng, sai kiểu dữ liệu, duplicate
- Custom exception, gom lỗi rồi report cuối

## Cài đặt

```bash
cd week_3
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Cấu hình

Copy `.env.example` thành `.env` và điền giá trị:

```bash
cp .env.example .env
```

## Chạy

```bash
python python_api_extract.py
python python_file_validate.py
```

## Output mẫu

```
2026-08-19 10:52:10 - INFO - Fetching https://api.github.com/users/octocat/repos
2026-08-19 10:52:11 - INFO - Thanh cong: 200
2026-08-19 10:52:11 - INFO - So record: 8
2026-08-19 10:52:11 - INFO - Saved to output.json
```