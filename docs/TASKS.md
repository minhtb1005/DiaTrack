# TASKS — DiaTrack týp 2

> Cập nhật tác vụ 5: 30/10/2026 08:51 +07, `main` tại `4130934d586535782248c21f5d30049840acaeff` với diff tác vụ 5 chưa commit. Kiểm tra lại trên code này: backend 11 pass, TypeScript exit 0, frontend build exit 0, previsit Playwright 4 pass. Bằng chứng các tác vụ 1–4 bên dưới là lịch sử trên snapshot cũ.

> Bằng chứng triển khai cập nhật 29/10/2026, khoảng 21:12 Asia/Saigon, `main` tại `99da3ca4232273259be00070649304f9e778c41d`, working tree chưa commit. Diff hiện hành: `git diff` của các file tác vụ 1–4 ghi bên dưới và file mới `tests/test_scope_guard.py`; log ở `test-results/` (local). Các thay đổi sau thời điểm kiểm thử cần chạy lại kiểm tra liên quan.

> Kế hoạch 29/10/2026, trên working tree chưa commit của main 99da3ca. Trạng thái dựa trên code/test đã đọc; `partial` không khẳng định test hiện hành pass. Người dùng đã xác nhận `docs/project_requirements.json` là nguồn phạm vi hiện hành gồm 6 project.

Ngưỡng và câu từ chối dùng đúng `scope_rules` trong `docs/project_requirements.json`; không tự đặt mục tiêu lâm sàng. Lệnh chạy trong PowerShell từ repo root, bằng Python `.venv`; test dự kiến phải được tạo ở phiên triển khai. Mỗi test API dùng DB/index cô lập như `tests/conftest.py`.

## Tác vụ 1: Nhật ký đường huyết và phân quyền (Project 264, Cơ bản)
- Trạng thái: done
- Hiện trạng: src/diabetes/glucose_tracker.py, src/diabetes/router.py; tests/test_glucose_tracker.py, tests/test_api_diabetes.py; đã kiểm chứng giá trị 110 mg/dL, quyền truy cập, dữ liệu sai/thiếu và thông báo không suy ra chẩn đoán.
- Việc cần làm: Hoàn thiện và kiểm chứng nhật ký đường huyết và phân quyền.
- Phụ thuộc: không
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_glucose_tracker.py -q --basetemp=test-results/tmp-task-1 -o cache_dir=test-results/pytest-cache` → 20 pass, 0 fail, exit 0; `test-results/task-1-acceptance.log`.
  - [x] Test chức năng: `tests/test_api_diabetes.py::TestDiabetesAPI::test_glucose_110_roundtrip_and_ownership` nhập 110 mg/dL lúc đói; API trả đúng người, thời điểm, giá trị (đơn vị hợp đồng API là mg/dL) và đọc lại được; 1 pass, 12 deselected, `test-results/task-1-api-final.log`.
  - [x] Test an toàn: Cùng test API xác nhận người khác bị 403, giá trị thiếu/sai bị 422; test `test_single_reading_message_does_not_diagnose` xác nhận không suy ra chẩn đoán từ một chỉ số. Playwright `tracker.spec.ts` hiện 8 case pass theo output nhưng tiến trình không tự thoát, đã ngắt; chưa tính là suite pass sạch.

## Tác vụ 2: Ngưỡng nguy hiểm và cảnh báo (Project 264, Cơ bản)
- Trạng thái: done
- Hiện trạng: src/diabetes/anomaly_detector.py, src/diabetes/glucose_tracker.py, src/diabetes/router.py, frontend/app/tracker/page.tsx; tests/test_anomaly_detector.py, tests/test_api_diabetes.py, frontend/e2e/tracker.spec.ts; đã tách cảnh báo >250 với khẩn ≥300 và kiểm chứng UI.
- Việc cần làm: Hoàn thiện và kiểm chứng ngưỡng nguy hiểm và cảnh báo.
- Phụ thuộc: 1
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_anomaly_detector.py -q --basetemp=test-results/tmp-task-2 -o cache_dir=test-results/pytest-cache` → 19 pass, 0 fail, exit 0; `test-results/task-2-acceptance.log`.
  - [x] Test chức năng: API `-k glucose_urgent_boundaries` → 1 pass, 13 deselected, exit 0; 69 và 300 báo khẩn, 110 không khẩn, 280 chỉ báo liên hệ bác sĩ; `test-results/task-2-api.log`. UI Playwright hai ca 280/300 → 2 pass, exit 0 khi dùng máy chủ frontend đã chạy sẵn.
  - [x] Test an toàn: Thông báo <70 và ≥300 yêu cầu liên hệ cơ sở y tế ngay; mọi spike nhắc không tự đổi liều thuốc/insulin. Test các biên 69/70/250/251/299/300 lấy từ `scope_rules`; `npx tsc --noEmit` exit 0. Giới hạn: chưa chạy toàn bộ API/RAG; Playwright cần frontend chạy sẵn để tiến trình kết thúc sạch trên máy này.

## Tác vụ 3: Xu hướng, nhắc đo/tái khám và hướng dẫn có nguồn (Project 264, Cơ bản)
- Trạng thái: done
- Hiện trạng: src/diabetes/glucose_tracker.py, src/diabetes/scope_guard.py, frontend/app/tracker/page.tsx; tests/test_glucose_tracker.py, tests/test_scope_guard.py, tests/test_api_diabetes.py, tests/test_demo_scenarios.py, frontend/e2e/tracker.spec.ts; xu hướng, nhắc việc trong trang, nguồn và câu từ chối cố định đã kiểm chứng.
- Việc cần làm: Hoàn thiện và kiểm chứng xu hướng, nhắc đo/tái khám và hướng dẫn có nguồn.
- Phụ thuộc: 1, 2
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_glucose_tracker.py -q --basetemp=test-results/tmp-task-3 -o cache_dir=test-results/pytest-cache` → 20 pass, 0 fail, exit 0; `test-results/task-3-acceptance.log`.
  - [x] Test chức năng: Playwright `tracker.spec.ts -g "multiple days|explain trend|due reminders"` → 3 pass, exit 0; hai ngày đo hiện trong tóm tắt/log gốc, lịch đo và tái khám đến hạn hiện khi mở trang, tồn tại sau tải lại và xóa được. `npm run build` exit 0, log `test-results/task-3-build.log`; `npx tsc --noEmit` exit 0.
  - [x] Test an toàn: Diễn giải AI không hiển thị khi thiếu metadata nguồn; có nguồn thì hiện tên tài liệu/trang và link về log. `tests/test_scope_guard.py` → 2 pass, API ngoài phạm vi → 1 pass ở `test-results/task-3-scope.log` và 1 pass ở `test-results/task-3-demo.log`, đúng câu cố định `scope_rules`. `git diff --check` exit 0. Giới hạn: lịch nhắc lưu trên thiết bị, chỉ hiện khi trang mở; test UI dùng mock API; không thay mục tiêu lâm sàng do bác sĩ đặt.

## Tác vụ 4: Dashboard bác sĩ và duyệt lời khuyên (Project 264, Nâng cao)
- Trạng thái: done
- Hiện trạng: src/triage/router.py::list_doctor_patients, src/chat/router.py, src/chat/rag_pipeline.py, src/chat/schemas.py, src/reviews/router.py; frontend/app/expert/patients/page.tsx, frontend/app/expert/queue/page.tsx, frontend/app/tracker/page.tsx; tests/test_doctor_patients.py, tests/test_auth_hilt.py, frontend/e2e/overview.spec.ts, frontend/e2e/tracker.spec.ts. Dashboard phân mức theo ngưỡng; diễn giải cá nhân đi qua bác sĩ duyệt.
- Việc cần làm: Hoàn thiện và kiểm chứng dashboard bác sĩ và duyệt lời khuyên.
- Phụ thuộc: 2, 3
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_doctor_patients.py -q --basetemp=test-results/tmp-task-4 -o cache_dir=test-results/pytest-cache` → 7 pass, 0 fail, exit 0; `test-results/task-4-acceptance.log`.
  - [x] Test chức năng: Bác sĩ thấy nhiều bệnh nhân, 300 mg/dL ở mức critical, 280 mg/dL ở watch; yêu cầu diễn giải từ tracker buộc `require_doctor_review`, tạo hàng đợi bác sĩ và chỉ hiện nội dung sau quyết định duyệt. Backend `tests/test_doctor_patients.py tests/test_auth_hilt.py` → 14 pass, log `test-results/task-4-final.log`; UI dashboard/tracker → 2 pass, exit 0; `npm run build` exit 0, `test-results/task-4-build.log`.
  - [x] Test an toàn: API bệnh nhân không trả bản nháp pending; chỉ bác sĩ/admin được duyệt diễn giải theo workflow; hàng đợi lỗi trả 503 và không lộ bản nháp; câu trả lời cần duyệt không ghi cache/bộ nhớ trước duyệt. `tests/test_triage.py` → 27 pass, `test-results/task-4-triage.log`, red-flag vẫn cảnh báo ngay. Không có đường tự đổi mục tiêu/thuốc trong tác vụ này; `npx tsc --noEmit` và `git diff --check` exit 0. Giới hạn: UI dùng mock API; chưa chạy full RAG/benchmark.

## Tác vụ 5: Dữ liệu thiếu, dự báo và báo cáo tái khám (Project 264, Nâng cao)
- Trạng thái: done
- Hiện trạng: src/diabetes/followup_report.py, src/diabetes/soap_summary.py, src/diabetes/schemas.py, src/diabetes/router.py và frontend/components/PrevisitView.tsx; tests/test_264_followup.py, tests/test_soap_summary.py, frontend/e2e/previsit.spec.ts. Báo cáo liệt kê ngày chưa có bản ghi, xu hướng mô tả có nguồn log và giới hạn; API thật trả trường followup.
- Việc cần làm: Hoàn thiện và kiểm chứng dữ liệu thiếu, dự báo và báo cáo tái khám.
- Phụ thuộc: 3
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_264_followup.py tests/test_soap_summary.py -q --basetemp=test-results/tmp-task-5-current -o cache_dir=test-results/pytest-cache` → 11 pass, 0 fail, 0 skip, exit 0 (30/10/2026 ~08:50 +07, main 4130934 và diff task 5 chưa commit); có một cảnh báo không ghi được pytest cache trong `test-results`.
  - [x] Test chức năng: ngày không có bản ghi được liệt kê, ngày đo tính theo giờ Việt Nam, xu hướng từ ba ngày liên tiếp có `basis_log_ids`; SOAP JSON API trả `followup` và Markdown có link log. `npx playwright test previsit.spec.ts --workers=1 --reporter=list` → 4 pass, exit 0; `npx tsc --noEmit` và `npm run build` exit 0 (30/10/2026 ~08:51 +07).
  - [x] Test an toàn: không điền giá trị cho ngày thiếu; khi thiếu dữ liệu, xu hướng trả `insufficient_data`; báo cáo không suy HbA1c/không tuyên bố đạt mục tiêu từ đường huyết tự đo, Plan để trống cho bác sĩ. `git diff --check` exit 0. Giới hạn: xu hướng chỉ là mô tả chiều từ dữ liệu có sẵn, không dự báo số đo hoặc gửi thông báo ngoài app; UI test dùng mock API; chưa chạy full RAG/benchmark.

## Tác vụ 6: Hỏi triệu chứng có cấu trúc và phân mức (Project 258-triage, Cơ bản)
- Trạng thái: done
- Hiện trạng: `src/triage/structured_assessment.py`, `src/triage/router.py`, `src/triage/schemas.py`, `tests/test_triage.py`; API `structured=true` hỏi số đo/thời điểm thiếu, phân mức đề xuất và giữ hướng xử trí thường chờ duyệt. Nguồn là protocol mô phỏng từ `docs/project_requirements.json`, chưa phải guideline lâm sàng đã kiểm chứng.
- Việc cần làm: Hoàn thiện và kiểm chứng hỏi triệu chứng có cấu trúc và phân mức.
- Phụ thuộc: 1, 2
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_triage.py -q --basetemp=test-results/tmp-task-6-final -o cache_dir=test-results/pytest-cache` → 29 pass, 0 fail, 0 skip, exit 0 (30/10/2026 ~10:33 +07; main 20fec547 + diff tác vụ 6). Một cảnh báo pytest cache không ghi được.
  - [x] Test chức năng: Mô tả triệu chứng + đường huyết gần nhất tạo câu hỏi cho số đo/thời điểm thiếu, sau đó đề xuất `routine|soon|emergency`; `tests/test_triage.py::TestEndpoint::test_structured_questions_and_review_only_proposal`.
  - [x] Test an toàn: Đề xuất ghi rõ không phải chẩn đoán; trường hợp thường không trả lịch/hướng xử trí trước duyệt; nguồn protocol mô phỏng và ngưỡng trong `docs/project_requirements.json`. Glucose 69/300 cảnh báo 115 ngay cả khi thiếu triệu chứng. Giới hạn: chưa có hàng đợi duyệt thật (tác vụ 8), chưa benchmark chất lượng phân mức với gold set; UI chưa dùng `structured=true`.

## Tác vụ 7: Bốn nhóm red-flag và từ chối ngoài phạm vi (Project 258-triage, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/triage/red_flag.py, src/diabetes/scope_guard.py; tests/test_triage.py; cần xác minh tích hợp UI
- Việc cần làm: Hoàn thiện và kiểm chứng bốn nhóm red-flag và từ chối ngoài phạm vi.
- Phụ thuộc: 2, 6
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_triage.py -q --basetemp=test-results/tmp-task-7 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Có dấu/không dấu cho hạ đường huyết nặng, nghi DKA, bàn chân, tim/đột quỵ đều khẩn; câu bình thường không báo nhầm.
  - [ ] Test an toàn: Red-flag luôn gọi 115/đến cơ sở y tế; ngoài phạm vi trả đúng scope_rules.out_of_scope_reply; không chẩn đoán.

## Tác vụ 8: Hàng đợi điều dưỡng duyệt/điều chỉnh (Project 258-triage, Nâng cao)
- Trạng thái: partial
- Hiện trạng: src/triage/triage_events.py, src/triage/router.py, frontend/app/admin/triage/page.tsx; thiếu xác nhận vai trò điều dưỡng/realtime
- Việc cần làm: Hoàn thiện và kiểm chứng hàng đợi điều dưỡng duyệt/điều chỉnh.
- Phụ thuộc: 6, 7
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_triage_monitor.py -q --basetemp=test-results/tmp-task-8 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Ca không khẩn vào hàng đợi, người có quyền duyệt/sửa rồi mới thông báo.
  - [ ] Test an toàn: Không trì hoãn red-flag; người trái quyền không duyệt; lưu dấu vết thay đổi.

## Tác vụ 9: Phiếu bàn giao và giải thích có nguồn (Project 258-triage, Nâng cao)
- Trạng thái: partial
- Hiện trạng: src/triage/triage_events.py, src/shared/memory; thiếu phiếu phiên đầy đủ và citation kiểm chứng
- Việc cần làm: Hoàn thiện và kiểm chứng phiếu bàn giao và giải thích có nguồn.
- Phụ thuộc: 6, 8
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_triage_handoff.py -q --basetemp=test-results/tmp-task-9 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Phiếu gồm triệu chứng, chỉ số gần nhất, dữ kiện thiếu, lý do mức ưu tiên và liên kết nguồn.
  - [ ] Test an toàn: Không bịa triệu chứng/chỉ số; ẩn PII người không có quyền; không chẩn đoán.

## Tác vụ 10: Kiểm toán và đối chiếu với điều dưỡng (Project 258-triage, Nâng cao)
- Trạng thái: partial
- Hiện trạng: src/triage/triage_events.py, data/evaluation/bench_triage.json; thiếu metric đối chiếu quyết định người duyệt
- Việc cần làm: Hoàn thiện và kiểm chứng kiểm toán và đối chiếu với điều dưỡng.
- Phụ thuộc: 8, 9
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_triage_audit.py -q --basetemp=test-results/tmp-task-10 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Log giữ đề xuất, chỉnh sửa, người duyệt, thời gian; báo cáo tỷ lệ sai khác theo bộ gold.
  - [ ] Test an toàn: Red-flag sai không bị che bởi metric chung; không lộ PII.

## Tác vụ 11: Bác sĩ tạo, duyệt và dừng phác đồ (Project 260, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/medications/router.py, tests/test_medications.py; code chưa commit, cần kiểm lại tích hợp UI và audit thay đổi
- Việc cần làm: Hoàn thiện và kiểm chứng bác sĩ tạo, duyệt và dừng phác đồ.
- Phụ thuộc: 1
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_medications.py -q --basetemp=test-results/tmp-task-11 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Bác sĩ tạo nháp, duyệt; bệnh nhân chỉ thấy lịch duyệt; bác sĩ dừng có lý do.
  - [ ] Test an toàn: Bệnh nhân/AI không tạo, đổi, ngưng liều; bác sĩ khác không duyệt; giữ lịch sử.

## Tác vụ 12: Lịch nhắc và xác nhận đã dùng/bỏ liều (Project 260, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/medications/router.py, frontend/app/medications/page.tsx; tests/test_medications.py; chưa có nhắc ngoài trang và hội thoại
- Việc cần làm: Hoàn thiện và kiểm chứng lịch nhắc và xác nhận đã dùng/bỏ liều.
- Phụ thuộc: 11
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_medications.py -q --basetemp=test-results/tmp-task-12 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Liều đến hạn theo giờ/bữa ăn đã duyệt; xác nhận một lần, dashboard cập nhật.
  - [ ] Test an toàn: Không xác nhận tương lai/trùng; bỏ liều nhắc hỏi bác sĩ, không uống gấp đôi.

## Tác vụ 13: Tuân thủ và đối chiếu đường huyết (Project 260, Nâng cao)
- Trạng thái: partial
- Hiện trạng: src/medications/router.py có tỉ lệ, chưa có chuỗi bỏ liều/đối chiếu bác sĩ
- Việc cần làm: Hoàn thiện và kiểm chứng tuân thủ và đối chiếu đường huyết.
- Phụ thuộc: 1, 12
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_medication_adherence.py -q --basetemp=test-results/tmp-task-13 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Bác sĩ thấy tỉ lệ, chuỗi bỏ liều và biểu đồ log cùng kỳ.
  - [ ] Test an toàn: Không suy ra hiệu quả thuốc hay đổi liều từ tương quan; dữ liệu chỉ người có quyền xem.

## Tác vụ 14: Báo tác dụng phụ, nhắc lại, báo cáo và duyệt đổi lịch (Project 260, Nâng cao)
- Trạng thái: todo
- Hiện trạng: src/medications/router.py chưa có luồng tác dụng phụ/retry/phiên bản lịch
- Việc cần làm: Hoàn thiện và kiểm chứng báo tác dụng phụ, nhắc lại, báo cáo và duyệt đổi lịch.
- Phụ thuộc: 11, 12
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_medication_escalation.py -q --basetemp=test-results/tmp-task-14 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Báo triệu chứng nặng tạo cảnh báo; không phản hồi tạo retry giới hạn; đổi lịch có bác sĩ duyệt và báo cáo.
  - [ ] Test an toàn: Hạ đường huyết nặng luôn escalate; không tự đổi/ngưng thuốc; báo người thân chỉ khi có đồng ý/phân quyền.

## Tác vụ 15: Nhập transcript và soạn SOAP có mục thiếu (Project 262, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/diabetes/soap_summary.py, router.py, tests/test_soap_summary.py: SOAP từ logs; chưa nhận transcript/đánh dấu thiếu có cấu trúc
- Việc cần làm: Hoàn thiện và kiểm chứng nhập transcript và soạn soap có mục thiếu.
- Phụ thuộc: 1
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_soap_summary.py -q --basetemp=test-results/tmp-task-15 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Transcript + log tạo nháp S/O/A, trường không có ghi “chưa ghi nhận”.
  - [ ] Test an toàn: Không tự chẩn đoán; Plan trống; mỗi nhận định liên kết transcript/log gốc.

## Tác vụ 16: Bác sĩ sửa, ký duyệt rồi lưu (Project 262, Cơ bản)
- Trạng thái: todo
- Hiện trạng: src/diabetes/router.py chỉ generate/markdown; chưa có editor + trạng thái duyệt
- Việc cần làm: Hoàn thiện và kiểm chứng bác sĩ sửa, ký duyệt rồi lưu.
- Phụ thuộc: 15
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_soap_approval.py -q --basetemp=test-results/tmp-task-16 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Bác sĩ chỉnh nháp, ký duyệt, bản cuối bất biến và xem lại được.
  - [ ] Test an toàn: Bệnh nhân/AI không ký; Plan chỉ bác sĩ nhập; PHI phân quyền.

## Tác vụ 17: ICD tham khảo, so sánh bản nháp, audit (Project 262, Nâng cao)
- Trạng thái: todo
- Hiện trạng: chưa thấy endpoint ICD/editor diff/audit trong src/diabetes/router.py
- Việc cần làm: Hoàn thiện và kiểm chứng icd tham khảo, so sánh bản nháp, audit.
- Phụ thuộc: 16
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_soap_review.py -q --basetemp=test-results/tmp-task-17 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Gợi ý E11.x có nguồn; so sánh nháp/bản duyệt và log người sửa.
  - [ ] Test an toàn: Mã chỉ tham khảo, bác sĩ kiểm chứng; không thêm chẩn đoán không có trong hồ sơ.

## Tác vụ 18: Thoại→text, kiểm tra hồ sơ và xuất bản bàn giao (Project 262, Nâng cao)
- Trạng thái: partial
- Hiện trạng: src/voice/router.py có voice chung; chưa nối transcript khám/SOAP, kiểm tra thiếu và PDF
- Việc cần làm: Hoàn thiện và kiểm chứng thoại→text, kiểm tra hồ sơ và xuất bản bàn giao.
- Phụ thuộc: 16, 17
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_soap_export.py -q --basetemp=test-results/tmp-task-18 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Transcript mô phỏng được duyệt, đối chiếu HbA1c/thuốc trước, xuất bản cuối.
  - [ ] Test an toàn: Thiếu dữ kiện phải cảnh báo; không bịa; xuất chỉ bản đã ký cho người có quyền.

## Tác vụ 19: Hồ sơ ăn kiêng, dị ứng và ràng buộc (Project 266, Cơ bản)
- Trạng thái: todo
- Hiện trạng: src/diabetes/nutrition_lookup.py chỉ tra món; chưa có hồ sơ ràng buộc
- Việc cần làm: Hoàn thiện và kiểm chứng hồ sơ ăn kiêng, dị ứng và ràng buộc.
- Phụ thuộc: 1
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_nutrition_profile.py -q --basetemp=test-results/tmp-task-19 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Lưu dị ứng/sở thích, truy vấn lại đúng bệnh nhân.
  - [ ] Test an toàn: Món gây dị ứng bị chặn; không tiết lộ hồ sơ người khác; không kê chế độ điều trị.

## Tác vụ 20: Thực đơn Việt có nguồn và nhật ký ăn (Project 266, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/diabetes/nutrition_lookup.py, tests/test_nutrition.py có lookup; thiếu thực đơn/nhật ký
- Việc cần làm: Hoàn thiện và kiểm chứng thực đơn việt có nguồn và nhật ký ăn.
- Phụ thuộc: 19
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_nutrition.py + tests/test_meal_plan.py -q --basetemp=test-results/tmp-task-20 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Tra món và tạo thực đơn/nhật ký với gram, carbohydrate, năng lượng và nguồn từng số.
  - [ ] Test an toàn: Thực phẩm thiếu dữ liệu không bịa; thực đơn là nháp chờ chuyên gia; cảnh báo dị ứng/nhịn ăn khi dùng thuốc.

## Tác vụ 21: Chuyên gia duyệt và so với đường huyết sau ăn (Project 266, Nâng cao)
- Trạng thái: todo
- Hiện trạng: src/diabetes/router.py chỉ nutrition lookup; chưa có duyệt hoặc liên kết nhật ký ăn
- Việc cần làm: Hoàn thiện và kiểm chứng chuyên gia duyệt và so với đường huyết sau ăn.
- Phụ thuộc: 2, 20
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_meal_review.py -q --basetemp=test-results/tmp-task-21 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Chuyên gia chỉnh/duyệt, bệnh nhân thấy bản duyệt; ghép bữa ăn với số đo sau 2 giờ.
  - [ ] Test an toàn: Không dùng tương quan để chẩn đoán; mục tiêu do bác sĩ đặt; số liệu có nguồn.

## Tác vụ 22: Tình huống đặc biệt và danh sách đi chợ (Project 266, Nâng cao)
- Trạng thái: todo
- Hiện trạng: chưa thấy API thực đơn cá nhân hóa trong src/diabetes/router.py
- Việc cần làm: Hoàn thiện và kiểm chứng tình huống đặc biệt và danh sách đi chợ.
- Phụ thuộc: 20, 21
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_grocery_list.py -q --basetemp=test-results/tmp-task-22 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Tết/ăn chay tạo lựa chọn từ thực phẩm có dữ liệu và danh sách mua theo bản duyệt.
  - [ ] Test an toàn: Dị ứng vẫn bị chặn; ngoài CSDL ghi không rõ, không bịa calo/muối.

## Tác vụ 23: Gợi ý khoa và lịch trống có nguồn (Project 258-booking, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/triage/router.py, src/scheduling/slot_generator.py, tests/test_triage.py; chưa có trích nguồn danh mục khoa hoàn chỉnh
- Việc cần làm: Hoàn thiện và kiểm chứng gợi ý khoa và lịch trống có nguồn.
- Phụ thuộc: 7
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_triage.py -q --basetemp=test-results/tmp-task-23 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Nhu cầu mắt/thận/nội tiết trả khoa trong danh mục và giờ trống mô phỏng.
  - [ ] Test an toàn: Không bịa bác sĩ/khoa; không chẩn đoán; red-flag chuyển 115 thay vì lịch thường.

## Tác vụ 24: Bệnh nhân xác nhận và lễ tân duyệt đặt lịch (Project 258-booking, Cơ bản)
- Trạng thái: todo
- Hiện trạng: src/triage/router.py trả gợi ý slot; chưa thấy API giữ chỗ/xác nhận/duyệt
- Việc cần làm: Hoàn thiện và kiểm chứng bệnh nhân xác nhận và lễ tân duyệt đặt lịch.
- Phụ thuộc: 23
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_booking_confirmation.py -q --basetemp=test-results/tmp-task-24 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Giữ chỗ rồi bệnh nhân xác nhận, lễ tân duyệt mới thành lịch chính thức.
  - [ ] Test an toàn: Người khác không xác nhận/duyệt; red-flag không đặt lịch; chống trùng slot.

## Tác vụ 25: Xung đột lịch, đổi lịch và nhắc hẹn (Project 258-booking, Nâng cao)
- Trạng thái: partial
- Hiện trạng: src/scheduling/solvers.py, slot_generator.py có chọn slot; chưa có booking persisted/notification
- Việc cần làm: Hoàn thiện và kiểm chứng xung đột lịch, đổi lịch và nhắc hẹn.
- Phụ thuộc: 24
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_booking_reschedule.py -q --basetemp=test-results/tmp-task-25 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Slot bận đề xuất slot khác; lễ tân duyệt đổi; gửi nhắc khi có consent.
  - [ ] Test an toàn: Không gửi PHI cho người khác; không xác nhận lịch trước duyệt; cấp cứu không vào queue thường.

## Tác vụ 26: Dashboard điều phối và chuyển người thật (Project 258-booking, Nâng cao)
- Trạng thái: todo
- Hiện trạng: chưa thấy dashboard booking trong frontend/app/ hoặc audit đặt lịch trong src/triage/router.py
- Việc cần làm: Hoàn thiện và kiểm chứng dashboard điều phối và chuyển người thật.
- Phụ thuộc: 24, 25
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_booking_audit.py -q --basetemp=test-results/tmp-task-26 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Tính tải công việc/tỉ lệ đúng khoa trên lịch đã duyệt; thiếu tự tin tạo ca người xử lý.
  - [ ] Test an toàn: Không bịa độ tự tin/nguồn; chỉ role lễ tân xem chi tiết; dữ liệu báo cáo không lộ PHI.

## Thứ tự đề xuất

1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26

## Câu hỏi cần người duyệt

1. Với triage, yêu cầu vừa nói HITL duyệt trước thông báo vừa yêu cầu red-flag cảnh báo tức thì. Đề xuất cảnh báo khẩn ngay, chỉ duyệt hướng xử trí không khẩn; cần xác nhận.
2. Ngưỡng mục tiêu cá nhân, ngưỡng carbohydrate/đường/muối, lịch nhắc và xử lý không phản hồi chưa được định lượng trong `scope_rules`; bác sĩ/chuyên gia cần đặt, không tự chọn.
3. Vai trò điều dưỡng/lễ tân, quyền xem PHI, gửi thông báo cho người thân và danh mục chuyên khoa mô phỏng cần quyết định sản phẩm/consent trước khi triển khai.
4. “App deploy online”, realtime, email/SMS và PDF trong deliverables có môi trường/kênh nào được duyệt? Chưa thể đánh dấu done qua test local.

## Rủi ro

- Working tree có thay đổi code/test chưa commit từ phiên trước; trạng thái `partial` phải xác minh lại trên snapshot khi triển khai.
- Benchmark trong `data/evaluation/bench_triage.json`, `bench_solvers.json`, `bench_labs.json` là dữ liệu thử, không chứng minh chất lượng hiện tại.
- Không dùng dữ liệu bệnh nhân thật cho seed/test; kiểm tra đường DB/index trước lệnh ghi.
- Nguồn y khoa và mục tiêu cá nhân phải được chuyên gia xác nhận trước dùng lâm sàng.
- Docker đã có cấu hình hai service nhưng chưa chạy build/runtime theo yêu cầu trước.
