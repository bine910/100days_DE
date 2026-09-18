# Medallion Architecture — Ghi chú tuần 8

## 1. Tổng quan

Medallion Architecture là cách tổ chức data trong Data Lake thành **3 tầng chất lượng tăng dần**:

```
Source (API, CSV, DB)
       ↓
   ┌────────┐
   │ BRONZE │  Raw — data nguyên bản, không sửa gì
   └────┬───┘
        ↓
   ┌────────┐
   │ SILVER │  Cleaned — đã clean, đúng type, bỏ duplicate
   └────┬───┘
        ↓
   ┌────────┐
   │  GOLD  │  Aggregated — sẵn sàng cho dashboard/BI
   └────────┘
```

---

## 2. Chi tiết từng tầng

### Bronze — "Cứ lưu đã, đừng động vào"

**Giải quyết vấn đề gì?**
- Giữ nguyên bản gốc data từ source
- Khi transform sai ở Silver/Gold → quay lại Bronze chạy lại
- Khi source sập/đổi format → vẫn còn data gốc
- Bằng chứng cho compliance/audit

**Nguyên tắc:**
- **KHÔNG sửa gì cả** — lưu y chang response API, CSV gốc
- Partition theo ngày để dễ tìm và backfill
- Format: giữ nguyên format gốc (JSON thì lưu JSON, CSV thì lưu CSV)

**Cấu trúc:**
```
bronze/
  orders/
    2024-01-15/
      raw_response.json     ← y chang API trả về
    2024-01-16/
      raw_response.json
  products/
    2024-01-15/
      products_export.csv   ← y chang file đối tác gửi
```

**Tại sao Bronze không được sửa data?**
- Nếu sửa Bronze → mất bản gốc → transform sai thì không có gì để chạy lại
- Phải gọi lại API → API có rate limit, data có thể đã thay đổi
- Mất khả năng **reproducibility** — không thể tái tạo kết quả cũ
- Mất bằng chứng audit — không chứng minh được data gốc trông thế nào

---

### Silver — "Clean và chuẩn hóa"

**Giải quyết vấn đề gì?**
- Data từ Bronze thường có lỗi: nested JSON, sai type, null, duplicate
- Silver xử lý tất cả để data **sạch, có schema rõ ràng, query được**

**Các bước xử lý điển hình:**

| Vấn đề ở Bronze | Xử lý ở Silver |
|-----------------|----------------|
| JSON lồng nhau (`customer.name`) | **Flatten** → cột `customer_name` |
| `price` là string `"150000"` | **Cast type** → integer `150000` |
| `address` là `null` | **Handle null** → giữ null hoặc default |
| Order xuất hiện 2 lần | **Deduplicate** → giữ 1 bản |
| Timezone khác nhau | **Chuẩn hóa** → UTC hoặc +07:00 |

**Ví dụ — trước và sau:**

Bronze (raw JSON):
```json
{
  "id": "ORD-001",
  "customer": {"name": "Nguyễn Văn A", "address": null},
  "items": [{"product": "Áo thun", "qty": 2, "price": "150000"}],
  "total": "650000",
  "created_at": "2024-01-15T08:30:00+07:00"
}
```

Silver (cleaned Parquet):

| order_id | customer_name | product | qty | price | total | created_at |
|----------|--------------|---------|-----|-------|-------|------------|
| ORD-001 | Nguyễn Văn A | Áo thun | 2 | 150000 | 650000 | 2024-01-15 |

**Tại sao Silver lưu Parquet thay vì JSON?**

| Tiêu chí | JSON | Parquet |
|----------|------|---------|
| Cách lưu | Row-based (lưu từng object) | **Columnar** (lưu từng cột) |
| Kích thước | Lớn (key lặp lại mỗi dòng) | **Nhỏ hơn 5-10x** (compress tốt) |
| Đọc 1 cột | Phải parse toàn bộ file | **Chỉ đọc cột cần** → nhanh |
| Schema | Không enforce | **Có schema embedded** → biết type |
| Analytics | Chậm | **Nhanh** — OLAP engine tối ưu cho columnar |

Parquet = format chuẩn cho analytics pipeline. JSON chỉ phù hợp cho Bronze (giữ raw).

**Cấu trúc:**
```
silver/
  orders/
    2024-01-15/
      orders_cleaned.parquet
    2024-01-16/
      orders_cleaned.parquet
  products/
    2024-01-15/
      products_cleaned.parquet
```

---

### Gold — "Tổng hợp cho business"

**Giải quyết vấn đề gì?**
- Data Silver sạch nhưng chưa trả lời câu hỏi business
- Gold aggregate theo nhu cầu cụ thể: doanh thu theo ngày, top sản phẩm, customer segments

**Ví dụ transform Silver → Gold:**
```sql
-- Từ Silver orders → Gold daily_revenue
SELECT 
    created_at AS date,
    product,
    SUM(qty * price) AS revenue,
    SUM(qty) AS units_sold
FROM silver_orders
GROUP BY date, product
```

**Output thường là:**
- Parquet file trong Data Lake, hoặc
- Bảng trong PostgreSQL/BigQuery (mart tables)
- BI tool (Metabase) kết nối vào Gold để tạo dashboard

**Cấu trúc:**
```
gold/
  daily_revenue/
    2024-01-15/
      daily_revenue.parquet
  top_products/
    2024-01/
      top_products_monthly.parquet
```

---

## 3. Tổng kết — Mỗi tầng 1 nhiệm vụ

| Tầng | Input | Xử lý | Output | Ai dùng |
|------|-------|--------|--------|---------|
| **Bronze** | API/CSV/DB | Không sửa gì | Raw file gốc | DE debug, compliance |
| **Silver** | Bronze files | Clean, flatten, dedup, cast type | Parquet sạch | Data Science, DE |
| **Gold** | Silver files | Aggregate, join dimensions | Mart tables | BI, Analyst, Dashboard |

## 4. Lợi ích chính

1. **Reproducibility** — Bronze không đổi → transform sai thì chạy lại từ Bronze
2. **Debuggability** — Dashboard sai → kiểm tra Gold → Silver → Bronze, tầng nào sai fix tầng đó
3. **Idempotency** — Mỗi tầng là 1 bước transform rõ ràng, chạy lại không duplicate
4. **Flexibility** — Nhiều team dùng cùng Bronze/Silver cho mục đích khác nhau

## 5. Data flow tổng thể

```
API/CSV/DB (Source)
     ↓ Extract (Python requests, psycopg2)
Bronze (MinIO: raw/)
     ↓ Transform (Python pandas: flatten, clean, dedup)
Silver (MinIO: cleaned/ — Parquet format)
     ↓ Aggregate (dbt hoặc Python: SUM, GROUP BY)
Gold (MinIO: aggregated/ hoặc PostgreSQL mart tables)
     ↓ Serve
Dashboard (Metabase, Looker)
```