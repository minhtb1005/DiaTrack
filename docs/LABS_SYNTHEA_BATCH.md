# Dữ liệu xét nghiệm theo đợt dựa trên phương pháp Synthea

Tài liệu này mô tả cách Synthea tạo phiếu xét nghiệm đái tháo đường theo thời gian và cách ánh xạ phương pháp đó sang bộ seed Faker hiện có. Dự án không chạy Java hoặc Synthea CLI.

> Chỉ dùng cho demo. Đây không phải dữ liệu bệnh nhân thật và không được dùng để chẩn đoán. Phần triển khai dùng Python, Faker và SQLite.

## 1. Cách Synthea tạo phiếu xét nghiệm theo đợt

- **Lần khám định kỳ:** mỗi lần khám wellness, chronic-care hoặc follow-up tạo một encounter. Observation chỉ được tạo khi có encounter, thay vì hằng ngày như dữ liệu đo đường huyết tại nhà. Vì vậy phiếu xét nghiệm thưa hơn chuỗi đường huyết.
- **Observation theo LOINC:** mỗi chỉ số là một observation gồm `DATE`, `PATIENT`, `ENCOUNTER`, `CODE-LOINC`, `VALUE` và `UNITS`. Panel đái tháo đường gồm HbA1c (`4548-4`), glucose (`1558-6`), lipid (`2571-8`, `2093-3`, `18262-6`, `18263-4`), thận (`2160-0`, `33914-3`) và gan (`1920-8`, `1742-6`).
- **Dữ liệu theo thời gian:** các encounter lặp lại, chẳng hạn ba tháng một lần, tạo xu hướng HbA1c và eGFR. Conditions và medications có `START`/`STOP`, nên phiếu sau có thể phản ánh lần điều trị trước.
- **Kiểm tra phân bố:** điều chỉnh xác suất chuyển trạng thái để phân bố quần thể gần dữ liệu tham chiếu; không ép từng bệnh nhân khớp phân bố. Cách làm này giống `SYNTHETIC_SYNTHEA_METHOD.md`.

## 2. Ánh xạ sang bộ seed Faker hiện có

| Synthea | DiaTrack (`src/labs/` và seed) |
|---|---|
| Encounter định kỳ | 2–4 report cho mỗi bệnh nhân trong 90 ngày, ở các mốc 30/60/90 ngày và thêm ngày 45 khi cần đợt thứ tư; mỗi mốc lệch tối đa hai ngày |
| Observation LOINC | 10 observation cho mỗi report trong `lab_observations`: `report_id`, `loinc`, `value`, `unit`, `ref_low`, `ref_high`, `flag` |
| Xu hướng theo thời gian | `sampled_at` cách nhau để `get_history` đọc được xu hướng HbA1c, FPG và eGFR |
| `START`/`STOP` của bệnh và thuốc | Không thêm schema; dữ liệu nằm trong notes hoặc sidecar như đợt trước, còn care engine được hoãn |
| Tái lập dữ liệu | `random.Random(seed)`, `--reset` chỉ áp dụng cho `syn_patient_%`, và `--dry-run` |

Schema nằm trong `src/labs/store.py` và dùng lại mẫu của `vitals/base_tracker`:

- `lab_reports(report_id, user_id, sampled_at, facility, visit_no)`
- `lab_observations(report_id, loinc, name, value, unit, ref_low, ref_high, flag)`

DB riêng là `metadata/labs.db`, cấu hình qua `LAB_DB_PATH` trong `src/shared/config.py`. Dữ liệu không được ghi chung vào `glucose_logs.db` và không thay đổi episodic memory, glucose hoặc B4.

## 3. Nguồn tham chiếu và điểm chưa rõ về QĐ3312

- Nguồn tham chiếu được ghi là BYT QĐ5481/2020, thay QĐ3319/2017, cùng mục tiêu HbA1c dưới 7% trong BYT QĐ5481 và ADA 2024. Các khoảng tham chiếu nằm trong `src/labs/lab_thresholds.py`.
- Corpus `data/raw/pdfs/byt/` chỉ có QĐ3319, QĐ5481 và QĐ3192 về tăng huyết áp; không có QĐ3312. Có khả năng số QĐ3312 được ghi nhầm thành QĐ3319, nhưng cần người dùng xác nhận trước khi khóa ngưỡng B2/B3.
- Không tự tạo nguồn hoặc ngưỡng cho QĐ3312. Ví dụ panic chỉ dùng giá trị có trong panel, như HbA1c trên 12%, glucose đói trên 300 mg/dL hoặc eGFR dưới 15; không dùng kali hoặc natri.
