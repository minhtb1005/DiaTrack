# TASKS — DiaTrack týp 2

> Kiểm chứng index v2 và ưu tiên 1–2, 02/11/2026 22:30 +07 trên `main` HEAD `f65619f62fe7fc3df477a1669363ef81a2ce1371` + working tree dirty: build 1.798 chunk/6 source, audit 0 invalid và sidecar SHA-256 `4e6d7e...ddab`; full backend **637 pass/4 live-provider deselected/0 fail** trong 1.862,29s; frontend production build exit 0; Playwright backend thật 8101 + Next 3101 + DB cô lập `test-results/triage-e2e/tasks-1-7-v2-20261102-222416-151` **14 pass/0 fail** trong 1,4 phút. Retrieval gate v2 **fail** lặp lại: Hit@5 0,733/MRR@5 0,567, miss DQ7/DQ9/DQ12/DQ13; 0 source violation và scope guard đạt. Active pointer đã rollback về index 452 chunk; không package/deploy v2 và không hạ ngưỡng.

> Kiểm chứng 02/11/2026 ~21:07 +07 trên `main` HEAD `f65619f62fe7fc3df477a1669363ef81a2ce1371` + working tree dirty: frontend production build với `NEXT_TEST_DIST_DIR=.next-task-1-7` exit 0; Playwright `e2e/tasks-1-7-live.spec.ts --workers=1 --timeout=90000 --reporter=list` chạy backend thật cổng 8101, Next production cổng 3101 và DB thử cô lập `test-results/triage-e2e/tasks-1-7-final-20261102-210531-616` → **14 pass, 0 fail**, exit 0, 1.4 phút. Đã bao phủ lưu/reload 110 + lịch nhắc + previsit, biên 69/70/250/251/299/300, structured triage, tám biến thể red-flag có/không dấu, từ chối ngoài phạm vi, pending review thường và dashboard bác sĩ. Tại thời điểm này Tác vụ 1–7 còn `partial`: suite chưa bao phủ đủ từng ô integration. Khoảng trống 403/422 và không ghi DB của Tác vụ 1 đã được đóng ngày 03/11/2026; các khoảng trống của tác vụ khác vẫn theo từng mục bên dưới.

> Bổ sung 01/11/2026 cho tác vụ 8–26: Mỗi ô integration dưới đây là kế hoạch chưa thực hiện. Chỉ đánh dấu `done` khi toàn bộ tiêu chí của tác vụ, gồm integration, pass trên code hiện hành với bằng chứng theo cổng nghiệm thu bên dưới; fail/skip/bị chặn không tính đạt. Luồng UI phải gọi backend/API thật, DB/index và tài khoản tổng hợp cô lập; không mock response API thuộc luồng. Kênh gửi thông báo dùng sandbox/người nhận thử được duyệt. Vai trò, consent, ngưỡng retry hoặc hợp đồng chưa chốt phải được xác định trước triển khai, không tự đặt để test pass. Endpoint/UI còn thiếu phải triển khai trong tác vụ tương ứng trước nghiệm thu. Lần cập nhật này chỉ bổ sung kế hoạch, không triển khai hay chạy test.

> Cổng nghiệm thu bổ sung 01/11/2026: Từng tác vụ 1–7 giữ `partial` cho đến khi **toàn bộ** kịch bản integration trong đúng tác vụ chạy pass trên cùng snapshot code hiện hành. Các ô `[x]` cũ là bằng chứng lịch sử, không thay thế cổng này. Test trình duyệt phải gọi backend/API thật và đọc/ghi DB thử cô lập; không mock response của API thuộc luồng đang xét. Chỉ đổi từng tác vụ về `done` sau khi mọi ô integration của tác vụ đó đạt, lệnh thoát 0, ghi SHA hoặc diff, thời điểm +07, cấu hình, số pass/fail/skip và log. Nếu code liên quan đổi sau test, chạy lại phần bị ảnh hưởng.

> Bổ sung 30/10/2026 ~15:44 +07: Hoàn tất thay nhãn theo dõi tại nhà (`low`, `no_alert`, `alert_high`, `critical`), tính lại nhãn log cũ khi đọc; voice daily-check vẫn hỏi chỉ số thiếu và luồng ghi bằng voice nay hỏi giờ đo còn thiếu, chỉ lưu `measured_at` sau xác nhận. Red-flag số đo <70/≥300 được báo ngay sau nhận dạng, kể cả thiếu bối cảnh. Kiểm tra trên `main` 655e0ef + diff: `pytest tests/test_voice_parse.py tests/test_voice_router_unit.py tests/test_glucose_tracker.py tests/test_glucose_policy.py -q --basetemp=test-results/tmp-voice-label-unit-commit2 -o cache_dir=test-results/pytest-cache` 77 pass, 0 fail; `npx tsc --noEmit` exit 0 sau sửa nhãn form; `npm run build` exit 0; Playwright `tracker.spec.ts -g "voice asks for missing measurement time|legacy|no alert|critical submit|spike above 250" --workers=1 --reporter=list` 4 pass. API integration `tests/test_voice_api.py` chưa xác minh: fixture nạp tokenizer `bert-base-uncased` không có trong cache và mạng bị chặn; không coi là pass. Build trước đó chạy đồng thời dev server đã lỗi `.next`, chạy lại độc lập exit 0. Test Playwright lần đầu 1 case pass nhưng lệnh treo khi dọn web server và bị ngắt; kết quả 4 case exit 0 thay thế. Các bằng chứng trước mốc này chỉ là lịch sử.

> Rà soát ngưỡng 30/10/2026 ~10:57 +07, `main` tại `73e3c15` cộng diff chưa commit: `docs/project_requirements.json#scope_rules.threshold_evidence` ghi nguồn/ngữ cảnh các mốc. Chuyển ca không còn dùng 3 nhãn `high` từ dải hiển thị cũ hoặc heuristic tăng 10–15% trong 3 ngày. Kiểm tra: backend tập trung 46 pass (`tests/test_glucose_tracker.py tests/test_anomaly_detector.py tests/test_glucose_policy.py` + 3 case API/queue/security, `--basetemp=test-results/tmp-threshold-focused`); sau sửa thông điệp backend 25 pass (`tests/test_glucose_tracker.py tests/test_glucose_policy.py` + 1 case API biên, `--basetemp=test-results/tmp-threshold-final`); sau sửa heuristic `tests/test_doctor_patients.py` 8 pass (`--basetemp=test-results/tmp-threshold-queue-final`). Cả ba exit 0, có cảnh báo không ghi được pytest cache. Frontend `npx tsc --noEmit`, `npm run build` exit 0; Playwright `tracker.spec.ts -g "explain trend"` 1 pass. Bộ mở rộng 79 case dừng khi nhóm API không trả kết quả, không tính pass. Bằng chứng tác vụ 1–6 bên dưới là lịch sử trên code trước lần sửa này. Dải hiển thị cũ vẫn chưa được xác minh lâm sàng.

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
  - [x] Integration UI/API thật: Playwright backend thật + DB thử cô lập đã nhập 110 mg/dL qua tracker và đọc lại sau tải trang (14 pass/0 fail, 02/11/2026 22:30 +07, bằng chứng đầu file). Bổ sung API/DB 03/11/2026 07:31 +07: cố định `measured_at=2026-11-03T07:15:00+07:00`, đối chiếu response, GET và hàng SQLite; bệnh nhân thứ hai đọc/ghi dữ liệu người đầu đều 403; payload thiếu/sai đều 422; số hàng và record gốc không đổi sau toàn bộ request bị từ chối. `pytest tests/test_api_diabetes.py::TestDiabetesAPI::test_glucose_110_roundtrip_and_ownership -q --basetemp=test-results/tmp-task-1-auth-db-20261103 -o cache_dir=test-results/pytest-cache-task-1` → 1 pass/0 fail/0 skip, exit 0, 130.60s; `main` HEAD `f65619f62fe7fc3df477a1669363ef81a2ce1371` + working tree dirty. Không mock `/v1/auth/*` hoặc `/v1/glucose*`.

## Tác vụ 2: Ngưỡng nguy hiểm và cảnh báo (Project 264, Cơ bản)
- Trạng thái: done
- Hiện trạng: src/diabetes/anomaly_detector.py, src/diabetes/glucose_tracker.py, src/diabetes/router.py, frontend/app/tracker/page.tsx; tests/test_anomaly_detector.py, tests/test_api_diabetes.py, frontend/e2e/tracker.spec.ts; đã tách cảnh báo >250 với khẩn ≥300 và kiểm chứng UI.
- Việc cần làm: Hoàn thiện và kiểm chứng ngưỡng nguy hiểm và cảnh báo.
- Phụ thuộc: 1
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_anomaly_detector.py -q --basetemp=test-results/tmp-task-2 -o cache_dir=test-results/pytest-cache` → 19 pass, 0 fail, exit 0; `test-results/task-2-acceptance.log`.
  - [x] Test chức năng: API `-k glucose_urgent_boundaries` → 1 pass, 13 deselected, exit 0; 69 và 300 báo khẩn, 110 không khẩn, 280 chỉ báo liên hệ bác sĩ; `test-results/task-2-api.log`. UI Playwright hai ca 280/300 → 2 pass, exit 0 khi dùng máy chủ frontend đã chạy sẵn.
  - [x] Test an toàn: Thông báo <70 và ≥300 yêu cầu liên hệ cơ sở y tế ngay; mọi spike nhắc không tự đổi liều thuốc/insulin. Test các biên 69/70/250/251/299/300 lấy từ `scope_rules`; `npx tsc --noEmit` exit 0. Giới hạn: chưa chạy toàn bộ API/RAG; Playwright cần frontend chạy sẵn để tiến trình kết thúc sạch trên máy này.
  - [x] Integration UI/API thật: 03/11/2026 07:45 +07, Playwright ghi lần lượt 69, 70, 250, 251, 299, 300 mg/dL qua tracker vào DB thử cô lập, chờ POST thật rồi tải lại sau từng giá trị; đối chiếu GET `/v1/glucose` trả nhãn + thông điệp. 69/300 hiện banner và yêu cầu liên hệ cơ sở y tế ngay; 251/299 chỉ yêu cầu liên hệ bác sĩ, không có banner/khóa cấp cứu; 70/250 không bị gán cảnh báo khẩn; mọi thông điệp không khuyên tự đổi liều. Không mock `/v1/glucose*`. `npm run test:e2e -- e2e/tasks-1-7-live.spec.ts -g "tracker displays real API safety classifications" --workers=1 --timeout=120000 --reporter=list` → 1 pass/0 fail/0 skip, exit 0, 31,4s; backend thật cổng 8114, Next dev 3114, DB `test-results/triage-e2e/task-2-final-20261103-074352-726`. Backend tập trung 68 pass/9 deselected, TypeScript và production build exit 0. Code: `main` HEAD `f65619f62fe7fc3df477a1669363ef81a2ce1371` + working tree dirty.

## Tác vụ 3: Xu hướng, nhắc đo/tái khám và hướng dẫn có nguồn (Project 264, Cơ bản)
- Trạng thái: done
- Hiện trạng: src/diabetes/glucose_tracker.py, src/diabetes/scope_guard.py, frontend/app/tracker/page.tsx; tests/test_glucose_tracker.py, tests/test_scope_guard.py, tests/test_api_diabetes.py, tests/test_demo_scenarios.py, frontend/e2e/tracker.spec.ts; xu hướng, nhắc việc trong trang, nguồn và câu từ chối cố định đã kiểm chứng.
- Việc cần làm: Hoàn thiện và kiểm chứng xu hướng, nhắc đo/tái khám và hướng dẫn có nguồn.
- Phụ thuộc: 1, 2
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_glucose_tracker.py -q --basetemp=test-results/tmp-task-3 -o cache_dir=test-results/pytest-cache` → 20 pass, 0 fail, exit 0; `test-results/task-3-acceptance.log`.
  - [x] Test chức năng: Playwright `tracker.spec.ts -g "multiple days|explain trend|due reminders"` → 3 pass, exit 0; hai ngày đo hiện trong tóm tắt/log gốc, lịch đo và tái khám đến hạn hiện khi mở trang, tồn tại sau tải lại và xóa được. `npm run build` exit 0, log `test-results/task-3-build.log`; `npx tsc --noEmit` exit 0.
  - [x] Test an toàn: Diễn giải AI không hiển thị khi thiếu metadata nguồn; có nguồn thì hiện tên tài liệu/trang và link về log. `tests/test_scope_guard.py` → 2 pass, API ngoài phạm vi → 1 pass ở `test-results/task-3-scope.log` và 1 pass ở `test-results/task-3-demo.log`, đúng câu cố định `scope_rules`. `git diff --check` exit 0. Giới hạn: lịch nhắc lưu trên thiết bị, chỉ hiện khi trang mở; test UI dùng mock API; không thay mục tiêu lâm sàng do bác sĩ đặt.
  - [x] Integration UI/API thật: 03/11/2026 08:17 +07, tạo 110 và 140 mg/dL tại hai ngày cố định 01–02/11/2026 qua API thật, mở tracker và xác nhận tóm tắt 2 chỉ số/min 110/max 140; từng link xu hướng dùng đúng ID có trong GET `/v1/glucose/{user_id}` và dẫn tới log UI tương ứng. Lịch đo/tái khám lưu trong `localStorage`, còn và hiện đến hạn sau reload; listener xác nhận thao tác lịch không phát request ghi backend, UI ghi rõ backend không gửi thông báo. `npm run test:e2e -- e2e/tasks-1-7-live.spec.ts -g "fixed-day real readings" --workers=1 --timeout=120000 --reporter=list` → 1 pass/0 fail/0 skip, exit 0, DB cô lập `test-results/triage-e2e/task-3-20261103-081351-227`, backend thật 8113/Next dev 3113. Diễn giải chỉ hiện khi context có tên/id nguồn và trang nguyên dương; case nguồn hợp lệ hiện `WHO_HEARTS-D_2020.pdf, trang 12`, case thiếu trang ẩn lời khuyên. Ba UI case đều in `ok` nhưng runner mock treo lúc dọn web server và bị ngắt nên không tính suite exit 0. Backend tập trung 69 pass/8 deselected; `npx tsc --noEmit` và production build `.next-task-3` exit 0. Câu ngoài phạm vi đúng `scope_rules.out_of_scope_reply` nằm trong backend focused pass và integration thật đã pass ngày 02/11. Code: `main` HEAD `f65619f62fe7fc3df477a1669363ef81a2ce1371` + working tree dirty.

## Tác vụ 4: Dashboard bác sĩ và duyệt lời khuyên (Project 264, Nâng cao)
- Trạng thái: done
- Hiện trạng: src/triage/router.py::list_doctor_patients, src/chat/router.py, src/chat/rag_pipeline.py, src/chat/schemas.py, src/reviews/router.py; frontend/app/expert/patients/page.tsx, frontend/app/expert/queue/page.tsx, frontend/app/tracker/page.tsx; tests/test_doctor_patients.py, tests/test_auth_hilt.py, frontend/e2e/overview.spec.ts, frontend/e2e/tracker.spec.ts. Dashboard phân mức theo ngưỡng; diễn giải cá nhân đi qua bác sĩ duyệt.
- Việc cần làm: Hoàn thiện và kiểm chứng dashboard bác sĩ và duyệt lời khuyên.
- Phụ thuộc: 2, 3
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_doctor_patients.py -q --basetemp=test-results/tmp-task-4 -o cache_dir=test-results/pytest-cache` → 7 pass, 0 fail, exit 0; `test-results/task-4-acceptance.log`.
  - [x] Test chức năng: Bác sĩ thấy nhiều bệnh nhân, 300 mg/dL ở mức critical, 280 mg/dL ở watch; yêu cầu diễn giải từ tracker buộc `require_doctor_review`, tạo hàng đợi bác sĩ và chỉ hiện nội dung sau quyết định duyệt. Backend `tests/test_doctor_patients.py tests/test_auth_hilt.py` → 14 pass, log `test-results/task-4-final.log`; UI dashboard/tracker → 2 pass, exit 0; `npm run build` exit 0, `test-results/task-4-build.log`.
  - [x] Test an toàn: API bệnh nhân không trả bản nháp pending; chỉ bác sĩ/admin được duyệt diễn giải theo workflow; hàng đợi lỗi trả 503 và không lộ bản nháp; câu trả lời cần duyệt không ghi cache/bộ nhớ trước duyệt. `tests/test_triage.py` → 27 pass, `test-results/task-4-triage.log`, red-flag vẫn cảnh báo ngay. Không có đường tự đổi mục tiêu/thuốc trong tác vụ này; `npx tsc --noEmit` và `git diff --check` exit 0. Giới hạn: UI dùng mock API; chưa chạy full RAG/benchmark.
  - [x] Integration UI/API thật: Hai bệnh nhân thử có 280 và 300 mg/dL xuất hiện đúng mức watch/critical trên dashboard bác sĩ. Bệnh nhân yêu cầu diễn giải, xác nhận bản nháp pending không lộ; bác sĩ thử đã xác minh thấy yêu cầu và duyệt/sửa, bệnh nhân tải lại mới thấy nội dung cuối. Bệnh nhân khác hoặc tài khoản không có quyền không duyệt được (403). Kiểm tra trạng thái review lưu trong DB thử. Không mock `/v1/doctor/patients`, `/v1/query` hay `/v1/reviews*`; nếu đường RAG phụ thuộc provider/index, dùng cấu hình thử tái lập được và ghi giới hạn.

- Bằng chứng hiện hành 03/11/2026 14:23 +07 (`main` f65619f + dirty tree; SHA file tại `test-results/task-4-tested-snapshot.json`): backend thật 8115 + Next production 3115 (`.next-task-4`), DB/index/memory riêng `test-results/triage-e2e/task-4-complete-20261103`; NVIDIA thật, bản sao index active 452 chunk giữ hash/provenance gate, không dùng v2. `npm run test:e2e -- e2e/tasks-1-7-live.spec.ts --grep 'real RAG review|verified doctor sees' --workers=1 --reporter=list` → **2 pass/0 fail/0 skip, exit 0, 1.4m**. Hai nhánh approved/revised đều qua UI: ẩn draft trên query/reviews/history, bác sĩ đã xác minh nhận hàng đợi, sửa/duyệt, bệnh nhân reload nhận toàn văn (bản sửa >300 ký tự); bệnh nhân khác/dược sĩ sai quyền nhận đúng 403 ở cả `/decide` và `/decision`, DB pending không đổi sau request bị từ chối; sau duyệt status/final/assigned_expert/reviewed_at và history khớp. Dashboard xác minh lại 280 watch/300 critical và chặn bệnh nhân. Log `test-results/task-4-browser-complete.log`, ảnh doctor/patient approved/revised trong DB run; không mock các endpoint nghiệm thu.
- Backend cuối: `.\.venv\Scripts\python.exe -m pytest tests/test_auth_hilt.py tests/test_safety_regressions.py tests/test_tasks_1_7_integration.py tests/test_payload_privacy.py tests/test_chat_language.py -q --basetemp=test-results/tmp-task-4-complete -o cache_dir=test-results/pytest-cache-task-4-complete --junitxml=test-results/task-4-backend-complete.xml` → **106 pass/0 fail/0 skip, exit 0, 94.15s**, env offline + scheduler disable. Bao phủ thêm nurse/pharmacist/specialist và bác sĩ chưa xác minh 403, không trả hash mật khẩu người yêu cầu, cấm sửa rỗng/duyệt lại, không phụ thuộc AI judge khi workflow bắt buộc bác sĩ. `npx tsc --noEmit` exit 0; `NEXT_PUBLIC_API_URL=http://127.0.0.1:8115 NEXT_TEST_DIST_DIR=.next-task-4 npm run build` exit 0; diff-check exit 0.
- Retrieval gold cuối: chạy `scripts/benchmark_verified_index.py::main` với `INDEX_ROOT` ghi đè sang bản sao active452 ở DB run; dataset `data/evaluation/diabetes_retrieval_evaluation.json`, 15/15 eligible, NVIDIA embeddings thật, Hit@5 **0.9333**, MRR@5 **0.6911**, 0 source violation, 3/3 ngoài phạm vi chặn; log `test-results/task-4-retrieval-benchmark.log`. Không thay pointer active/v2.
- Thay đổi: pending query ẩn evaluation; projection bệnh nhân chỉ trả trạng thái/câu hỏi/final sau duyệt, không draft/vitals/notes/evaluation; nurse không đọc queue/detail; reviewer chỉ nhận id/username/role của requester; quyết định có điều kiện DB pending chống ghi đè; UI đọc toàn văn và điều khiển hàng đợi có nhãn truy cập; mandatory doctor review đi thẳng sau RAG/provenance, không gọi AI judge. Sửa retry generation rỗng một lần cả khi đã dùng model hard, tăng budget retry tối thiểu 2048 token, vẫn fail khi còn rỗng.
- Giới hạn/lịch sử: lần đầu sandbox chặn mạng → 500; hai lượt NVIDIA hoạt động nhưng evaluator gặp ký tự ẩn nguồn → 422; sau bỏ judge không cần thiết, lượt kế revised qua nhưng approved gặp content rỗng → 500. Giữ log fail trong `task-4-browser-final.log`, `task-4-browser-retry.log`, `task-4-browser-publish.log`; lượt complete thay thế cho code cuối. CrossEncoder local không nạp được nên runtime dùng fallback không rerank. Chưa full backend suite hoặc benchmark chất lượng câu trả lời bằng judge/bác sĩ thật. Tài khoản bác sĩ mô phỏng và dữ liệu tổng hợp chỉ xác minh workflow, không phải duyệt y khoa. Báo cáo `test-results/task-4-verification.md`; chưa commit.

## Tác vụ 5: Dữ liệu thiếu, dự báo và báo cáo tái khám (Project 264, Nâng cao)
- Trạng thái: done
- Hiện trạng: src/diabetes/followup_report.py, src/diabetes/soap_summary.py, src/diabetes/schemas.py, src/diabetes/router.py và frontend/components/PrevisitView.tsx; tests/test_264_followup.py, tests/test_soap_summary.py, frontend/e2e/previsit.spec.ts. Báo cáo liệt kê ngày chưa có bản ghi, xu hướng mô tả có nguồn log và giới hạn; API thật trả trường followup.
- Việc cần làm: Hoàn thiện và kiểm chứng dữ liệu thiếu, dự báo và báo cáo tái khám.
- Phụ thuộc: 3
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_264_followup.py tests/test_soap_summary.py -q --basetemp=test-results/tmp-task-5-current -o cache_dir=test-results/pytest-cache` → 11 pass, 0 fail, 0 skip, exit 0 (30/10/2026 ~08:50 +07, main 4130934 và diff task 5 chưa commit); có một cảnh báo không ghi được pytest cache trong `test-results`.
  - [x] Test chức năng: ngày không có bản ghi được liệt kê, ngày đo tính theo giờ Việt Nam, xu hướng từ ba ngày liên tiếp có `basis_log_ids`; SOAP JSON API trả `followup` và Markdown có link log. `npx playwright test previsit.spec.ts --workers=1 --reporter=list` → 4 pass, exit 0; `npx tsc --noEmit` và `npm run build` exit 0 (30/10/2026 ~08:51 +07).
  - [x] Test an toàn: không điền giá trị cho ngày thiếu; khi thiếu dữ liệu, xu hướng trả `insufficient_data`; báo cáo không suy HbA1c/không tuyên bố đạt mục tiêu từ đường huyết tự đo, Plan để trống cho bác sĩ. `git diff --check` exit 0. Giới hạn: xu hướng chỉ là mô tả chiều từ dữ liệu có sẵn, không dự báo số đo hoặc gửi thông báo ngoài app; UI test dùng mock API; chưa chạy full RAG/benchmark.
  - [x] Integration UI/API thật: 03/11/2026 15:44 +07, ghi 100/110/120/130 mg/dL tại 30/10 và 01–03/11/2026 qua API thật, chủ động để 31/10 trống; tạo JSON và Markdown từ UI với backend thật. JSON/UI/Markdown cùng liệt kê 31/10 nhưng SQLite không có record ngày đó; xu hướng `up` dùng đúng `basis_log_ids` của ba log 01–03/11. Assessment ghi chưa có HbA1c và không thể kết luận đạt mục tiêu, không sinh số HbA1c; `soap.plan == ""`, Markdown có heading Plan rồi để trống, UI chỉ hiện placeholder cho bác sĩ. Không mock `/v1/glucose*` hoặc `/v1/soap/*`. Bằng chứng chung tác vụ 5–7: Playwright 16 pass/0 fail/0 skip, exit 0, 1.1m; log `test-results/tasks-5-7-browser-final.log`, DB `test-results/triage-e2e/tasks-5-7-20261103`, ảnh `task-5-previsit.png`.
  - [x] Integration NVIDIA riêng: 03/11/2026 15:49–15:51 +07, chạy cùng ca trên API thật 8116 + Next production 3116 với `TRIAGE_E2E_LIVE_RAG=1`, index active 452 chunk sao chép và DB riêng `test-results/triage-e2e/task-5-live-nvidia-20261103`; Playwright `--grep 'previsit report'` → 1 pass/0 fail/0 skip, exit 0, 1.7m. Backend ghi nhận hai POST NVIDIA chat `HTTP/1.1 200 OK`; UI/JSON/Markdown/SQLite và các guard Plan/HbA1c vẫn đạt. Giới hạn: response model API không xuất `_fallback_reason`, nên HTTP 200 không tự chứng minh nội dung model đã parse và được dùng; không thực hiện thêm lần gửi dữ liệu thử ra provider chỉ để quan sát cờ nội bộ.
  - [x] Đóng rủi ro telemetry NVIDIA: 04/11/2026 00:09 +07, harness ánh xạ `TRIAGE_E2E_FRONTEND_URL` sang `FRONTEND_URL` nên CORS origin 3116 trả 200/allow-origin/credentials. SOAP dùng model light, tắt reasoning theo tham số Nemotron `enable_thinking=false`, kiểm content rỗng/finish reason và log mode không chứa payload. API integration live trên DB `task-5-live-telemetry-no-thinking-20261104`: NVIDIA HTTP 200 liền sau bởi `soap_generation mode=llm`, không fallback; S/O/A có nội dung, Plan rỗng, 4 ngày ghi nhận, trend `up`. Unit `tests/test_soap_summary.py` 8 pass/0 fail/0 skip, 38.30s; diff-check 3 file exit 0.

## Tác vụ 6: Hỏi triệu chứng có cấu trúc và phân mức (Project 258-triage, Cơ bản)
- Trạng thái: done
- Hiện trạng: `src/triage/structured_assessment.py`, `src/triage/router.py`, `src/triage/schemas.py`, `tests/test_triage.py`; API `structured=true` hỏi số đo/thời điểm thiếu, phân mức đề xuất và giữ hướng xử trí thường chờ duyệt. Nguồn là protocol mô phỏng từ `docs/project_requirements.json`, chưa phải guideline lâm sàng đã kiểm chứng.
- Việc cần làm: Hoàn thiện và kiểm chứng hỏi triệu chứng có cấu trúc và phân mức.
- Phụ thuộc: 1, 2
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_triage.py -q --basetemp=test-results/tmp-task-6-final -o cache_dir=test-results/pytest-cache` → 29 pass, 0 fail, 0 skip, exit 0 (30/10/2026 ~10:33 +07; main 20fec547 + diff tác vụ 6). Một cảnh báo pytest cache không ghi được.
  - [x] Test chức năng: Mô tả triệu chứng + đường huyết gần nhất tạo câu hỏi cho số đo/thời điểm thiếu, sau đó đề xuất `routine|soon|emergency`; `tests/test_triage.py::TestEndpoint::test_structured_questions_and_review_only_proposal`.
  - [x] Test an toàn: Đề xuất ghi rõ không phải chẩn đoán; trường hợp thường không trả lịch/hướng xử trí trước duyệt; nguồn protocol mô phỏng và ngưỡng trong `docs/project_requirements.json`. Glucose 69/300 cảnh báo 115 ngay cả khi thiếu triệu chứng. Giới hạn: chưa có hàng đợi duyệt thật (tác vụ 8), chưa benchmark chất lượng phân mức với gold set; UI chưa dùng `structured=true`.
  - [x] Integration UI/API thật: 03/11/2026 15:44 +07, UI gửi `structured=true`; khi thiếu số đo nhận câu hỏi bổ sung, khi đủ 180 mg/dL + thời điểm nhận `proposed_priority=soon` (thuộc enum), `rationale` ghi rõ không phải chẩn đoán, `source` trỏ `project_requirements.json`, `review_status=pending_clinician_review`. Response và UI không có danh sách bác sĩ/lịch hay hướng xử trí đã duyệt. Sửa lỗi nhánh người dùng đăng nhập làm rơi ba trường proposal khi tạo case; UI nay hiện mức/lý do/nguồn. Không mock `/v1/triage`. Bằng chứng: cùng lượt Playwright 16 pass; ảnh `task-6-structured.png` trong DB run.

## Tác vụ 7: Bốn nhóm red-flag và từ chối ngoài phạm vi (Project 258-triage, Cơ bản)
- Trạng thái: done
- Hiện trạng: `src/triage/red_flag.py`, `src/triage/router.py`, `src/diabetes/scope_guard.py`, `frontend/app/tracker/page.tsx`; bốn nhóm riêng, số đo khẩn ưu tiên trước scope, UI hiển thị câu từ chối cố định.
- Việc cần làm: Hoàn thiện và kiểm chứng bốn nhóm red-flag và từ chối ngoài phạm vi.
- Phụ thuộc: 2, 6
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_triage.py -q --basetemp=test-results/tmp-task-7 -o cache_dir=test-results/pytest-cache` → 34 pass, 0 fail, 0 skip, exit 0 (30/10/2026 ~16:13 +07, `main` d9a806f + diff tác vụ 7); 1 cảnh báo cache WinError 5. Env: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `MONITOR_SCHEDULER_DISABLE=true`.
  - [x] Test chức năng: Có dấu/không dấu cho hạ đường huyết, nghi tăng đường huyết nguy hiểm, bàn chân, tim/đột quỵ; câu bình thường không báo nhầm. `tests/test_triage.py::TestRedFlag`.
  - [x] Test an toàn: Red-flag và số đo <70/≥300 luôn trả 115/đến cơ sở y tế trước scope; ngoài phạm vi trả đúng câu cố định, không chẩn đoán. Playwright `npx playwright test e2e/triage-safety.spec.ts --workers=1 --reporter=list` → 1 pass, exit 0, ~16:12 +07 (mock API); `npx tsc --noEmit` và `npm run build` exit 0. Giới hạn: UI dùng mock API, chưa benchmark gold set, chưa xác minh toàn bộ RAG/API khác.
  - [x] Integration UI/API thật: 03/11/2026 15:44 +07, 8 biến thể có/không dấu của 4 nhóm đều cảnh báo 115 và trả danh sách bác sĩ rỗng; ca thường `khát nhiều`, 180 mg/dL không bị gắn red-flag và chỉ vào pending review. Ca `đau ngực, méo miệng và hỏi về huyết áp` trả cảnh báo 115 thay vì scope refusal, chứng minh red-flag ưu tiên. 69 và 300 được gửi trong payload `/v1/triage` thật, trả `emergency`, `proposed_priority=emergency`, không lịch/danh sách bác sĩ. Câu ngoài phạm vi trả đúng câu cố định, không chứa tuyên bố chẩn đoán và không có bác sĩ. Không mock `/v1/triage`; cùng lượt Playwright 16 pass/0 fail.

- Xác minh chung code cuối tác vụ 5–7: `.\.venv\Scripts\python.exe -m pytest tests/test_264_followup.py tests/test_soap_summary.py tests/test_triage.py -q --basetemp=test-results/tmp-tasks-5-7-focused -o cache_dir=test-results/pytest-cache-tasks-5-7-focused --junitxml=test-results/tasks-5-7-focused.xml` → 45 pass/0 fail/0 skip, exit 0, 66.31s. `npx tsc --noEmit` và production build `NEXT_TEST_DIST_DIR=.next-tasks-5-7 npm run build` exit 0. Code lúc chạy: `main` HEAD `f65619f62fe7fc3df477a1669363ef81a2ce1371` + working tree dirty; chưa commit. Lượt Playwright đầu 15 pass/1 fail chỉ do selector UI không khớp câu API, đã sửa và được lượt 16 pass thay thế. Chưa chạy full backend suite.

## Tác vụ 8: Hàng đợi điều dưỡng duyệt/điều chỉnh (Project 258-triage, Nâng cao)
- Trạng thái: done
- Hiện trạng: `src/triage/review_queue.py` lưu ca và audit SQLite; `src/triage/router.py` cung cấp API duyệt có phân quyền; `frontend/app/expert/triage/page.tsx` cho điều dưỡng đã xác minh duyệt/sửa, tracker polling sau duyệt. Cập nhật hàng đợi và bệnh nhân bằng polling 5 giây, không dùng WebSocket.
- Bằng chứng integration 01/11/2026 ~17:18 +07: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_triage_e2e.ps1` → Playwright `triage-review.integration.spec.ts` 1 pass, 0 fail, 0 skip, exit 0 (56.1s). `main` HEAD `f65619f62fe7fc3df477a1669363ef81a2ce1371` + diff tác vụ 8 chưa commit. API thật `127.0.0.1:8108`, Next thật `127.0.0.1:3108`, SQLite/log thử riêng trong `test-results/triage-e2e/run-20261101-171610-116` và log cùng tiền tố. Không mock `/v1/auth/*` hoặc `/v1/triage*`. Env offline và tắt scheduler, không dùng provider/index cho đường triage này.
- Hậu kiểm 01/11/2026 ~17:21 +07: `.\.venv\Scripts\python.exe -m pytest tests/test_triage_monitor.py -q --basetemp=test-results/tmp-task-8-integration-final -o cache_dir=test-results/pytest-cache-task8-final` (env offline/scheduler disable) → 4 pass, 0 fail, 0 skip, exit 0; `npx tsc --noEmit` exit 0; `npm run build` chạy lại riêng → exit 0. Lần build chạy đồng thời trước đó lỗi collect `/login`, không dùng làm bằng chứng pass. `git diff --check` exit 0.
- Phụ thuộc: 6, 7
- Chấp nhận:
  - [x] `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 MONITOR_SCHEDULER_DISABLE=true .\.venv\Scripts\python.exe -m pytest tests/test_triage_monitor.py -q --basetemp=test-results/tmp-task-8-20261101c -o cache_dir=test-results/pytest-cache-task8c` → 4 pass, 0 fail, 0 skip, exit 0 (01/11/2026 ~16:49 +07, main f65619f + diff tác vụ 8). Lần đầu với `tmp-task-8` lỗi WinError 5 ở setup, không tính pass.
  - [x] Test API chức năng: Ca không khẩn vào hàng đợi, điều dưỡng đã xác minh duyệt/sửa rồi bệnh nhân mới đọc được nội dung cuối; 4 pass ở lệnh trên.
  - [x] Test API an toàn: Red-flag trả 115 ngay; bệnh nhân khác và điều dưỡng chưa xác minh bị từ chối; audit lưu người duyệt, mức ưu tiên trước/sau, nội dung trước/sau và thời điểm. 4 pass ở lệnh trên.

  - [x] Integration UI/API thật (tác vụ 8): Bệnh nhân tạo ca không khẩn qua UI; điều dưỡng đã xác minh mở ở phiên đăng nhập riêng, sửa/duyệt; bệnh nhân nhận đúng nội dung cuối sau tải lại/polling. Trước duyệt không lộ hướng xử trí; bệnh nhân bị 403 khi duyệt/xem hàng đợi; SQLite lưu người duyệt, mức/nội dung trước và sau, thời điểm. Ca red-flag báo 115 ngay và không tạo ca mới khi hàng đợi còn pending. Playwright 1 pass như bằng chứng trên.

## Tác vụ 9: Phiếu bàn giao và giải thích có nguồn (Project 258-triage, Nâng cao)
- Trạng thái: partial
- Hiện trạng: API/UI phiếu bàn giao đã chiếu dữ liệu ca, dữ kiện thiếu, lý do và liên kết nguồn; còn xung đột tiêu chí integration vì luồng tác vụ 6 không tạo ca cho tới khi đã thu đủ dữ kiện bắt buộc.
- Việc cần làm: Hoàn thiện và kiểm chứng phiếu bàn giao và giải thích có nguồn.
- Phụ thuộc: 6, 8
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_triage_handoff.py -q --basetemp=test-results/tmp-task-9 -o cache_dir=test-results/pytest-cache-task9` → 1 pass, 0 fail, 0 skip, exit 0 (04/11/2026 +07, `main` e0e062d + diff tác vụ 9).
  - [x] Test chức năng: Phiếu gồm triệu chứng nguyên văn, chỉ số gần nhất, dữ kiện thiếu, lý do mức ưu tiên và hai liên kết nguồn.
  - [x] Test an toàn: Không suy diễn triệu chứng/chỉ số; bệnh nhân khác nhận 404; phiếu ghi rõ không phải chẩn đoán.

  - [ ] Integration UI/API thật (tác vụ 9): Tạo phiên có triệu chứng, số đo và dữ kiện thiếu, mở phiếu bàn giao qua UI người có quyền; đối chiếu từng trường với dữ liệu phiên/log trong DB thử và mở liên kết nguồn. Tải lại vẫn đúng phiên; dữ kiện không có phải ghi thiếu; bệnh nhân khác không đọc được phiếu, không lẫn dữ liệu giữa hai phiên.
  - Bằng chứng một phần 04/11/2026 +07: `scripts/run_triage_e2e.ps1` → 1 pass/0 fail trên API, Next và SQLite thử thật; điều dưỡng mở phiếu đúng triệu chứng, 180 mg/dL, khởi phát, lý do/cảnh báo và hai link nguồn. Lượt đầu fail do assertion cũ đòi priority null trong khi API trả `soon`, đã sửa và lượt sau đạt. `npx tsc --noEmit` và `NEXT_TEST_DIST_DIR=.next-task-9 npm run build` exit 0. Chưa đánh dấu integration đạt: tác vụ 6 hiện không tạo ca khi còn thiếu glucose/onset, nên không thể tạo đúng ca thiếu dữ kiện qua UI mà không đổi hợp đồng thu thập; ca trái quyền mới được kiểm ở API test, chưa qua phiên UI thứ hai.

## Tác vụ 10: Kiểm toán và đối chiếu với điều dưỡng (Project 258-triage, Nâng cao)
- Trạng thái: done
- Hiện trạng: `src/triage/review_queue.py` giữ audit và tính tỷ lệ khác quyết định; gold red-flag được đánh giá riêng theo `data/evaluation/bench_triage.json` để lỗi nguy hiểm không bị metric chung che lấp. Báo cáo tổng hợp không trả PII.
- Việc cần làm: Hoàn thiện và kiểm chứng kiểm toán và đối chiếu với điều dưỡng.
- Phụ thuộc: 8, 9
- Chấp nhận:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_triage_audit.py -q --basetemp=test-results/tmp-task-10 -o cache_dir=test-results/pytest-cache-task10` → 1 pass, 0 fail, 0 skip, exit 0; 04/11/2026 04:28 +07, `main` HEAD `e0e062d` + diff tác vụ 10.
  - [x] Test chức năng: Log giữ đề xuất, chỉnh sửa, người duyệt, thời gian; báo cáo tỷ lệ sai khác với quyết định người duyệt và ghi dataset/version gold.
  - [x] Test an toàn: Gold red-flag có mẫu số/danh sách lỗi riêng; báo cáo không chứa requester/message và bệnh nhân nhận 403.

  - [x] Integration UI/API thật (tác vụ 10): 04/11/2026 04:29 +07, `scripts/run_triage_e2e.ps1` chạy API 8108, Next 3108 và SQLite thử cô lập → Playwright 1 pass/0 fail/0 skip, exit 0, 38,4s. Ca `soon` được điều dưỡng sửa thành `routine`; DB giữ actor, đề xuất/quyết định, nội dung trước/sau và cùng thời điểm reviewed/audit. UI/API báo 1/1 khác (100,0%), gold red-flag v1 có 0 lỗi; response tổng hợp không có requester/message, bệnh nhân bị 403. Red-flag khẩn đi đường cảnh báo tức thì và không bị đưa vào hàng đợi thường. Đây là kiểm tra integration, không thay benchmark chất lượng.

## Tác vụ 11: Bác sĩ tạo, duyệt và dừng phác đồ (Project 260, Cơ bản)
- Trạng thái: done
- Hiện trạng: src/medications/router.py, tests/test_medications.py; code chưa commit, cần kiểm lại tích hợp UI và audit thay đổi
- Việc cần làm: Hoàn thiện và kiểm chứng bác sĩ tạo, duyệt và dừng phác đồ.
- Phụ thuộc: 1
- Chấp nhận:
  - [x] Pytest `tests/test_medications.py` trên diff tác vụ 11 → 8 pass/0 fail; lượt regression sau tác vụ 13 → 10 pass chung, 04/11/2026 +07.
  - [x] Test chức năng: Bác sĩ tạo nháp, duyệt; bệnh nhân chỉ thấy lịch duyệt; bác sĩ dừng có lý do; audit giữ `created/approved/stopped`.
  - [x] Test an toàn: Bệnh nhân không tạo/dừng, bác sĩ khác không duyệt/dừng; không có đường AI áp dụng liều.

  - [x] Integration UI/API thật: 04/11/2026 04:42 +07, suite API/Next/SQLite cô lập tạo nháp, xác nhận bệnh nhân chưa thấy, bác sĩ khác 403, duyệt rồi bệnh nhân thấy, dừng có lý do và tải lại audit `created/approved/stopped`. Cùng lượt Playwright 2 pass/0 fail, 50,8s.

## Tác vụ 12: Lịch nhắc và xác nhận đã dùng/bỏ liều (Project 260, Cơ bản)
- Trạng thái: done
- Hiện trạng: src/medications/router.py, frontend/app/medications/page.tsx; tests/test_medications.py; chưa có nhắc ngoài trang và hội thoại
- Việc cần làm: Hoàn thiện và kiểm chứng lịch nhắc và xác nhận đã dùng/bỏ liều.
- Phụ thuộc: 11
- Chấp nhận:
  - [x] Pytest `tests/test_medications.py` → 9 pass/0 fail/0 skip, 47,80s, 04/11/2026 +07.
  - [x] Test chức năng: Lịch theo giờ đã duyệt; scheduler tạo notification nội bộ ngoài trang đúng một lần; xác nhận đã dùng/bỏ liều cập nhật dashboard.
  - [x] Test an toàn: Tương lai/trùng bị từ chối; bỏ liều nhắc hỏi bác sĩ/dược sĩ và không tự uống bù.

  - [x] Integration UI/API thật: scheduler thử tạo in-app notification trong `/my/reviews`, lần chạy hai gửi 0; bệnh nhân báo bỏ liều qua UI, DB/API trả `skipped`, gửi trùng 409, thông báo không uống bù. Xác nhận tương lai được unit/API test 422. Kênh thử là notification nội bộ, không tuyên bố email/web-push.

## Tác vụ 13: Tuân thủ và đối chiếu đường huyết (Project 260, Nâng cao)
- Trạng thái: done
- Hiện trạng: src/medications/router.py có tỉ lệ, chưa có chuỗi bỏ liều/đối chiếu bác sĩ
- Việc cần làm: Hoàn thiện và kiểm chứng tuân thủ và đối chiếu đường huyết.
- Phụ thuộc: 1, 12
- Chấp nhận:
  - [x] Pytest `tests/test_medications.py tests/test_medication_adherence.py` → 10 pass/0 fail/0 skip, 50,50s, 04/11/2026 +07.
  - [x] Test chức năng: Bác sĩ thấy tử/mẫu số, tỷ lệ, chuỗi bỏ liều và danh sách log cùng kỳ; kỳ rỗng ghi chưa có dữ liệu.
  - [x] Test an toàn: Disclaimer không suy hiệu quả/đổi liều; response bác sĩ chỉ có plan do chính bác sĩ tạo, bệnh nhân chỉ xem chính mình.

  - [x] Integration UI/API thật: cùng suite 04/11/2026, lịch một liều bị bỏ + log 180 mg/dL; UI bác sĩ hiện 0/1 (0%), chuỗi 1 và 180 mg/dL, kèm cảnh báo không chứng minh hiệu quả/đề xuất đổi liều. Trước khi có log, UI ghi chưa có dữ liệu; bác sĩ khác không đọc được plan qua danh sách lọc theo owner.

## Tác vụ 14: Báo tác dụng phụ, nhắc lại, báo cáo và duyệt đổi lịch (Project 260, Nâng cao)
- Trạng thái: todo
- Hiện trạng: src/medications/router.py chưa có luồng tác dụng phụ/retry/phiên bản lịch
- Việc cần làm: Hoàn thiện và kiểm chứng báo tác dụng phụ, nhắc lại, báo cáo và duyệt đổi lịch.
- Phụ thuộc: 11, 12
- Chấp nhận:
  - [ ] `.\.venv\Scripts\python.exe -m pytest tests/test_medication_escalation.py -q --basetemp=test-results/tmp-task-14 -o cache_dir=test-results/pytest-cache` → exit 0, 0 fail; nếu test chưa có, tạo file nêu trong lệnh ở phiên triển khai.
  - [ ] Test chức năng: Báo triệu chứng nặng tạo cảnh báo; không phản hồi tạo retry giới hạn; đổi lịch có bác sĩ duyệt và báo cáo.
  - [ ] Test an toàn: Hạ đường huyết nặng luôn escalate; không tự đổi/ngưng thuốc; báo người thân chỉ khi có đồng ý/phân quyền.

  - [ ] Integration UI/API thật (tác vụ 14): Bệnh nhân báo triệu chứng nặng qua UI, người phụ trách nhận ca thật và cảnh báo khẩn hiện ngay. Với lịch không phản hồi, chạy scheduler thử theo thời gian kiểm soát và giới hạn retry đã được duyệt; đối chiếu số lần gửi trong DB/kênh thử. Yêu cầu đổi lịch chỉ có hiệu lực sau bác sĩ duyệt, báo cáo giữ phiên bản trước/sau; không gửi người thân thiếu consent, không tự ngưng thuốc.

## Tác vụ 15: Nhập transcript và soạn SOAP có mục thiếu (Project 262, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/diabetes/soap_summary.py, router.py, tests/test_soap_summary.py: SOAP từ logs; chưa nhận transcript/đánh dấu thiếu có cấu trúc
- Việc cần làm: Hoàn thiện và kiểm chứng nhập transcript và soạn soap có mục thiếu.
- Phụ thuộc: 1
- Chấp nhận:
  - [x] `tests/test_soap_summary.py` trong regression tác vụ 15–26: đạt; toàn regression 59 pass/0 fail, 04/11/2026 07:01 +07.
  - [x] Test chức năng: Transcript + log tạo nháp S/O/A, trường không có ghi “chưa ghi nhận”.
  - [x] Test an toàn: Không tự chẩn đoán; Plan trống; S/O/A liên kết transcript/log gốc.

  - [ ] Integration UI/API thật (tác vụ 15): Nhập transcript tổng hợp và log thử qua UI, tạo SOAP qua API thật; đối chiếu S/O/A với đoạn transcript/log có thể mở lại. Trường thiếu ghi chưa ghi nhận, Plan trống; tải lại không lẫn bệnh nhân; trường hợp transcript mâu thuẫn hoặc thiếu không được tự bịa dữ kiện/chẩn đoán.
  - [x] Integration nền UI/API/SQLite thật 04/11/2026: bệnh nhân có log 142 mg/dL nhập transcript trên `/soap`, UI hiện S/O/A, evidence log và Plan khóa; bác sĩ mở cùng note ID ở phiên khác, nhập Plan, lưu và ký; DB/API tải lại `signed`. Nằm trong Playwright 5 pass/0 fail, 1,3 phút. Các ca transcript mâu thuẫn chuyên biệt vẫn do unit guard bao phủ, chưa có case browser riêng.

## Tác vụ 16: Bác sĩ sửa, ký duyệt rồi lưu (Project 262, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/diabetes/router.py chỉ generate/markdown; chưa có editor + trạng thái duyệt
- Việc cần làm: Hoàn thiện và kiểm chứng bác sĩ sửa, ký duyệt rồi lưu.
- Phụ thuộc: 15
- Chấp nhận:
  - [x] `tests/test_soap_approval.py` đạt trong regression 59 pass/0 fail.
  - [x] Test chức năng: Bác sĩ chỉnh nháp, ký duyệt, bản cuối bất biến và xem lại được.
  - [x] Test an toàn: Bệnh nhân/AI không ký; Plan chỉ bác sĩ nhập; PHI phân quyền.

  - [ ] Integration UI/API thật (tác vụ 16): Bác sĩ có quyền mở nháp, sửa S/O/A và nhập Plan, ký duyệt rồi tải lại bản cuối từ DB thử. Gửi yêu cầu sửa trực tiếp bản đã ký bị từ chối; lưu dấu vết người ký/thời điểm. Bệnh nhân và tài khoản trái quyền không ký, sửa Plan hoặc đọc hồ sơ khác.
  - [x] Integration nền 04/11/2026: hai browser context bệnh nhân/bác sĩ dùng API và SQLite cô lập; bệnh nhân thấy Plan disabled, bác sĩ sửa/ký và API xác nhận bản `signed`. Unit test xác minh sửa bản ký trả 409 và bệnh nhân ký trả 403. Playwright chung 5 pass.

## Tác vụ 17: ICD tham khảo, so sánh bản nháp, audit (Project 262, Nâng cao)
- Trạng thái: partial
- Hiện trạng: chưa thấy endpoint ICD/editor diff/audit trong src/diabetes/router.py
- Việc cần làm: Hoàn thiện và kiểm chứng icd tham khảo, so sánh bản nháp, audit.
- Phụ thuộc: 16
- Chấp nhận:
  - [x] `tests/test_soap_review.py` đạt trong regression 59 pass/0 fail.
  - [x] Test chức năng: Gợi ý E11.x có nguồn WHO; audit giữ trước/sau và người sửa.
  - [x] Test an toàn: Mã chỉ tham khảo, bác sĩ kiểm chứng; không tự thêm mã vào SOAP.

  - [ ] Integration UI/API thật (tác vụ 17): Dùng hồ sơ thử có dữ kiện đủ và thiếu, bác sĩ mở gợi ý ICD có nguồn, chỉnh nháp và so sánh với bản duyệt qua UI; diff/audit phải khớp dữ liệu trước/sau trong DB. Mã E11.x chỉ là tham khảo có nguồn tra được, không tự thêm chẩn đoán; người trái quyền không đọc audit hồ sơ.

## Tác vụ 18: Thoại→text, kiểm tra hồ sơ và xuất bản bàn giao (Project 262, Nâng cao)
- Trạng thái: partial
- Hiện trạng: src/voice/router.py có voice chung; chưa nối transcript khám/SOAP, kiểm tra thiếu và PDF
- Việc cần làm: Hoàn thiện và kiểm chứng thoại→text, kiểm tra hồ sơ và xuất bản bàn giao.
- Phụ thuộc: 16, 17
- Chấp nhận:
  - [x] `tests/test_soap_export.py` đạt trong regression 59 pass/0 fail; chỉ bản ký và role bác sĩ/admin xuất được.
  - [ ] Test chức năng: Transcript mô phỏng được duyệt, đối chiếu HbA1c/thuốc trước, xuất bản cuối.
  - [ ] Test an toàn: Thiếu dữ kiện phải cảnh báo; không bịa; xuất chỉ bản đã ký cho người có quyền.

  - [ ] Integration UI/API thật (tác vụ 18): Nạp audio tổng hợp vào luồng thoại thật, nhận transcript qua dịch vụ STT thử, bác sĩ sửa/xác nhận rồi tạo SOAP, đối chiếu thuốc/HbA1c có sẵn và cảnh báo phần thiếu. Ký bản cuối, xuất tài liệu bàn giao và kiểm tra nội dung/file tải về khớp bản đã ký; bản nháp hoặc người trái quyền không xuất được. Thiếu STT/kênh xuất thì ghi chưa xác minh, không thay bằng mock response.
  - Bằng chứng STT thật 04/11/2026 08:20 +07: thêm provider local `openai/whisper-tiny` opt-in; Piper sinh WAV tiếng Việt trong bộ nhớ, gửi HTTP multipart tới `/v1/voice/transcribe` trên API/DB cô lập; response 200 và transcript không rỗng. Transcript tiny sai âm (`Đừng quyết...`) nên parser không lấy được 142; đây chỉ chứng minh đường STT thật hoạt động, **không đạt gate độ chính xác**. Chưa nối audio→SOAP trong cùng Playwright và export vẫn là text, chưa phải PDF; task giữ partial.

## Tác vụ 19: Hồ sơ ăn kiêng, dị ứng và ràng buộc (Project 266, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/diabetes/nutrition_lookup.py chỉ tra món; chưa có hồ sơ ràng buộc
- Việc cần làm: Hoàn thiện và kiểm chứng hồ sơ ăn kiêng, dị ứng và ràng buộc.
- Phụ thuộc: 1
- Chấp nhận:
  - [x] `tests/test_nutrition_profile.py` đạt trong regression 59 pass/0 fail.
  - [x] Test chức năng: Lưu dị ứng/sở thích, truy vấn lại đúng bệnh nhân.
  - [x] Test an toàn: Món gây dị ứng bị chặn; không tiết lộ hồ sơ người khác; không kê chế độ điều trị.

  - [ ] Integration UI/API thật (tác vụ 19): Bệnh nhân nhập dị ứng/sở thích qua UI, tải lại và đối chiếu hồ sơ từ API/DB; tài khoản khác không đọc/sửa được. Dùng hồ sơ đó yêu cầu món có thành phần gây dị ứng, hệ thống phải chặn trong luồng thật; hồ sơ thiếu thông tin không được coi như đã xác nhận không dị ứng.
  - Bằng chứng nền 04/11/2026: Playwright bệnh nhân lưu hồ sơ và tạo meal plan qua UI/API/SQLite thật; specialist mở đúng plan ID và duyệt ở phiên khác. Unit test giữ chặn dị ứng, ownership và trạng thái dị ứng chưa rõ. Chưa có browser case cố tình chọn món dị ứng.

## Tác vụ 20: Thực đơn Việt có nguồn và nhật ký ăn (Project 266, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/diabetes/nutrition_lookup.py, tests/test_nutrition.py có lookup; thiếu thực đơn/nhật ký
- Việc cần làm: Hoàn thiện và kiểm chứng thực đơn việt có nguồn và nhật ký ăn.
- Phụ thuộc: 19
- Chấp nhận:
  - [x] `tests/test_nutrition.py tests/test_meal_plan.py` đạt trong regression 59 pass/0 fail (sửa lệnh tài liệu sai dấu `+`).
  - [x] Test chức năng: Tra món và tạo thực đơn/nhật ký với gram, carbohydrate, năng lượng và nguồn từng số.
  - [x] Test an toàn: Thực phẩm thiếu dữ liệu trả `unknown`/không có số; thực đơn là nháp chờ chuyên gia; có cảnh báo không nhịn ăn/đổi thuốc.

  - [ ] Integration UI/API thật (tác vụ 20): Tra món Việt, tạo thực đơn nháp và ghi bữa ăn qua UI/API thật với dataset thử có nguồn; tải lại đối chiếu gram, carbohydrate, năng lượng và nguồn từng giá trị. Món không có dữ liệu phải ghi không rõ, không tạo số giả; món gây dị ứng bị chặn, nháp chưa được trình bày như bản chuyên gia đã duyệt; kiểm tra cảnh báo nhịn ăn khi dùng thuốc.

## Tác vụ 21: Chuyên gia duyệt và so với đường huyết sau ăn (Project 266, Nâng cao)
- Trạng thái: partial
- Hiện trạng: src/diabetes/router.py chỉ nutrition lookup; chưa có duyệt hoặc liên kết nhật ký ăn
- Việc cần làm: Hoàn thiện và kiểm chứng chuyên gia duyệt và so với đường huyết sau ăn.
- Phụ thuộc: 2, 20
- Chấp nhận:
  - [x] `tests/test_meal_review.py` đạt trong regression 59 pass/0 fail.
  - [x] Test chức năng: Chuyên gia/bác sĩ duyệt; nhật ký chỉ ghép số đo khi có ID tường minh, không tự ghép ca thiếu.
  - [x] Test an toàn: Response ghi tương quan không chứng minh nguyên nhân/chẩn đoán; số liệu có nguồn.

  - [ ] Integration UI/API thật (tác vụ 21): Chuyên gia có quyền sửa/duyệt thực đơn qua UI; bệnh nhân chỉ thấy bản được duyệt là bản chính thức sau tải lại. Ghi bữa ăn và số đo sau 2 giờ, kiểm tra liên kết ID/thời điểm đúng trong DB; ca thiếu số đo không tự ghép dữ liệu khác. Người trái quyền không duyệt; báo cáo không chẩn đoán hoặc tự đặt mục tiêu.

## Tác vụ 22: Tình huống đặc biệt và danh sách đi chợ (Project 266, Nâng cao)
- Trạng thái: partial
- Hiện trạng: chưa thấy API thực đơn cá nhân hóa trong src/diabetes/router.py
- Việc cần làm: Hoàn thiện và kiểm chứng tình huống đặc biệt và danh sách đi chợ.
- Phụ thuộc: 20, 21
- Chấp nhận:
  - [x] `tests/test_grocery_list.py` đạt trong regression 59 pass/0 fail.
  - [x] Test chức năng: Tết/ăn chay là scenario của nháp; danh sách mua chỉ sinh từ đúng phiên bản đã duyệt.
  - [x] Test an toàn: Dị ứng vẫn bị chặn; ngoài CSDL ghi không rõ, không bịa dinh dưỡng.

  - [ ] Integration UI/API thật (tác vụ 22): Chọn tình huống Tết/ăn chay qua UI, tạo lựa chọn từ dataset thử có nguồn, chuyên gia duyệt rồi sinh danh sách mua. Đối chiếu thành phần/số lượng với đúng phiên bản duyệt; đổi bản nháp không làm thay danh sách chính thức. Dị ứng vẫn bị chặn; nguyên liệu ngoài dataset ghi không rõ, không bịa dinh dưỡng.

## Tác vụ 23: Gợi ý khoa và lịch trống có nguồn (Project 258-booking, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/triage/router.py, src/scheduling/slot_generator.py, tests/test_triage.py; chưa có trích nguồn danh mục khoa hoàn chỉnh
- Việc cần làm: Hoàn thiện và kiểm chứng gợi ý khoa và lịch trống có nguồn.
- Phụ thuộc: 7
- Chấp nhận:
  - [x] `tests/test_triage.py` đạt trong regression 59 pass/0 fail.
  - [x] Test chức năng: Nhu cầu mắt/thận/nội tiết trả khoa trong roster và giờ trống mô phỏng.
  - [x] Test an toàn: Không bịa bác sĩ/khoa; red-flag chuyển 115 và không trả slot.

  - [ ] Integration UI/API thật (tác vụ 23): Bệnh nhân nhập nhu cầu mắt/thận/nội tiết qua UI; đối chiếu khoa, bác sĩ và giờ trống trả từ API thật với danh mục/lịch mô phỏng trong DB thử, nguồn mở được. Không có slot thì báo hết lịch, không bịa; nhập red-flag phải nhận cảnh báo 115 thay lịch thường.

## Tác vụ 24: Bệnh nhân xác nhận và lễ tân duyệt đặt lịch (Project 258-booking, Cơ bản)
- Trạng thái: partial
- Hiện trạng: src/triage/router.py trả gợi ý slot; chưa thấy API giữ chỗ/xác nhận/duyệt
- Việc cần làm: Hoàn thiện và kiểm chứng bệnh nhân xác nhận và lễ tân duyệt đặt lịch.
- Phụ thuộc: 23
- Chấp nhận:
  - [x] `tests/test_booking_confirmation.py` đạt trong regression 59 pass/0 fail.
  - [x] Test chức năng: Giữ chỗ rồi bệnh nhân xác nhận, role `receptionist`/admin duyệt mới thành lịch chính thức.
  - [x] Test an toàn: Người khác không xác nhận/duyệt; red-flag không vào luồng; unique index chống trùng slot.

  - [ ] Integration UI/API thật (tác vụ 24): Bệnh nhân giữ chỗ rồi xác nhận qua UI, lễ tân có quyền duyệt ở phiên khác; tải lại chỉ thấy lịch chính thức sau duyệt. Hai bệnh nhân cùng yêu cầu một slot qua API thật phải chỉ có một lịch hợp lệ, kiểm tra DB; người khác không xác nhận/duyệt hộ trái quyền. Red-flag không đi qua luồng đặt lịch thường.
  - [x] Integration nền 04/11/2026: thêm role `receptionist` xuyên schema/migration/admin UI; bệnh nhân giữ chỗ và xác nhận, receptionist đăng nhập phiên khác, thấy dashboard chờ và duyệt qua UI. Unique slot/ownership/red-flag được test API. Playwright chung 5 pass/0 fail.

## Tác vụ 25: Xung đột lịch, đổi lịch và nhắc hẹn (Project 258-booking, Nâng cao)
- Trạng thái: partial
- Hiện trạng: src/scheduling/solvers.py, slot_generator.py có chọn slot; chưa có booking persisted/notification
- Việc cần làm: Hoàn thiện và kiểm chứng xung đột lịch, đổi lịch và nhắc hẹn.
- Phụ thuộc: 24
- Chấp nhận:
  - [x] `tests/test_booking_reschedule.py` đạt trong regression 59 pass/0 fail.
  - [x] Test chức năng: Slot bận trả lựa chọn khác; điều phối duyệt đổi; reminder nội bộ chỉ gửi khi consent và idempotent.
  - [x] Test an toàn: Reminder chỉ giữ patient ID/kênh/giờ, lịch cũ chỉ đổi sau duyệt; cấp cứu không vào queue thường.

  - [ ] Integration UI/API thật (tác vụ 25): Tạo lịch đã duyệt rồi gây xung đột slot trong dữ liệu thử; UI đề xuất giờ khác, bệnh nhân yêu cầu đổi và lễ tân duyệt, kiểm tra DB không giữ hai lịch chính thức cho cùng yêu cầu. Chạy nhắc theo thời gian kiểm soát bằng kênh thử đã duyệt: có consent mới gửi, đúng người/giờ và không gửi trùng; không dùng mock response để chứng minh giao thông báo. Red-flag chuyển hỗ trợ khẩn.

## Tác vụ 26: Dashboard điều phối và chuyển người thật (Project 258-booking, Nâng cao)
- Trạng thái: partial
- Hiện trạng: chưa thấy dashboard booking trong frontend/app/ hoặc audit đặt lịch trong src/triage/router.py
- Việc cần làm: Hoàn thiện và kiểm chứng dashboard điều phối và chuyển người thật.
- Phụ thuộc: 24, 25
- Chấp nhận:
  - [x] `tests/test_booking_audit.py` đạt trong regression 59 pass/0 fail.
  - [x] Test chức năng: Tính tải/tỷ lệ lịch có nguồn; confidence <0,6 tạo ca người xử lý.
  - [x] Test an toàn: Confidence do rule trả rõ; `receptionist`/admin mới xem dashboard; danh sách ca không trả patient ID.

  - [ ] Integration UI/API thật (tác vụ 26): Tạo lịch đã duyệt, lịch chờ và ca cần người xử lý qua UI/API thật; mở dashboard lễ tân, đối chiếu tải công việc/tỷ lệ đúng khoa với tập thử có kết quả tính sẵn. Ca thiếu dữ kiện/độ tin cậy được chuyển người thật, xử lý rồi tải lại thấy trạng thái/audit bền vững; người trái quyền không đọc chi tiết, báo cáo tổng hợp không lộ PHI hoặc bịa nguồn/độ tin cậy.
  - Bằng chứng nền 04/11/2026: dashboard receptionist UI hiện số lịch chờ, duyệt và tải lại về 0 trên SQLite thật; unit test xác minh ca confidence thấp, aggregate không patient ID và user bị 403. Chưa có browser case đủ ba loại lịch để đối chiếu toàn bộ metric, task giữ partial.

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


## Payload privacy — partial (02/11/2026)

Nguồn: [kế hoạch](PAYLOAD_PRIVACY_PLAN.md), [bằng chứng/giới hạn](PAYLOAD_PRIVACY_IMPLEMENTATION.md). Không thay trạng thái hoặc tiêu chí tác vụ 1–7.

- [x] Shared gate trước NVIDIA chat/embedding; recursive JSON, tool content/arguments, metadata; unknown SDK fields/media bị chặn; retry/stream/fallback-model được HTTP MockTransport kiểm tra, socket ngoài transport bị chặn.
- [x] Short/episodic theo owner; long-term handle cục bộ; pipeline bỏ response cache; sửa followup/rollup; ownerless state không được nhận làm lịch sử người đăng nhập. A/B xen kẽ/đồng thời, summary/export, sync/stream offline trên API/auth DB/Chroma thật riêng có test.
- [x] Gold nhỏ tổng hợp: 14 ca định danh, 9 đối chứng; 0 false-negative/0 false-positive trong tập, 5 ca bị chặn. Không suy rộng ra văn bản tự do.
- [x] Regression: `.\.venv\Scripts\python.exe -m pytest tests/test_payload_privacy.py tests/test_memory_initialization.py tests/test_chat_language.py tests/test_triage_llm.py tests/test_safety_regressions.py tests/test_soap_summary.py tests/test_admin_memory.py -q -o cache_dir=test-results/privacy-pytest-cache --junitxml=test-results/privacy-regression-final.xml` → 70 pass/0 fail/0 skip, 40.47s; 02/11/2026 +07, main f65619f + snapshot SHA256 từng file tại `test-results/privacy-tested-snapshot.json`. Env offline/scheduler-disable, NVIDIA key env rỗng trừ fixture transport tổng hợp.
- [x] Capture API đủ provenance cho mọi nguồn hiện hành, đặc biệt GHO injected thực tế; detector local cho tên/địa chỉ tự do và span-gold mở rộng có nhãn. Giới hạn: chưa có NER tổng quát; miễn trừ tác giả công khai chỉ dùng exact hash của chunk đã xác minh.
  - Đã thêm detector fail-closed cho tên theo quan hệ/họ phổ biến và địa chỉ có cue; 7 ca định danh tự do + 5 đối chứng pass. Chưa có NER tiếng Việt được đánh giá, span-gold lớn hoặc miễn trừ tác giả công khai.
  - Đã thêm manifest/cổng provenance trước generate ở sync và stream; GHO aggregate có file hash; DB thật đã đi qua inject → provenance → sanitizer → MockTransport. Chưa có NER/span-gold lớn hoặc phân loại tác giả công khai tổng quát.
- [x] Audit/phân loại corpus serving và persisted memory theo provenance; quét rule-only không dùng làm bằng chứng không có PII.
  - Audit active index read-only: 25.077 chunk/44 source ID; 360 chunk từ 4 binary khớp nguồn chính thức, 5.223 chunk từ 2 nguồn chưa đối chiếu binary, 19.494 chunk ngoài manifest/scope. Runtime chặn 24.717 chunk sau nếu lọt vào context; chưa rebuild index hoặc audit mọi memory persisted.
  - Serving mới: 452 chunk/4 source; audit độc lập 452/452 khớp file SHA-256, trang, content hash và sidecar. NVIDIA memory 140 record: 0 thiếu owner/0 bị policy chặn; local legacy không serving có 5 record bị chặn, giữ nguyên để rollback.
- [x] Playwright integration 1–7 trên snapshot cuối: 14 pass/0 fail, backend thật + Next production + DB thử cô lập; bằng chứng ở đầu file. Retrieval benchmark index sạch đạt Hit@5 0,933/MRR@5 0,691, 0 source violation; live smoke NVIDIA tổng hợp đạt lúc 16:26 +07 và payload sanitized lưu local.
- [x] Full backend suite trên snapshot cuối. Lượt lỗi 02/11/2026 17:29 +07: 629 pass/8 fail; đã phân loại và sửa. Lượt cuối 20:08 +07, `main` HEAD `f65619f62fe7fc3df477a1669363ef81a2ce1371` + working tree chưa commit, env offline/scheduler-disable: `pytest -q --basetemp=test-results/tmp-full-backend-after-rag-fix-20261102 -o cache_dir=test-results/pytest-cache-full-after-rag-fix` → **635 pass/4 live-provider deselected/0 fail**, exit 0, 784.60s. Bốn live-provider chạy riêng: `test_rag_e2e.py` 3 pass trong lượt 3 pass/1 fail; fail synthetic provenance được giữ fail-closed rồi test seam giới hạn đúng source tổng hợp, `test_tasks_1_7_live_rag.py -m live_provider` rerun 1 pass, 72.77s. NVIDIA health tổng hợp: slot 1 chat/embedding 200 (2048d), slot 2–3 đều 403; không log key.

### Thứ tự privacy tiếp theo — đã chốt 02/11/2026

- [x] Dựng index cô lập chỉ từ WHO Classification, HEARTS-D, WHO PEN và BYT QĐ3319; giữ nguyên index cũ. Bundle deployment 11.205.908 byte có SHA-256 `eca27169...acf7e6`; checkout mới phải restore bundle.
- [x] Audit từng chunk từ binary nguồn: 452/452, SHA-256 file, `source_id`, trang và content hash tái tính; 0 invalid, sidecar SHA-256 `828b3c...42223`.
- [x] Chuyển cấu hình sang index mới bằng cơ chế rollback; startup preflight từ chối config/index/sidecar/source/row không khớp. 2 test preflight pass.
- [x] Chạy retrieval benchmark, citation và câu hỏi ngoài phạm vi; không có hit từ bệnh/source ngoài bốn nguồn.
- [x] Mở rộng span-gold thủ công: 40 positive/12 negative, tách có dấu, không dấu, viết tắt và địa chỉ; policy `2026-11-02.3`, FN=0/FP=0 trong tập.
- [x] Audit persisted memory và quarantine 5 record legacy bằng metadata: 175 record trước/sau, 5 quarantined, 0 xóa; active NVIDIA 140 record, 0 thiếu owner/0 policy-block. GHO injected đã capture qua transport.
- [x] NVIDIA live smoke bằng dữ liệu tổng hợp đã đạt sau sáu cổng, payload làm sạch lưu local.
- [ ] ADA 2024/BYT QĐ5481 và index phiên bản kế tiếp: cả hai binary đã được xác minh. Candidate v2 đã build 1.798 chunk/6 source và audit 0 invalid, nhưng retrieval gate fail lặp lại với Hit@5 0,733/MRR@5 0,567 (miss DQ7/DQ9/DQ12/DQ13). Active pointer giữ index 452 chunk; ADA/QĐ5481 vẫn `eligible_for_next_index` nhưng chưa external-send. Cần review gold/source relevance và sửa retrieval hoặc chunking, sau đó rebuild/benchmark; không hạ ngưỡng để switch.
