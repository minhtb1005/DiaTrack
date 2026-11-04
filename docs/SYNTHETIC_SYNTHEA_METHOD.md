# Áp dụng phương pháp Synthea vào dữ liệu Faker

> Demo-only. Không phải dữ liệu bệnh nhân thật. Không dùng cho chẩn đoán.
> Cách tiếp cận: học phương pháp của Synthea rồi triển khai lại bằng Python/Faker, không chạy Java. Synthea CLI vẫn chỉ nằm trong thiết kế; demo chạy `seed_synthetic_data.py` như mô tả trong `docs/SYNTHETIC_DATA.md` và `docs/SYNTHETIC_SYNTHEA_ETL_SPEC.md`.

## 1. Các nguyên tắc lấy từ Synthea

- **PADARSER**: không dùng EHR thật (privacy by construction). Số liệu công
  khai + clinical guidelines/care maps + coding dictionaries được bắn thẳng
  vào quá trình sinh.
- **Generic Module Framework (GMF)**: mỗi bệnh là một JSON state machine.
  Control states (Initial/Terminal/Guard/...) điều luồng; clinical states
  (ConditionOnset, MedicationOrder, Observation, Symptom, ...) ghi sự kiện;
  transitions (direct/distributed/conditional/...) quyết nhảy state.
- **Thời gian**: timestep mặc định 7 ngày; observations chỉ sinh khi có
  encounter/lab; conditions/meds có START/STOP.
- **Diabetes = 2 modules**: `metabolic_syndrome_disease` (tiến triển +
  biến chứng staged neuropathy/nephropathy/retinopathy theo xác suất mỗi
  timestep) + `metabolic_syndrome_care` (metformin → insulin, dialysis,
  HbA1c/glucose observations).
- **Validation kiểu JAMIA Table 2**: tune transition probabilities để
  **phân bố quần thể** khớp thực tế, không ép từng cá thể.

## 2. Ánh xạ khái niệm Synthea sang phần triển khai

| Synthea | Ta (`disease_engine.py` + `modules/diabetes_vn.json`) |
|---|---|
| GMF full taxonomy | Subset v1: 8 state kinds + 3 transition kinds (D1); unknown kind FAIL loudly |
| Timestep 7 ngày | Weekly runner (`DiseaseEngine.run`, 1 transition/tuần) |
| Distributed transitions | Weighted pick bằng seeded RNG (`random.Random`) |
| Conditional + Guards | `when: {attribute, op, value}` trên ctx (tuổi/bệnh nền/archetype) |
| Disease progression | Drift baseline tích lũy, budget ≤ ±2 mg/dL/tuần (remarks) |
| Staged complications | `ConditionOnset` võng mạc/thần kinh/thận → sidecar comorbidities |
| Medication timeline | `MedicationOrder` lifestyle → metformin → insulin → notes log |
| Encounter-driven obs | Dawn-spike giữ làm condition-gated morning rule (demo-critical) |
| Validation Table-2 | Assert phân bố ở scale seed (bands rộng ±15pp), không ép cá thể |

## 3. Ngoài phạm vi của đợt triển khai này

Phiên bản engine đầu tiên không có Java, Gradle, parser FHIR, import CSV, schema DB mới hoặc các thành phần Delay, Counter, Encounter, Procedure, CarePlan, Death, CallSubmodule và table lookup. Chỉ bổ sung khi phạm vi được mở rộng hợp lệ.

## 4. Số liệu có nguồn và giả định

**Có nguồn ngoài:**

- ĐTĐ Việt Nam ~7.3% người lớn (GHO/BYT) — bối cảnh hiệu chỉnh phenotypes.
- Mục tiêu HbA1c < 7% (QĐ BYT 5481/2020 + ADA 2024) — Assessment, không đổi.
- Toán ramp-week 100 → 114 (+14%) → 126 (+10.5%) nằm trong band detector
  10–15% (`anomaly_detector.py:118`) — đã verify bằng test recorder.

**Giả định cho demo, được ghi trong `remarks` của JSON:**

- Phenotype weights 1/3–1/3–1/3 (giữ block-thirds cho benchmark coverage).
- Drift budget ±2 mg/dL/tuần; mọi `p` distributed; staged-complication rates;
  meds escalation; guards tuổi/bệnh nền. Tất cả đều gắn
  `"remarks": {"assumption": "..."}` để grep được, không bịa thành epidemiology.

Mọi probability trong `diabetes_vn.json` đều mang `remarks.source|assumption`
(zero bare-probabilities — có shape test chặn).
