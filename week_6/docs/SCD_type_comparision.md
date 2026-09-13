# SCD Types Comparison

## Overview

Slowly Changing Dimension (SCD) defines how a data warehouse handles
changes to dimension attributes over time.

The core question: when a dimension value changes, what happens to
the historical records that referenced the old value?

## Comparison

| Tiêu chí           | Type 0          | Type 1          | Type 2              | Type 3              |
|---------------------|-----------------|-----------------|----------------------|----------------------|
| **Tên gọi**        | Retain Original | Overwrite       | Add New Row          | Add New Column       |
| **Giữ lịch sử?**   | Không thay đổi  | Không           | Đầy đủ               | Chỉ 1 lần thay đổi  |
| **Cách xử lý**     | Không làm gì    | UPDATE trực tiếp| Expire row cũ, INSERT row mới | Thêm cột `previous_` |
| **Số row/entity**   | Luôn 1          | Luôn 1          | Tăng theo số lần đổi | Luôn 1               |
| **Cần surrogate key?** | Không bắt buộc | Không bắt buộc | Bắt buộc            | Không bắt buộc       |
| **Cột phụ cần thêm** | Không          | Không           | effective_date, expiry_date, is_current | previous_city, current_city |
| **Query current**   | Trực tiếp       | Trực tiếp       | `WHERE is_current = TRUE` | Trực tiếp (cột current_) |
| **Query tại thời điểm** | Không hỗ trợ | Không hỗ trợ   | `WHERE eff <= date AND exp >= date` | Chỉ 1 thời điểm trước |
| **Khi nào dùng**    | Giá trị không bao giờ nên đổi (ngày sinh) | Sửa lỗi, cập nhật không quan trọng (email, typo) | Thay đổi cần theo dõi lịch sử (địa chỉ, segment, trạng thái) | Hiếm dùng trong thực tế |

## SCD Type 2 — Chi tiết

### Cấu trúc bảng

```text
dim_customer
├── customer_key      PK  (surrogate, auto-increment)
├── customer_id       BK  (business key từ source)
├── customer_name
├── customer_city
├── customer_state
├── customer_zip
├── customer_segment
├── effective_date         bắt đầu có hiệu lực
├── expiry_date            hết hiệu lực (9999-12-31 = current)
└── is_current             TRUE/FALSE shortcut
```

### Ví dụ

CUST001 chuyển từ Hanoi → Ho Chi Minh City ngày 2025-07-01:

```text
customer_key | customer_id | city             | effective  | expiry     | is_current
-------------|-------------|------------------|------------|------------|----------
101          | CUST001     | Hanoi            | 2025-01-01 | 2025-06-30 | FALSE
102          | CUST001     | Ho Chi Minh City | 2025-07-01 | 9999-12-31 | TRUE
```

### Quy tắc quan trọng

1. **Không overlap:** expiry row cũ = effective row mới − 1 ngày.
2. **Không gap:** ngày liên tiếp không bỏ sót.
3. **Surrogate key bắt buộc:** cùng 1 business key có nhiều row, cần PK riêng cho mỗi version.
4. **Fact JOIN tự động đúng:** fact_sales.customer_key trỏ đến version tại thời điểm giao dịch, không cần logic date khi query.
5. **INSERT phải copy toàn bộ attribute:** row mới là version độc lập, không inherit từ row cũ.

### Khi nào dùng Type 1 vs Type 2

- Attribute thay đổi nhưng lịch sử **không quan trọng** (email, số điện thoại) → Type 1.
- Attribute thay đổi và lịch sử **ảnh hưởng đến phân tích** (thành phố, segment, cấp bậc) → Type 2.
- Cùng 1 dimension có thể mix: email dùng Type 1, city dùng Type 2.