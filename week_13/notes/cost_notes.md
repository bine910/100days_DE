# Cost awareness — Week 13 Day 5

Dataset `bine910.olist_marts` (US, sandbox)
Bảng đo: `fct_orders_part` và `fct_orders_nopart` — **cùng một dữ liệu** 99.441 dòng, khác nhau duy nhất ở `PARTITION BY purchased_at`
Ngày: 2026-11-05

---

## 1. Ba chốt chặn, ba tầng khác nhau

| Chốt | Chặn gì | Biết khi nào |
|---|---|---|
| `--dry_run` | không chặn, chỉ **báo giá trước** | trước khi chạy |
| `--maximum_bytes_billed` | **huỷ query** nếu vượt ngưỡng, không tính tiền | ngay lúc chạy |
| Budget alert | gửi mail | sau khi tiền đã tiêu |

Budget alert là thứ người mới biết đầu tiên, mà lại yếu nhất. `maximum_bytes_billed` mới là chốt thật — nhưng xem mục 4, nó có giới hạn riêng.

---

## 2. Sáu phép đo — partition pruning

Tất cả là `--dry_run`, không tốn gì.

| # | Query | Bytes | So với |
|---|---|---|---|
| 1 | `nopart`, lọc 1 ngày, 1 cột | 4.176.522 | — |
| 2 | `part`, lọc 1 ngày, cột trần | **105.714** | **1/39,5 của câu 1** |
| 3 | `part`, lọc 1 ngày, `DATE(purchased_at) = ...` | **105.714** | = câu 2 (xem mục 3) |
| 4 | `part`, lọc 1 ngày, `SELECT *` | 338.982 | 3,2× câu 2 |
| 5 | `part`, không lọc, 1 cột | 3.380.994 | toàn bảng |
| 6 | `part`, lọc 7 ngày, 1 cột | 951.300 | **9×** câu 2, không phải 7× |

### Đọc bảng này

**Câu 1 → câu 2: pruning giảm 39,5 lần.** Chú ý câu 1 cũng chỉ đọc 1 cột (column pruning đã áp dụng), nên 39,5 lần này là **phần partition đóng góp thêm**, không phải tổng.

**Câu 6 ≈ 9× câu 2 cho 7 ngày, không phải 7×.** Mỗi partition có overhead metadata riêng; partition càng nhỏ, overhead chiếm tỉ trọng càng lớn. Đó là lý do không ai partition theo giờ cho bảng ít dữ liệu.

### Vì sao partition mạnh hơn column pruning

| | Giảm theo | Trần |
|---|---|---|
| Column pruning | số cột đọc | **tối đa N lần** (N = số cột) |
| Partition pruning | số ngày đọc | không có trần — bảng càng dài lịch sử càng mạnh |

Bảng 3 năm (~1095 ngày), 10 cột:
- lọc 1 ngày → 1/1095 dữ liệu
- chọn 1/10 cột → 1/10 dữ liệu
- kết hợp → **~10.000 lần**, tức khoảng cách giữa query $50 và query $0,005

Column pruning bị chặn trên bởi số cột. Partition thì không. Đó là lý do mọi fact table ở công ty đều partition theo ngày.

### Partition hoạt động thế nào

BigQuery **không** lưu bảng partition thành một khối liền — nó chia vật lý theo giá trị cột partition, mỗi khối có metadata riêng (khoảng giá trị, số dòng, kích thước).

```
fct_orders_part (PARTITION BY DATE(purchased_at))
├── __partition__2026-09-11   ← khối riêng, metadata riêng
├── __partition__2026-09-12
└── ...~55 khối
```

Khi query đến: (1) đọc metadata của mọi partition — miễn phí, (2) so `WHERE` với metadata để chọn partition cần, (3) chỉ đọc dữ liệu những partition đó. Bước 2 là **pruning** — cắt trước khi đọc.

So với index Postgres: index là **cấu trúc phụ trỏ vào dữ liệu**, dữ liệu vẫn nằm chung. Partition là **chia tách dữ liệu thật** — không cần cấu trúc phụ, chỉ cần biết file nào bỏ qua. Vì thế partition pruning không bao giờ bị optimizer "bỏ qua vì thấy không đáng".

---

## 3. Phát hiện trái với lý thuyết: `DATE()` VẪN prune được

Câu 3 và câu 2 ra **bytes bằng nhau chính xác**. Tức `WHERE DATE(purchased_at) = "2026-10-15"` vẫn được pruning đầy đủ.

Điều này **trái với quy tắc "bọc cột trong hàm là mất pruning"** đã ghi ở note Day 4. BigQuery nhận ra một số hàm trên cột partition và vẫn prune được; `DATE()` là một trong số đó.

Hai điều rút ra:

- **Quy tắc "cột đứng trần" vẫn nên theo**, vì nó an toàn với mọi engine và mọi hàm — không phải hàm nào cũng được optimizer nhận diện.
- **Nhưng đừng khẳng định hàm nào cũng phá pruning khi chưa đo.** Có `--dry_run` trong tay thì đo, đừng suy từ lý thuyết.

Lưu ý quan trọng: trên **Postgres** thì `DATE(col) = x` **vẫn mất index thật**. Hai engine, hai optimizer — không chuyển kết luận từ engine này sang engine kia.

---

## 4. Sàn 10 MB — và chỗ nó phá `maximum_bytes_billed`

Mỗi query có **sàn tối thiểu 10 MB (10.485.760 bytes)** khi tính tiền, bất kể scan bao nhiêu.

Thử đặt ngưỡng 1MB:

```bash
bq query --maximum_bytes_billed=1000000 '<query scan 105KB>'
# → Query exceeded limit for bytes billed: 1000000. 10485760 or higher required.
```

**Cả query đã tối ưu (105KB) cũng bị chặn.** Vì nó vẫn được *billed* 10MB.

→ `maximum_bytes_billed` **không đặt được dưới 10MB**, nên nó vô dụng ở quy mô nhỏ. Nó là chốt chặn cho bảng GB/TB — nơi cần chặn `SELECT *` trên bảng 2TB, không phải nơi đếm vài nghìn dòng.

Với ngưỡng hợp lệ (`--maximum_bytes_billed=10485760`) thì query prune chạy bình thường.

---

## 5. Hai kết cục trái chiều — khác nhau ở SỐ LƯỢNG query

### Thực tế tuần này (16 query, 7 ngày)

| | |
|---|---|
| processed | 10.638.689 (~10 MB) |
| **billed** | 41.943.040 (~40 MB) |
| tỉ lệ | **×3,9** |
| % free tier (1 TB) | **0,004%** |

40MB = đúng 4 × 10MB → chỉ **4 trong 16 query** thực sự bị tính tiền. 12 câu còn lại là dry-run (miễn phí) và `count(*)` (0 byte, trả lời từ metadata).

### Kịch bản dashboard

20 dashboard × 10 widget × 12 lần/giờ × 24h × 30 ngày = **1.728.000 query/tháng**

Mỗi widget scan 2MB → nhưng **billed 10MB** (sàn):

```
1.728.000 × 10MB = 17.280.000 MB ≈ 16,5 TB/tháng
```

Free tier 1TB → vượt **16 lần**, hoá đơn ~$100/tháng cho những dashboard **không ai mở lúc 3h sáng**.

### Kết luận giữ cả hai

- **Bảng nhỏ:** tối ưu cột vô nghĩa về tiền (40KB hay 120KB đều ra 10MB). Thứ đắt là **số lượng query**.
- **Bảng lớn (GB+):** sàn 10MB không còn ý nghĩa, column/partition pruning quyết định hoá đơn.

Biết mình đang ở chế độ nào quan trọng hơn thuộc lòng kỹ thuật tối ưu.

---

## 6. Câu audit tái dùng

```sql
-- Chi phí 7 ngày gần nhất
SELECT
  count(*) AS n_queries,
  SUM(total_bytes_processed) AS processed,
  SUM(total_bytes_billed)    AS billed,
  ROUND(SUM(total_bytes_billed)/POW(1024,3), 3) AS gb_billed
FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND job_type = 'QUERY';

-- Ai/query nào đốt nhiều nhất
SELECT
  user_email,
  total_bytes_billed,
  ROUND(total_bytes_billed / NULLIF(total_bytes_processed, 0), 1) AS billed_ratio,
  query
FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), MONTH)
  AND job_type = 'QUERY'
ORDER BY total_bytes_billed DESC
LIMIT 20;
```

Không cần chờ hoá đơn cuối tháng — mọi job đều ghi lại `total_bytes_billed`, `user_email`, `query`. Đây là cách team DE tìm ra ai đang đốt tiền và bằng query nào.

---

## 7. Bảng `fct_orders_part` được dựng thế nào

Vấn đề: Olist là 2016–2018, sandbox xoá partition quá 60 ngày (bài học Day 4). Giải: **nén + tịnh tiến** toàn bộ dải ngày về 55 ngày gần đây, giữ nguyên hình dạng phân bố.

```
purchased_at_mới = (hôm_nay − 55 ngày)
                 + (purchased_at − min) × (55 / số_ngày_thật)
```

770 ngày thật → 55 ngày. Ngày nào nhiều đơn vẫn nhiều đơn, chỉ co trục thời gian.

**Cảnh báo:** `delivered_customer_at` không dịch nên vẫn ở 2018 trong khi `purchased_at` ở 2026 → dữ liệu **vô nghĩa về nghiệp vụ**. Bảng này chỉ dùng đo bytes, tên có hậu tố `_part`/`_nopart` để không ai nhầm với `fct_orders` thật.

Script: `week_13/scripts/export_shifted.py`

---

## 8. Checklist mang đi làm

Trước khi chạy một query trên bảng lớn:

1. `--dry_run` trước. Luôn luôn.
2. Viết tên cột, không `SELECT *`.
3. Filter trên cột partition, để **cột đứng trần** (an toàn với mọi engine).
4. `LIMIT` **không** giảm byte nào — scan hết rồi mới cắt.
5. `count(*)` miễn phí (metadata), `count(DISTINCT col)` thì không.
6. Đặt `--maximum_bytes_billed` khi query có thể quét bảng lớn — nhớ sàn 10MB.
7. Audit định kỳ bằng `INFORMATION_SCHEMA.JOBS_BY_PROJECT`, đừng chờ hoá đơn.