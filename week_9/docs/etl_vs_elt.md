# ETL vs ELT

## ETL là gì

**ETL = Extract → Transform → Load.** Dữ liệu được biến đổi (làm sạch, lọc, chuẩn hóa kiểu dữ liệu...) **trước khi** nạp vào hệ thống đích. Transform diễn ra ở một engine trung gian (script Python, Spark job...), bên ngoài kho dữ liệu đích.

```
Nguồn dữ liệu → Extract → Transform (engine trung gian) → Load → Database/Warehouse đích
```

Đặc điểm:

- Dữ liệu ghi vào đích **đã sạch/đúng schema đích**, đích không cần chứa bản raw.
- Logic transform nằm trong code (Python/Spark/...), không phải trong SQL của warehouse.
- Compute để transform tách rời khỏi database đích → không tốn tài nguyên của DB đích, nhưng cần hạ tầng riêng để chạy transform (server, Spark cluster...).
- Muốn đổi logic transform phải sửa code và chạy lại pipeline, không chỉ sửa một câu SQL.

### Ví dụ trong repo này

Pipeline ở `week_9/etl_pipeline/` là một ví dụ ETL kinh điển:

1. `extract.py` — đọc CSV giá vàng (`XAU_1d_data.csv`) từ local hoặc từ MinIO.
2. `transform.py` — parse cột `Date` sang datetime, lọc theo khoảng ngày *trước khi* dữ liệu chạm tới Postgres.
3. `load.py` — chỉ nạp dữ liệu **đã transform xong** vào bảng `gold_price_daily` bằng UPSERT.

Transform (bước 2) chạy hoàn toàn trong Python bằng `pandas`, ở ngoài PostgreSQL. PostgreSQL chỉ nhận dữ liệu thành phẩm, không biết gì về dữ liệu thô ban đầu.

## ELT là gì

**ELT = Extract → Load → Transform.** Dữ liệu thô được nạp thẳng vào hệ thống đích trước, transform diễn ra **sau đó, ngay bên trong** hệ thống đích (thường bằng SQL/dbt chạy trên warehouse).

```
Nguồn dữ liệu → Extract → Load (raw) → Warehouse đích → Transform (SQL/dbt chạy trong warehouse)
```

Đặc điểm:

- Đích lưu cả **raw layer** (dữ liệu thô, chưa xử lý) lẫn các layer đã transform (staging/mart...) — kiến trúc "bronze → silver → gold".
- Tận dụng compute mạnh sẵn có của warehouse (BigQuery, Snowflake, Redshift...) để transform bằng SQL, không cần hạ tầng transform riêng.
- Giữ được bản raw gốc trong warehouse → dễ transform lại từ đầu khi logic nghiệp vụ thay đổi, không cần extract lại từ nguồn.
- Transform thường được quản lý bằng công cụ như dbt, version hóa dưới dạng SQL model.

### Ví dụ trong repo này

`upload_to_minio.py` chính là bước "L" của một luồng ELT: đẩy CSV **thô, chưa transform** lên MinIO vào `gold-price/bronze/<ngày>/XAU_1d_data.csv` — MinIO đóng vai trò raw/bronze layer. Nếu sau này viết thêm bước transform chạy trực tiếp trên dữ liệu đã nằm trong MinIO/warehouse (ví dụ bằng SQL trên một query engine đọc thẳng từ MinIO) thay vì transform bằng `pandas` trước khi load, đó sẽ là mô hình ELT.

Hiện tại pipeline chính (`main.py`) vẫn đọc raw từ MinIO rồi transform bằng `pandas` *trước khi* load vào Postgres — nên về bản chất đây vẫn là ETL, MinIO chỉ đóng vai trò lưu trữ raw trung gian chứ transform không chạy "bên trong" nó.

## Khi nào chọn cái nào

| Tiêu chí | Chọn ETL | Chọn ELT |
|---|---|---|
| Kích thước dữ liệu | Nhỏ/vừa, transform trên 1 máy/script là đủ | Lớn, cần compute song song của warehouse |
| Hạ tầng đích | DB đích compute yếu (OLTP như Postgres cho app) | Warehouse mạnh, trả tiền theo compute (BigQuery, Snowflake) |
| Yêu cầu dữ liệu thô | Không cần giữ raw, chỉ cần dữ liệu sạch | Cần audit trail, cần transform lại khi logic đổi |
| Đội ngũ | Quen viết Python/Spark | Quen viết SQL, dùng dbt |
| Độ trễ | Cần dữ liệu sẵn sàng ngay khi vào đích (đã sạch) | Chấp nhận có raw trước, sạch sau theo lịch/on-demand |
| Chi phí lưu trữ | Tối ưu, chỉ lưu bản cần thiết | Tốn thêm dung lượng lưu cả raw + các layer transform |

Quy tắc chung: DB đích là **hệ vận hành (OLTP)**, dữ liệu nhỏ, transform logic đơn giản → **ETL** (như pipeline giá vàng trong repo, đích là Postgres phục vụ truy vấn ứng dụng). DB đích là **data warehouse/lakehouse**, dữ liệu lớn, cần giữ raw để tái xử lý nhiều lần → **ELT**.
