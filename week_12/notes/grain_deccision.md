# Grain của từng model — Tuần 12

> Grain = một dòng trong bảng này đại diện cho cái gì.
> Quy tắc tự đặt từ Day 4: **khai grain ra chữ + số dòng dự kiến TRƯỚC khi viết SQL**.
> Chạy xong đối chiếu — đó là bước nghiệm thu rẻ nhất.

---

## Bảng tổng hợp

| Model | Grain | Số dòng | Khớp? |
|---|---|---|---|
| `stg_olist__orders` | 1 đơn hàng | 99.441 | ✓ |
| `stg_olist__customers` | 1 customer_id | 99.441 | ✓ |
| `stg_olist__products` | 1 sản phẩm | 32.951 | ✓ |
| `stg_olist__order_items` | 1 **(order_id, order_item_id)** | 112.650 | ✓ |
| `stg_olist__order_payments` | 1 **(order_id, payment_sequential)** | 103.886 | ✓ |
| `int_order_items_enriched` | 1 dòng hàng (giữ grain của order_items) | 112.650 | — ephemeral |
| `int_order_payments_agg` | 1 đơn hàng (đã gộp) | 99.440 | — ephemeral |
| `fct_orders` | 1 đơn hàng | 99.441 | ✓ |
| `dim_customers` | 1 customer_id | 99.441 | ✓ |
| `dim_products` | 1 sản phẩm | 32.951 | ✓ |

---

## Hai bảng có khoá kép

### `order_items`: (order_id, order_item_id)

`order_item_id` là **số thứ tự dòng hàng trong một đơn** — giá trị 1, 2, 3… lặp lại ở mọi đơn.
Riêng nó không duy nhất.

Hệ quả: test `unique` chỉ nhận một cột nên phải viết singular test
`tests/assert_order_items_unique_key.sql` gom theo cả hai cột.

**Sai lầm đã mắc (Day 3):** định gộp hai cột thành một `primary_key` ngay ở staging.
Sai vì (a) gộp là mất dữ liệu — muốn JOIN sang `orders` theo `order_id` phải tách chuỗi ra lại,
(b) staging giữ nguyên cấu trúc nguồn. Nếu mart thật sự cần khoá đơn thì tạo surrogate key
ở mart, không phải ở staging.

### `order_payments`: (order_id, payment_sequential)

Một đơn có thể trả nhiều lần. **2.961 đơn** có nhiều hơn một bản ghi thanh toán
(phát hiện khi test `unique` trên `order_id` fail với 2961 vi phạm ở Day 5).

Đây chính là lý do `int_order_payments_agg` phải `group by order_id` trước khi
`fct_orders` join vào — nếu join thẳng, số dòng đã phình lên.

---

## Luật JOIN rút ra từ Day 4

**Trước khi JOIN, hỏi grain của cả hai bên:**

- Grain giống nhau → JOIN an toàn, số dòng giữ nguyên
- Grain bên phải mịn hơn → **gộp về cùng grain TRƯỚC khi JOIN**, không bao giờ join rồi mới gộp

Ví dụ cụ thể: JOIN thẳng `stg_olist__orders` với `int_order_items_enriched` theo `order_id`
sẽ cho **112.650 dòng** (số dòng hàng), không phải 99.441 (số đơn).

Điểm chết người: kết quả đó **trông vẫn hợp lý** — mỗi dòng vẫn có đủ `order_id`, `status`,
`purchased_at`. Chỉ khi `count()` hoặc `sum()` mới lộ ra. Doanh thu bị cộng trùng,
không có lỗi nào báo.

Vì thế `fct_orders` có CTE `items_agg` gộp 112.650 → 99.441 trước, rồi mới `left join`.

---

## Vì sao `fct_orders` dùng `left join`, không `inner join`

Số liệu thực tế sau khi build:

| | Số dòng |
|---|---|
| Tổng đơn | 99.441 |
| Đơn **không có dòng hàng nào** (`total_revenue` NULL) | 775 |
| Đơn **không có bản ghi thanh toán** (`total_payment_value` NULL) | 1 |

Nếu dùng `inner join`, **775 đơn biến mất khỏi fact table và không ai biết**.
Thường là đơn `unavailable` hoặc `canceled` trước khi có hàng.

**Nguyên tắc: fact giữ nguyên số dòng khi join sang dimension.**
Join làm mất dòng là tín hiệu có vấn đề, không phải cách lọc dữ liệu.
Thiếu dữ liệu thì để NULL — NULL ở đây là **thông tin**, không phải lỗi.

Hệ quả khi viết test: **không gắn `not_null`** cho `total_revenue`, `total_payment_value`,
`item_count`, `payment_count`. Phép thử trước khi gắn `not_null`: *cột này có được phép
thiếu không?* Khoá → không. Cột đến từ left join → thường có.

---

## Test `unique` là máy dò grain sai

Nếu `unique` trên khoá fact fail, 90% là **join nhân bản dòng ở tầng dưới**,
không phải dữ liệu bẩn.

Đừng dập test bằng `distinct` — đi ngược lên tìm chỗ nhân bản.

Kiểm chứng ở Day 5: cố tình `insert` một dòng trùng vào `raw.orders`
→ `unique_fct_orders_order_id` FAIL 1, trong khi 4 test khác vẫn xanh
(dòng nhân đôi không có NULL, status vẫn hợp lệ, customer_id vẫn tồn tại trong dim).
Mỗi test bắt đúng một loại lỗi — đó là lý do cần nhiều test nhỏ thay vì một test lớn.