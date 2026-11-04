# Kiểm soát dữ liệu gửi ra ngoài — triển khai và bằng chứng 02/11/2026

Trạng thái: **partial; chưa xác minh đầy đủ toàn kế hoạch**. Không đổi nghiệm thu 1–7.

## Thay đổi

- `src/shared/privacy.py`: policy local version `2026-11-02.2`, Unicode NFC, định danh có mẫu rõ, trường định danh có cấu trúc, known-identity ContextVar từ auth; chặn identity mơ hồ, tên theo quan hệ/họ phổ biến và địa chỉ có cue, ký tự vô hình, media, object không phải JSON và SDK kwargs ngoài danh sách. Không thay glucose/đơn vị/phủ định trong đối chứng đã test.
- `src/shared/corpus_provenance.json` và `src/shared/corpus_provenance.py`: manifest hash và cổng fail-closed ngay trước generate ở sync/stream. Context chỉ được gửi khi source được duyệt, binary đã đối chiếu và file/index hiện hành khớp SHA-256; memory owner-isolated là ngoại lệ có chủ đích nhưng vẫn đi qua redaction payload.
- `scripts/audit_corpus_provenance.py`: mở SQLite read-only, chỉ xuất hash-status, source ID công khai và số đếm; không xuất document text.
- `src/shared/nvidia.py`: gate trước embeddings và trước SDK chat, trước retry/đổi model/stream; lỗi provider không đưa response body vào lỗi ứng dụng. Không chỉnh Authorization hoặc model như dữ liệu người bệnh. Sửa nhánh overload fallback trước đây không tới được.
- Memory short/episodic theo owner, ownerless legacy không được nhận vào prompt người đăng nhập; long-term handle cục bộ mỗi request, kiểm tra owner cả retrieval/profile; followup/weekly-rollup dùng owner. Không xóa legacy hoặc rebuild index.
- Bỏ đọc/ghi response cache trong pipeline cá nhân: cache cũ không có owner và ngữ cảnh memory đổi sau mỗi lượt. API giữ `cache_hit=false` và shape thống kê hiện có. Đổi này làm tăng số request/độ trễ khi hỏi lại.
- Judge, SOAP, rollup, retriever trim và monitor summary làm sạch trước phần truncate liên quan. PrivacyError không được chuyển thành thành công LLM/heuristic ở các caller đã sửa; red-flag deterministic vẫn chạy trước RAG.
- `scripts/audit_payload_privacy.py`: SQLite read-only, chỉ đường dẫn được chọn, không fallback; report hash ID, loại/số phát hiện, provenance do người chạy khai báo; không xuất giá trị gốc hoặc đường dẫn nguồn. BLOB không được giải mã, được ghi `uninspected_blob`.

## Ma trận kiểm tra request HTTP offline

| Nguồn/nhánh | Request đích | Bằng chứng |
|---|---|---|
| query/document/metadata/short/episodic/long/judge-answer/GHO dưới dạng messages tổng hợp | chat sync/stream | `test_chat_sources_retry_and_stream`, 429 rồi retry; không marker email trong HTTP JSON |
| query/document | embeddings query/passage | `test_embedding_boundary`, 401 rồi retry |
| HARD quá tải | chat LIGHT | `test_hard_fallback_is_sanitized`, hai 503 rồi LIGHT |
| unknown kwargs/media/uncertain address | không gửi | các test policy: 0 HTTP request |
| auth → SQLite riêng → index Chroma riêng → short/episodic/long → SDK | embeddings/chat/judge, API sync/SSE | `test_api_index_memory_transport_isolation`: A/B xen kẽ và đồng thời, summary/export, không fallback index repo, không marker người khác |
| provider failure | lỗi ứng dụng | không echo provider body/payload |

Hàng GHO đầu tiên chỉ kiểm tra nội dung có nhãn GHO tại gate, **chưa kiểm tra toàn luồng GHO injected thực tế**. Không gọi provider thật trong các test này. `socket.connect` bị chặn trong file privacy test; MockTransport thay đúng HTTP transport SDK/httpx.

## Bằng chứng

- Branch `main`, HEAD `f65619f62fe7fc3df477a1669363ef81a2ce1371` + diff chưa commit; hash từng file đã test: `test-results/privacy-tested-snapshot.json` (local).
- Lệnh và env: xem mục Payload privacy trong `TASKS.md`. Kết quả cuối: **70 pass, 0 fail, 0 skip; 40.47s**, ngày 02/11/2026 +07; XML `test-results/privacy-regression-final.xml`.
- Gold tổng hợp: 14 positive, 9 negative; 5 ca chặn; 0 FN/0 FP **chỉ trong tập này**. Report metric-only `test-results/privacy-gold-metrics.json`.
- Lỗi lịch sử đã xử lý: lượt đầu 24 pass/3 fail do fixture httpx.Client bị thay bằng function; sửa subclass. Lượt regression 57 pass/8 fail do test import xóa sys.modules làm mock admin trỏ module cũ; sửa restore. Sau đó 66 rồi 69 pass. Hai lượt 69 pass/1 fail phát hiện ID regex nhận nhầm chuỗi glucose nhóm ba; đã sửa giữ đơn vị mg/dL/mmol/L và thêm đối chứng. Lượt cuối 70 pass. Các lượt trước code cuối chỉ là lịch sử.
- Không dùng skip-judge để chứng minh chất lượng. Không chạy live/benchmark/browser trong mốc này.

## Giới hạn còn mở

1. Bộ rule không đủ nhận diện mọi tên/địa chỉ tự do, tên không nhãn hoặc cách viết lạ. Chưa có local NER được đánh giá. Tên tác giả công khai trùng mẫu người bệnh có thể bị chặn; chưa có provenance đáng tin để miễn trừ. Không tuyên bố ẩn danh tuyệt đối hay đủ điều kiện chạy dữ liệu bệnh nhân thật.
2. Cần mở rộng gold có span labels và capture API đủ mọi nguồn, kể cả injected GHO và các job nền. Kiểm thử A/B dùng dữ liệu tổng hợp; chưa kiểm tải nhiều session cùng owner.
3. Audit corpus rule-only hoàn tất: 26 DB, 1.371.478 rows, 418.528 flagged rows, 0 lỗi đọc; đây là candidate có dữ liệu trùng/URL công khai, không phải số lượng PII thật. Report local tại `test-results/privacy-corpus-audit.json`; provenance đầu vào là `unknown`, không suy từ filename. Snapshot scanner lúc bắt đầu khác rule bổ sung sau đó; report không chứng minh policy cuối hoặc toàn corpus đã sạch. Không tự sửa/xóa/rebuild index. File ngoài SQLite, BLOB và memory ở process khác chưa được bao phủ.
4. Chưa benchmark retrieval/answer sau thay đổi nội dung embedding, chưa live NVIDIA, chưa Playwright 1–7 hay full backend suite. Các cổng này vẫn mở; không đánh dấu done.
5. Dữ liệu sức khỏe đã giảm định danh vẫn có nguy cơ tái nhận diện; chính sách lưu giữ của provider chưa được đánh giá.

## Xác minh tên, địa chỉ và nguồn dữ liệu — 02/11/2026 15:56 +07

- Active index: 25.077 chunk, 44 source ID. Chỉ **360** chunk thuộc 4 source có local binary khớp SHA-256 với binary tải từ trang chính thức (WHO Classification, WHO HEARTS-D, WHO PEN, BYT QĐ3319). **5.223** chunk thuộc ADA 2024/BYT QĐ5481 chưa đối chiếu được binary và **19.494** chunk ngoài manifest/scope; cả 24.717 chunk bị cổng runtime từ chối nếu được chọn làm context.
- ADA 2024 chỉ xác minh trang/tên ấn phẩm; BYT QĐ5481 chỉ xác minh trang công bố do redirect tải hỏng. Hai source giữ `approved_for_external_send=false`; không suy provenance từ filename.
- `pytest tests/test_payload_privacy.py ...` → **52 pass, 0 fail, 0 skip, 38.05s**; JUnit `test-results/privacy-freeform-provenance.xml`. Test gồm API/auth/SQLite/Chroma/memory thật riêng, SDK MockTransport và xác nhận payload bị chặn tạo 0 request provider.
- `py_compile` 4 file và `git diff --check` exit 0 lúc 15:56:40 +07; diff-check chỉ cảnh báo CRLF có sẵn.
- Kết luận giới hạn: cổng chứng minh hành vi fail-closed trên các mẫu và nguồn đã liệt kê, không chứng minh nhận diện mọi tên/địa chỉ tự do hoặc ẩn danh tuyệt đối. Chưa dùng dữ liệu bệnh nhân thật và chưa gọi NVIDIA live.

## Quyết định triển khai tiếp theo

- Không tiếp tục dùng index hiện tại làm index vận hành: 24.717/25.077 chunk bị provenance gate chặn. Giữ nguyên index này chỉ để rollback/đối chứng, không xóa hoặc sửa tại chỗ.
- Index thay thế phải được dựng cô lập chỉ từ 4 nguồn binary đã xác minh. Mỗi chunk phải truy ngược được tới SHA-256 file, `source_id`, trang và hash nội dung được tái tính từ binary; metadata cũ không phải nguồn sự thật.
- Chuyển cấu hình phải có rollback; sau chuyển phải chạy benchmark retrieval, citation và ca ngoài phạm vi để chứng minh không lấy tài liệu bệnh khác.
- Sau đó mới mở rộng gold tên/địa chỉ, audit persisted memory và GHO injected. NVIDIA live smoke là cổng cuối, chỉ dùng dữ liệu tổng hợp và chỉ chạy khi toàn bộ cổng offline trước đó đạt.
- ADA 2024 và BYT QĐ5481 vẫn `approved_for_external_send=false` cho tới khi binary chính thức khớp SHA-256; không whitelist tạm.

## Index sạch và kiểm tra live — 02/11/2026 16:26 +07

- Serving mới: `embeddings/pdf_db_nvidia_verified_20261102/hybrid_section_semantic`; index cũ giữ nguyên. Rollback bằng `NVIDIA_PDF_DB_DIR=<repo>/embeddings/pdf_db_nvidia` cùng manifest cũ, không rebuild/xóa dữ liệu.
- Builder chỉ đọc bốn PDF có binary hash khớp, chunk trực tiếp theo trang và ghi source/content/chunk hash. Audit độc lập đạt 452/452 chunk, 0 invalid, vector 2.048 chiều; sidecar SHA-256 `828b3c2448f16ffe088ab7b9743dc0488479cdc9b22eeff573f9e47209744223`.
- Benchmark 15 câu tổng hợp: Hit@5 0,9333; MRR@5 0,6911; 0 source ngoài allowlist. Hen phế quản/COPD/trầm cảm đều bị scope guard chặn trước RAG.
- Gold local: 26 ca tên/địa chỉ dương tính và 10 đối chứng, gồm có dấu, không dấu, viết tắt và địa chỉ tự do. Đây vẫn là rule-gold nhỏ.
- Memory: NVIDIA serving 140 record, 0 thiếu owner/0 policy-block. Local legacy 175 record có 5 policy-block nhưng không serving; OpenAI legacy 114 record, 0 policy-block. Không xóa để giữ rollback.
- GHO dùng DB thật qua inject → provenance → sanitizer → MockTransport. Snapshot cuối: **83 pass/0 fail/0 skip, 35,61s**; JUnit `test-results/privacy-verified-index-final.xml`; pycompile và diff-check đạt.
- Live smoke cuối `2026-11-02T16:26:05+07`, câu tổng hợp, provenance valid, nhận answer. Exact sanitized payload local: `test-results/verified-live-smoke-payload.json`, không chứa key.
- Lịch sử lỗi giữ lại: hai lượt đầu dừng trước chat do ký tự vô hình/prompt ghép; lượt ba chat thành công nhưng lỗi namespace Pydantic sau response. Lượt cuối hoàn tất report.

## Deployment, kiểm tra trước khi chạy, gold set và cách ly dữ liệu cũ — 02/11/2026 21:27 +07

- Bundle `deployment/verified-rag-assets-20261102.zip` chứa đúng index 452 chunk và bốn PDF nguồn, SHA-256 `eca27169aa713db004dd2247e35fefdd54fa4289c868fa9916b508d1e4acf7e6`, 11.205.908 byte. Startup gọi `validate_serving_index()` và fail khi config directory, sidecar, source hash hoặc Chroma row không khớp.
- Span-gold `data/evaluation/privacy_span_gold_vi.json`: 40 positive + 12 negative, review thủ công, tách tên có dấu/không dấu/viết tắt và địa chỉ có dấu/không dấu. Lượt đầu phát hiện 1 FN + 1 FP; policy `2026-11-02.3` sửa root cause, lượt cuối FN=0/FP=0 trong tập. Không suy rộng thành NER đầy đủ.
- `scripts/quarantine_legacy_memory.py --apply`: 175 record trước/sau, 5 record policy-block được gắn metadata quarantine, 0 xóa; dry-run sau apply thấy 5/5 đã quarantine. Kho legacy không serving; active NVIDIA vẫn 140 record, 0 thiếu owner/0 policy-block.
- `pytest tests/test_corpus_startup_preflight.py tests/test_payload_privacy.py tests/test_safety_regressions.py ...` → 89 pass/0 fail, 50.47s. Audit index sau chỉnh lifecycle: PASSED, 452 chunk, 0 invalid; diff-check và pycompile đạt.
- QĐ5481: bản đính kèm cổng Sở Y tế Đồng Nai có 77 trang; binary SHA-256 `305fc9c51d54418f5798e7691d59f94d24545e0dd728945e2225794730694486`; normalized text SHA-256 `601e7e...0148f` khớp bản local cũ. Đánh dấu `eligible_for_next_index`, chưa external-send trước rebuild/switch.
- ADA 2024: tải binary qua URL có chữ ký lấy trực tiếp từ nút `Standards of Care (PDF)` trên issue page ADA. Binary chính thức và file local cùng 71.612.971 byte, 328 trang và SHA-256 `bdc60c919f5d596092c1962fde675a126938e128b4fabb763aef99ff1fbf0a93`; metadata `PDFsam Basic v4.2.8`/`SAMBox 2.3.0` tồn tại ngay trên bản ADA phân phối. Đánh dấu `binary_match=true`, `eligible_for_next_index=true`; vẫn chưa external-send trước rebuild/audit/switch.
