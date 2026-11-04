# Hợp đồng API DiaTrack

> Base `http://localhost:8000`, prefix `/v1`. Tài liệu sống ở `/docs` (Swagger). Code: `src/api/main.py`, `src/api/schemas.py`.

> Đọc xong tài liệu này, bạn có thể đăng nhập lấy token, ghi đường huyết, gọi RAG, tạo SOAP và xử lý các lỗi 401, 403 và 422.

## 1. Quy ước chung

| Mục | Nói đơn giản |
|---|---|
| Auth | Gửi `Authorization: Bearer <token>` hoặc cookie `access_token`. Không có/sai → `401`, chưa verify expert → `403` |
| JWT | Token `HS256`, hết hạn 30 phút, refresh 7 ngày (`src/auth/security.py:37`) |
| CORS | Chỉ origin trong `FRONTEND_URL` mới gọi được kèm cookie |
| Lỗi chung | `422` sai kiểu dữ liệu, `401` chưa login, `403` không có quyền, `404` không thấy, `500` lỗi RAG |
| Phân trang | `limit 1..100`, `offset >=0`, kèm `total` |
| Trace | Không header riêng; `trace_id`, `prompt_version` nằm trong body trả về |

RAG (tìm tài liệu rồi sinh câu trả lời có trích dẫn) xem Glossary ở `docs/architecture_diagram.md`.

## 2. Kiểm tra dịch vụ và khám phá API

- `GET /health` (public): trả `{status, version, pdf_count, vector_db_ready}`. Dùng để kiểm tra backend sống chưa.
- `GET /` (public): liệt kê nhóm endpoint (health, query, glucose, soap, auth, reviews, monitors).
- `GET /v1/guidelines/status` (public): số PDF theo nguồn.

## 3. Xác thực — `src/auth/router.py`

Chỉ cần nhớ 3 cặp: `register` tạo user → `login` lấy token → `me` kiểm tra. Expert và `receptionist` tạo ra bị `is_verified=false` chờ admin duyệt nếu không do admin tạo. Token refresh ở `/v1/auth/refresh`, logout ở `/v1/auth/logout`. Admin xem users ở `GET /v1/admin/users`. Chi tiết field xem Swagger `/docs`.

## 4. Truy vấn RAG có HILT — `POST /v1/query`

Hỏi guideline, AI trả lời kèm trích dẫn; điểm thấp thì chuyển bác sĩ duyệt (`pending_review`).

- Request tối thiểu: `{"query": "Dấu hiệu đái tháo đường type 2 là gì?", "top_k": 5}`. Thêm `tone` (strict/friendly/balanced) nếu muốn, `user_id` phải trùng token nếu role=user.
- Response tối thiểu: `{"answer": "...[Source 1]", "status": "answered|pending_review", "trace_id": "abc", "cache_hit": false}`. Đầy đủ còn có `contexts[]`, `audit` (prompt_version, latency), `evaluation` (4 điểm, `is_low_confidence`, `routed_role`).
- Luồng: check quyền/scope → `rag_chat` (retrieve hybrid 0.6 → rerank top3 → privacy/provenance gate → sinh) → `evaluate_rag`; thấp điểm (<3.5) thì tạo review. Response cache cá nhân hiện bị bypass.
- Ngoài-scope ĐTĐ (ví dụ "uống kháng sinh nào?") bị chặn bằng mẫu cứng TRƯỚC khi gọi RAG, không tốn lookup.

## 5. Diabetes — phạm vi sản phẩm hiện hành

Tất cả cần login; user thường chỉ được thao tác trên `user_id` của mình. Các router BP/respiratory/mood còn trong repo là module legacy hoặc hạ tầng dùng thử, không mở rộng phạm vi sản phẩm ngoài đái tháo đường týp 2.

### 5.1 Diabetes — Glucose

- `POST /v1/glucose`: `{"user_id": "...", "value_mgdl": 145, "context": "fasting"}` (`value 20..800`, context: fasting/pre_meal/post_meal_2h/bedtime/random). Trả thêm `classification` (`low` <70, `no_alert` 70–250, `alert_high` >250 và <300, `critical` ≥300), `message`, `anomaly {spike|trend|none}`, `follow_up_questions[]`. `no_alert` chỉ nghĩa là chưa chạm ngưỡng cảnh báo của hệ thống, không xác nhận đạt mục tiêu cá nhân. GET log cũ tính lại nhãn từ giá trị đo; dữ liệu gốc không bị sửa.
- Ngưỡng cảnh báo sản phẩm: <70 cần liên hệ y tế, >250 cần liên hệ bác sĩ, ≥300 cần liên hệ y tế ngay; dấu hiệu nặng gọi 115. Mốc xét nghiệm lúc đói ≥126 và OGTT 2 giờ ≥200 là tiêu chuẩn chẩn đoán trong phòng xét nghiệm, không dùng để chẩn đoán từ một lần đo tại nhà. Xem nguồn và giới hạn từng mốc ở `docs/project_requirements.json#scope_rules.threshold_evidence`.
- `GET /v1/glucose/{user_id}?limit=50&days=14`: trả `logs[]` với `classification` và `message` được tính lại từ giá trị gốc, cùng `stats` (trung bình, streak) + `should_escalate` (có số đo <70 hoặc ≥300 trong các log gần nhất). Nhãn hiển thị cũ không tự kích hoạt chuyển ca.
- `POST /v1/voice/transcribe`: trả `parse` (giá trị và bối cảnh), `measurement_time` (ISO 8601 +07:00 khi nghe rõ giờ và buổi đo) và cảnh báo red-flag. Luồng voice hỏi lại giờ đo nếu thiếu hoặc mơ hồ; chỉ gọi `POST /v1/glucose` với `measured_at` sau khi bệnh nhân xác nhận. Không tự gán giờ hiện tại cho bản ghi voice. Khi mất micro hoặc STT, người dùng có thể nhập thủ công.
- STT mặc định là mock xác định cho test. Runtime local chỉ dùng Whisper thật khi đặt `VOICE_STT_PROVIDER=whisper`; cần ffmpeg và model trong cache. Transcript không rỗng không đồng nghĩa số được nhận đúng, vì vậy giá trị và thời điểm luôn phải qua bước xác nhận.

### 5.2–5.5 Module legacy ngoài phạm vi

`/v1/bp`, `/v1/respiratory`, `/v1/mood` và `/v1/vitals` có thể còn được wire để tương thích hoặc thử nghiệm. Không dùng chúng làm chức năng DiaTrack hiện hành; câu hỏi ngoài phạm vi phải trả đúng `scope_rules.out_of_scope_reply`.

## 6. SOAP trước buổi khám — `POST /v1/soap/generate` + `/markdown`

- Request tối thiểu: `{"user_id": "...", "days": 14, "language": "vi", "disease": "diabetes"}` (`days 1..90`).
- Response tối thiểu: `{"soap": {"subjective": "...[Xem log #3]", "objective": "...", "assessment": "chưa thể kết luận HbA1c từ nhật ký tự đo...[Xem log #3]", "plan": ""}, "period": "..."}`. **P luôn `""`** + placeholder mờ cho bác sĩ; S/O/A có audit link. A mô tả dữ liệu đã ghi, không suy HbA1c hoặc kết luận đạt mục tiêu từ đường huyết tự đo.
- `/markdown` trả `text/plain` đã format sẵn.

## 7. Quy trình duyệt HILT — `src/reviews/router.py`

### Workflow SOAP, dinh dưỡng và đặt lịch

- `/v1/soap/drafts`: bệnh nhân tạo nháp từ transcript; doctor/admin mở, sửa, nhập Plan và ký. Bản đã ký bất biến; `/export` chỉ xuất bản đã ký.
- `/v1/nutrition/profile`, `/meal-plans`, `/meal-logs`: hồ sơ dị ứng thuộc bệnh nhân; số dinh dưỡng lấy từ dataset có nguồn, món không biết trả `nutrition=null`; specialist/doctor/admin duyệt meal plan.
- `/v1/bookings/suggest`, `/hold`, `/{id}/confirm`: bệnh nhân tìm slot, giữ chỗ và xác nhận. Chỉ `receptionist`/admin duyệt, chạy reminder và xem `/coordination/dashboard`; unique index ngăn hai lịch đang hiệu lực dùng cùng slot.

### Triage có cấu trúc — `POST /v1/triage`

Gửi `{"message":"tê chân, mắt mờ", "structured":true, "latest_glucose_mgdl":180, "symptom_onset":"hai ngày trước"}`. Nếu thiếu triệu chứng, số đo hoặc thời điểm bắt đầu, API trả `followup_question` và `review_status=collecting`. Khi đủ dữ kiện, API trả `proposed_priority` (`routine|soon|emergency`), `rationale`, `source` và `review_status=pending_clinician_review`; không trả lịch/hướng xử trí thường trước duyệt. Dấu hiệu red-flag hoặc số đo <70/≥300 mg/dL trả cảnh báo 115 ngay. `source` trỏ tới protocol mô phỏng trong `docs/project_requirements.json`, không phải trích dẫn guideline lâm sàng đã kiểm chứng.

Red-flag được kiểm trước từ chối ngoài phạm vi, gồm `hypo_severe`, `hyperglycemia_danger`, `foot_infection`, `cardio_stroke`; API trả `emergency=true`, `red_flag_type`, `message` có 115 và danh sách bác sĩ rỗng. Số đo khẩn trong `latest_glucose_mgdl` cũng đi đường cảnh báo này. Nếu không có red-flag mà câu hỏi ngoài phạm vi, `message` là đúng `scope_rules.out_of_scope_reply` và không gợi ý lịch.

`POST /v1/query` với `require_doctor_review=true` luôn chuyển bản diễn giải sang bác sĩ (`pending_review`, `review_id`); chỉ trả thông báo chờ, không trả bản nháp hoặc evaluation nội bộ. Yêu cầu bắt buộc duyệt chuyển trực tiếp tới bác sĩ sau RAG/kiểm tra nguồn, không phụ thuộc bộ chấm AI; các câu hỏi khác giữ bộ chấm tự động hiện hành. Dấu hiệu khẩn và ngoài phạm vi vẫn đi đường an toàn trước RAG.

Bác sĩ đã xác minh xem `GET /v1/reviews?status=pending`, chi tiết/nguồn/chỉ số tại `GET /v1/reviews/{id}`, và quyết định qua `POST /v1/reviews/{id}/decide` với `{decision: approved|rejected|revised, final_answer?, expert_notes?}`. `approved` công bố nguyên bản; `revised` bắt buộc nội dung sửa không rỗng. Review chỉ được quyết định một lần; lặp quyết định trả 400. Endpoint tương thích `/decision?decision=...` áp cùng quyền. Review bắt buộc bác sĩ chỉ cho doctor/admin duyệt; bệnh nhân, điều dưỡng, dược sĩ/chuyên gia sai quyền và bác sĩ chưa xác minh nhận 403.

Bệnh nhân xem yêu cầu của mình tại `/v1/reviews/me`, `/v1/reviews` và `/v1/reviews/{id}`; chỉ nhận thông tin trạng thái/câu hỏi và `final_answer` sau quyết định, không nhận draft, evaluation, ghi chú nội bộ hay vitals. Truy cập chi tiết của bệnh nhân khác trả 403. `/v1/query/history` và history trong `/reviews/me` ẩn answer khi pending; sau duyệt trả toàn văn cuối (`history.status=approved`, kể cả khi review là `revised`). UI `/my/reviews` tải lại hoặc polling để cập nhật nội dung cuối; không cắt câu trả lời ở 300 ký tự. Tài khoản bác sĩ demo và dữ liệu thử không thay thế duyệt y khoa thực tế.

## 8. Giám sát nguồn — `src/monitors/router.py` (13 route)

Chỉ cần nhớ: `GET /v1/monitors/status` xem tổng quan; `POST /v1/monitors/check/guidelines?source_key=gold` (specialist) và `check/safety` (pharmacist) để quét bản mới; `GET .../guidelines` + `POST .../guidelines/{gid}/decision` để duyệt; alerts tương tự cho dược sĩ; `cleanup-superseded` (admin) dọn bản cũ >30 ngày.

## 9. Quản trị tracing và prompt

Tracing (`src/admin/tracing_router.py`): `GET /v1/admin/traces` lọc + `GET /v1/admin/traces/{trace_id}` xem spans/chunks/ragas + `POST .../ragas` chấm lại + `DELETE .../expired` dọn >30 ngày. Prompts (`src/admin/prompt_router.py`): xem/tạo/duyệt version prompt theo tone, `dry-run` chạy 5 câu golden để so sánh.

## 10. Ví dụ cURL

Thử 3 bước sau khi có token (`TOKEN` từ login):

```bash
curl -X POST http://localhost:8000/v1/auth/login -H "Content-Type: application/json" -d '{"username":"demo","password":"demo123"}'
curl -X POST http://localhost:8000/v1/query -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"query":"Nguong chan doan dai thao duong theo WHO?","top_k":5}'
curl -X POST http://localhost:8000/v1/glucose -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"user_id":"<id>","value_mgdl":145,"context":"fasting"}'
```

Thêm SOAP và monitors xem Swagger `/docs` (không paste dài ở đây để file gọn).

## 11. Mã lỗi và cách xử lý

- `422`: sai kiểu/miền — ví dụ `value_mgdl` ngoài 20..800, `top_k` ngoài 1..20, `days` ngoài 1..90. Cách sửa: đọc `detail` trả về, sửa field đó.
- `401`: thiếu/hết hạn token → login lại, gắn `Authorization: Bearer`.
- `403`: user thao tác nhầm `user_id` người khác, hoặc thiếu role (cần specialist/pharmacist/admin), hoặc expert chưa verify.
- `400`: thao tác không hợp lệ (review đã duyệt rồi...). `500`: lỗi RAG — kiểm tra cấu hình NVIDIA, bundle index, provenance gate và log không chứa dữ liệu nhạy cảm.

### Tự kiểm tra

- [ ] Login + gọi 3 API query/glucose/soap bằng Swagger thành công.
- [ ] Kể được khác biệt 401 vs 403 vs 422 bằng 1 câu mỗi loại.
- [ ] Chỉ ra file schema và router của 1 endpoint bất kỳ.
