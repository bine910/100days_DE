# Incremental model (dbt) vs UPSERT tự viết (tuần 9)

---

## Tuần 9 tôi đã làm gì

Trong `etl_daily`, task `load_gold_price` dùng `INSERT ... ON CONFLICT DO UPDATE`
để pipeline chạy lại không nhân dữ liệu. Tôi phải:

- tự nhớ viết UPSERT
- tự xác định cột xung đột
- tự test bằng cách chạy lại 3 lần rồi đếm dòng

## Tuần 12 dbt làm gì

```sql
{{ config(materialized='incremental', unique_key='order_id') }}

with orders as (
    select * from {{ ref('stg_olist__orders') }}
    {% if is_incremental() %}
    where purchased_at > (select max(purchased_at) from {{ this }})
    {% endif %}
),
...
```

Khai `unique_key` là xong. dbt tính dòng mới → dòng nào trùng `order_id` thì **update**,
không trùng thì **insert**. Đúng ngữ nghĩa UPSERT.

**Quên `unique_key` → dbt insert thuần → nhân đôi dữ liệu.**

---

## Hai mảnh Jinja cần hiểu

| | Nghĩa |
|---|---|
| `is_incremental()` | `true` **chỉ khi** bảng đã tồn tại VÀ không chạy với `--full-refresh` |
| `{{ this }}` | chính bảng này trong database |

Mệnh đề `where purchased_at > (select max(purchased_at) from {{ this }})` đọc là:
*"lấy mốc thời gian mới nhất tôi đã có, chỉ xử lý dữ liệu sau mốc đó"*.

Lọc đặt ở **CTE nguồn**, không đặt ở cuối — để các phép JOIN phía sau chỉ chạy trên dữ liệu mới.

---

## Lần chạy đầu luôn là FULL BUILD

Bảng chưa tồn tại dưới dạng incremental → `is_incremental()` = `false`
→ mệnh đề `where` bị bỏ qua → build toàn bộ.

Kết quả thực tế:

| Lần chạy | `[SELECT ?]` |
|---|---|
| 1 | 99.441 (full build) |
| 2 | 0 (không có đơn nào mới hơn `max(purchased_at)`) |

Sau 2 lần: `count(*)` = `count(distinct order_id)` = **99.441**. Không nhân đôi.
Đây là tính idempotent — thứ tuần 9 phải tự code.

Người mới hay hoảng khi thấy lần đầu chạy lâu rồi tưởng config không ăn.

---

## BÀI HỌC CHÍNH: incremental CHỈ THÊM, KHÔNG XOÁ

Thí nghiệm Day 6:

1. `insert into raw.orders` một đơn `test_order_001` với `purchased_at = 2030-01-15`
2. `dbt run --select fct_orders` → `[SELECT 1]` — **chỉ xử lý 1 dòng**, không phải 99.442.
   Đây là toàn bộ giá trị của incremental.
3. Đơn mới có mặt trong mart, các cột `item_count` / `total_revenue` / `total_payment_value`
   đều NULL (không có dòng hàng, không có thanh toán) — `left join` giữ nó lại.
4. `delete from raw.orders where order_id = 'test_order_001'` → chạy lại dbt
5. **Đơn đó VẪN CÒN trong `fct_orders`.** Bảng vẫn 99.442 dòng.

Lý do: mệnh đề incremental chỉ biết **thêm** dòng mới. Không có cơ chế nào bảo dbt
"dòng nào biến mất ở nguồn thì xoá khỏi đích". Incremental chảy một chiều.

**Và tệ hơn:** `max(purchased_at)` của bảng giờ là 2030-01-15. Mọi đơn thật năm 2018
sẽ không bao giờ lọt qua bộ lọc nữa. Bảng hỏng vĩnh viễn với mọi lần chạy incremental sau.

Cách duy nhất dọn:

```bash
dbt run --select fct_orders --full-refresh
```

`--full-refresh` ép `is_incremental()` trả `false` → dbt drop bảng và build lại toàn bộ.
Sau lệnh này: về đúng 99.441.

---

## So sánh với `table`

| | `table` | `incremental` |
|---|---|---|
| Mỗi lần `dbt run` | drop rồi tạo lại toàn bộ | chỉ thêm vào bảng đang có |
| Dữ liệu sai từ lần trước | bị xoá sạch, bảng mới tinh | **vẫn nằm nguyên trong đó** |
| Rác lọt vào một lần | tự biến mất lần chạy sau | **ở lại mãi** |
| Chi phí mỗi lần chạy | tính lại hết | chỉ phần mới |

**Một câu: incremental tích luỹ lỗi, table thì không.**
Đó là cái giá của tốc độ — và là lý do test trên bảng incremental quan trọng hơn hẳn.

---

## Khi nào dùng incremental

Chỉ khi **cả hai** điều kiện:

1. Bảng đủ lớn để full build thành vấn đề thật (ở đây 99k dòng build mất 1,6s — chưa cần)
2. Dữ liệu nguồn **chỉ thêm**, không sửa, không xoá

Dùng sai chỗ là đổi một chút tốc độ lấy một lớp lỗi âm thầm.

---

## Test không ngăn được dữ liệu sai vào bảng

Thứ tự thực tế của dbt:

```
dbt run  →  CREATE TABLE AS SELECT ...   (dữ liệu đã nằm trong DB)
dbt test →  SELECT ... HAVING count(*) > 1   (đọc bảng vừa ghi)
```

Test là câu SELECT đọc bảng **đã tồn tại**. Nó không chặn được thứ đã ghi,
chỉ nói "bảng này đang sai".

Khác hẳn constraint `UNIQUE` trong OLTP (NestJS): ở đó insert trùng **bị từ chối**,
dữ liệu sai không bao giờ vào được bảng.

**`dbt build` giới hạn thiệt hại:**

```
dbt run && dbt test
  run:  build HẾT mọi model  →  test sau  →  mart đã xây trên dữ liệu hỏng (2 bảng sai)

dbt build
  stg_items → test ✗ → fct_orders bị SKIP  →  chỉ 1 bảng sai,
                                              fct_orders giữ dữ liệu đúng lần trước
```

`build` không ngăn được bảng đầu tiên bị sai. Nó ngăn cái sai **lan xuống** các tầng dưới.
Từ tuần 12 dùng `dbt build` thay cho cặp `run && test`.

Với bảng incremental, sửa xong luôn phải `--full-refresh` — vì chạy lại thường
không dọn được dữ liệu cũ.