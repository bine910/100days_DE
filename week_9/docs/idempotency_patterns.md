# Idempotency Patterns

## Idempotency là gì

Một thao tác (hoặc cả pipeline) là **idempotent** nếu chạy nó **một lần** hay **nhiều lần với cùng input** đều cho ra **cùng một kết quả cuối cùng** trong hệ thống đích — không tạo thêm dữ liệu trùng, không làm sai lệch trạng thái dù chạy lại bao nhiêu lần.

Với ETL/ELT, idempotency thường nói về bước **load**: chạy lại job load cho cùng một khoảng dữ liệu (cùng ngày, cùng batch...) nhiều lần phải cho ra đúng một bản ghi cho mỗi khóa, không phải N bản ghi trùng nhau.

Đây là thuộc tính bắt buộc nếu muốn pipeline **retry an toàn** — job có thể chết giữa chừng (mất kết nối DB, container restart, lỗi mạng khi gọi MinIO...) và chỉ cần chạy lại đúng lệnh cũ mà không cần dọn dẹp thủ công trước.

## Hai kỹ thuật: UPSERT vs Delete-then-Insert

### 1. UPSERT (`INSERT ... ON CONFLICT DO UPDATE`)

Nạp dữ liệu bằng một câu lệnh vừa insert vừa update dựa trên khóa duy nhất (natural key hoặc primary key).

Ví dụ thực tế trong `week_9/etl_pipeline/load.py`:

```sql
INSERT INTO gold_price_daily (date, open, high, low, close, volume)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (date)
DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    volume = EXCLUDED.volume;
```

`date` là khóa duy nhất (`PRIMARY KEY`) của bảng `gold_price_daily`. Nếu ngày đó đã có dữ liệu → ghi đè bằng giá trị mới; nếu chưa có → insert mới. Chạy `python main.py --start-date 2023-01-01 --end-date 2023-12-31` bao nhiêu lần cũng chỉ có đúng một dòng cho mỗi ngày trong năm 2023.

**Ưu điểm:**
- Một statement duy nhất, atomic theo từng dòng (hoặc cả batch nếu dùng `execute_values`).
- Không có khoảng trống (window) giữa lúc xóa và lúc insert lại → dữ liệu không bao giờ "biến mất" tạm thời, an toàn nếu có process khác đang đọc bảng song song.
- Không cần biết trước phạm vi dữ liệu cũ cần xóa.

**Nhược điểm:**
- Cần có unique/primary key rõ ràng để `ON CONFLICT` match đúng dòng.
- Nếu batch mới có ít dòng hơn batch cũ trong cùng khoảng (ví dụ một ngày trước có, giờ nguồn không còn trả về ngày đó nữa), dòng cũ **không bị xóa** — dữ liệu đích có thể lệch so với nguồn.
- Load từng dòng (`for _, row in df.iterrows(): cursor.execute(...)` như trong `load.py`) chậm hơn khi dữ liệu lớn, nên thực tế hay dùng `execute_values(...)` hoặc `COPY` kết hợp `ON CONFLICT` để tăng tốc.

### 2. Delete-then-Insert

Xóa toàn bộ dữ liệu thuộc phạm vi batch (ví dụ toàn bộ dòng của khoảng ngày đang backfill) trước, rồi insert lại dữ liệu mới của batch đó — thường bọc trong một transaction.

```sql
BEGIN;
DELETE FROM gold_price_daily WHERE date BETWEEN %s AND %s;
INSERT INTO gold_price_daily (date, open, high, low, close, volume)
VALUES (%s, %s, %s, %s, %s, %s), ...;
COMMIT;
```

Áp dụng cho pipeline hiện tại: nếu backfill `--start-date 2023-01-01 --end-date 2023-12-31`, sẽ `DELETE` toàn bộ dòng có `date` trong khoảng đó trước khi insert lại dữ liệu mới lấy từ `transform()`.

**Ưu điểm:**
- Đảm bảo đích **khớp chính xác** với nguồn cho phạm vi batch, kể cả trường hợp nguồn đã bớt dòng (ví dụ dữ liệu ngày lễ bị nhà cung cấp rút lại) — dòng thừa trong đích cũng bị xóa theo.
- Không phụ thuộc vào việc có primary key hay không, chỉ cần xác định đúng điều kiện `WHERE` cho phạm vi batch.

**Nhược điểm:**
- Cần transaction bọc `DELETE` + `INSERT`, nếu không sẽ có khoảng trống bảng trống tạm thời (dữ liệu "biến mất" giữa chừng nếu có reader đọc song song không dùng cùng transaction/isolation phù hợp).
- Phải xác định đúng phạm vi `WHERE` của `DELETE` khớp chính xác với phạm vi dữ liệu sắp insert — sai phạm vi (quá rộng/quá hẹp) sẽ xóa nhầm hoặc để sót dữ liệu cũ.
- Tốn chi phí ghi (rewrite) nhiều hơn UPSERT khi phần lớn dữ liệu trong batch không đổi so với lần chạy trước.

## Vì sao quan trọng khi backfill

Backfill nghĩa là chạy lại pipeline cho một khoảng dữ liệu **trong quá khứ**, thường vì:

- Job trước đó chạy lỗi/crash giữa chừng và cần chạy lại.
- Phát hiện bug ở logic transform và cần nạp lại dữ liệu cũ với logic đã sửa.
- Nguồn dữ liệu được cập nhật/sửa lại (ví dụ nhà cung cấp XAU sửa giá đóng cửa của một ngày cũ).

Nếu bước load **không idempotent** (ví dụ dùng `INSERT` thuần, không có `ON CONFLICT` và không xóa dữ liệu cũ), thì:

- Chạy lại `python main.py --start-date 2023-06-01 --end-date 2023-06-30` hai lần sẽ tạo ra **hai bản ghi cho cùng một ngày** trong `gold_price_daily` — vi phạm giả định "mỗi ngày một dòng" mà mọi query/report phía sau đều dựa vào.
- Không thể retry an toàn: mỗi lần job chết giữa chừng, phải tự tính toán và xóa thủ công phần dữ liệu đã insert dở trước khi chạy lại, dễ sai sót và không tự động hóa được (không thể đưa vào cron/scheduler mà tin tưởng được).
- Backfill chồng lấn (chạy lại tháng 6 sau khi đã chạy nguyên quý 2) sẽ luôn gây trùng lặp.

Với idempotent load (UPSERT như trong `load.py`, hoặc delete-then-insert), backfill chỉ đơn giản là "chạy lại đúng lệnh cũ" — an toàn để tự động retry, an toàn để chạy chồng lấn phạm vi ngày, và là điều kiện tiên quyết để đưa pipeline vào orchestrator (Airflow/cron) chạy định kỳ mà không cần người can thiệp mỗi khi có lỗi.
