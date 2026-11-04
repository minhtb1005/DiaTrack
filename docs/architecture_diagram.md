# Kiến trúc hệ thống DiaTrack

> Nguồn chính: `src/shared/config.py`, `src/chat/rag_pipeline.py:36`, `src/shared/observability/tracing_db.py:32`, `src/shared/indexer.py:98`, `src/monitors/*`, `frontend/app/**`.

> Đọc xong tài liệu này, bạn có thể vẽ lại luồng từ bệnh nhân đến bác sĩ, chạy backend và frontend, đồng thời giải thích RAG, HILT, FQG và SOAP cho thành viên mới.

## 0. Thuật ngữ dùng chung

- **RAG (Retrieval-Augmented Generation):** trả lời dựa trên tài liệu WHO/BYT đã lưu, kèm trích dẫn, để không bịa.
- **Response cache:** API còn giữ field tương thích, nhưng pipeline cá nhân hiện không đọc/ghi cache vì memory thay đổi theo lượt và cache cũ không có owner.
- **BM25:** tìm kiếm theo từ khóa (đếm từ khớp), hợp với mã bệnh, tên thuốc.
- **Rerank:** chấm lại top kết quả bằng mô hình CrossEncoder rồi chỉ giữ top 3 tốt nhất.
- **Chroma:** kho vector lưu chunks đã embedding, hỏi là tìm đoạn gần nghĩa nhất.
- **SOAP (Subjective/Objective/Assessment/Plan):** mẫu ghi chú bác sĩ chuẩn 4 phần; ở đây P để trống cho bác sĩ quyết.
- **FQG (Follow-up Questions):** 2-3 câu hỏi gợi ý ngữ cảnh (ăn ngọt? quên thuốc?) trước khi escalate; hội thoại nhiều vòng là future-work.
- **HILT (Human-In-The-Loop):** AI chấm điểm câu trả lời, điểm thấp (<3.5/5) thì chuyển cho bác sĩ duyệt, không trả lời liều.

Chi tiết đo lường → xem `docs/evaluation.md`; dữ liệu/corpus → xem `docs/data_contract.md`.

## 1. Tổng quan hệ thống

Luồng chính gồm năm bước:

```
[Patient log glucose] -> [API + Anomaly check] -> [RAG + Memory] -> [FQG truoc escalate] -> [Doctor: sparkline 90d + SOAP]
```

- Patient nhập chỉ số → `POST /v1/glucose` kiểm tra spike >250/<70 và trend 3 ngày.
- Hỏi đáp → `POST /v1/query` kiểm tra scope → hybrid BM25+vector → rerank → privacy/provenance gate → NVIDIA NIM.
- Memory 3 tầng (`src/shared/memory/`): short 500 tokens + episodic 300 tokens + long-term 3 facts; cuối tuần gom thành 1 fact/tuần.
- Doctor xem `previsit`: sparkline 90 ngày chấm đỏ anomaly (30%) + SOAP text (70%), mỗi nhận định có `[Xem log #id]`; bác sĩ còn có hàng đợi `/expert/patients` ưu tiên critical → watch → safe. Heuristic xu hướng demo không tự nâng mức chuyển ca.
- Kiến trúc module hóa đa chỉ số (BP/HR/SpO2) nhưng MVP tập trung sâu Glucose làm POC.

<details>
<summary>Mermaid chi tiết cũ (click để mở, không cần học thuộc)</summary>

Mermaid gốc 4 sơ đồ đã thu gọn. Muốn xem full thì `git log -- docs/architecture_diagram.md`. Tóm tắt: Client (Next.js) → FastAPI (`src/api/main.py` — composition root, router theo service ở `src/<service>/router.py`) → RAG Pipeline (`src/chat/rag_pipeline.py:36`) → Storage (Chroma + `metadata/*.db`) + Agents giám sát guideline.

</details>

### Ba luồng nghiệp vụ chính

- **Track A — Hỏi đáp RAG + HILT:** `POST /v1/query` → scope guard → retrieve → rerank → privacy/provenance gate → sinh câu trả lời → `evaluate_rag`; câu bắt buộc duyệt hoặc độ tin cậy thấp thành `pending_review`. Xem contract ở `docs/api_contract.md`.
- **Track B — Theo dõi đường huyết + Anomaly:** `POST /v1/glucose` → lưu log → `anomaly_detector` (ngưỡng cứng + trend heuristic demo) → banner + FQG ở tracker. Ngưỡng an toàn lấy từ `project_requirements.json#scope_rules`.
- **Track C — Pre-visit SOAP cho bác sĩ:** `POST /v1/soap/generate` → S gom notes FQG, O số đã ghi, A mô tả dữ liệu nhưng không suy HbA1c hay kết luận đạt mục tiêu từ đường huyết tự đo, **P = ""** cho bác sĩ quyết định.

### Bản đồ module

- `src/api/main.py` — composition root, chỉ wire router + middleware; endpoint thật nằm ở `src/<service>/router.py` + schema ở `src/<service>/schemas.py`.
- `src/chat/` — service RAG: `rag_pipeline.py` luồng chính, `retriever.py` hybrid BM25+vector, `generator.py` LLM, `router.py` `/v1/query` (+ stream). Response cache không dùng cho pipeline cá nhân hiện hành.
- `src/diabetes/` — `glucose_tracker.py`, `anomaly_detector.py`, `scope_guard.py`, `soap_summary.py`, `followup_notes.py`.
- `src/triage/` — `triage_nlu.py`, `red_flag.py`, `triage_events.py`; `src/scheduling/` — `slot_generator.py`, `solvers.py`, `synthetic_roster.py` (gọi in-process từ triage).
- `src/vitals/` — `bp_tracker.py`, `respiratory_tracker.py`, `mood_tracker.py` (base chung `base_tracker.py`).
- `src/shared/` — hạ tầng dùng chung: `config.py`, `memory/`, `observability/tracing_db.py`, `indexer.py`, `embedding/`, `models/`, `evaluation.py`.
- `frontend/app/tracker`, `frontend/app/previsit`, `frontend/app/admin/tracing` — 3 màn hình chính.

## 2. Luồng dữ liệu — Guideline & Safety (5 bước)

1. Crawler HEAD kiểm tra etag/last-modified của nguồn (ADA, WHO, BYT...).
2. Có bản mới → tải về `data/raw/staging/`, kiểm tra `%PDF`, dedup sha256.
3. LLM tóm tắt thay đổi tiếng Việt → ghi `guideline_versions` trạng thái `pending_review`.
4. Chuyên gia duyệt trên UI → file move sang `data/raw/pdfs/`, bản cũ thành `superseded`.
5. Reindex vào thư mục version mới, audit provenance rồi mới đổi cấu hình serving. FDA alerts tương tự nhưng chỉ cảnh báo, không index.

## 3. Sequence HILT — RAG Query

1. API nhận `{query, top_k=5, user_id}` → gọi `rag_chat`.
2. Hybrid retrieve (BM25 + vector, alpha 0.6) → rerank top 3; response cache bị bỏ qua cho request cá nhân.
3. Context và memory đi qua privacy/provenance gate trước khi NVIDIA sinh câu trả lời kèm trích dẫn `[Source X]`.
4. `evaluate_rag` chấm, metric nào <3.5 thì tạo review, gán bác sĩ/dược sĩ/chuyên gia, trả `pending_review`.

**Spans trace:** vẫn có `cache_check` để giữ telemetry/API tương thích, sau đó `retrieve_context → rerank_contexts → build_llm_input → generate_answer → update_memories → format_answer`; không có cache hit/put cho pipeline cá nhân hiện hành.

## 4. ERD — 6 DBs

| DB | File | Bảng chính để nhớ |
|---|---|---|
| Metadata | `metadata/metadata_store.db` | metadata ingestion cũ; số row phụ thuộc artifact local |
| Vector | `NVIDIA_PDF_DB_DIR` | index NVIDIA versioned; startup kiểm manifest, source hash, sidecar và Chroma rows |
| Auth | `metadata/auth.db` | `users`, `review_requests`, `notifications` |
| Tracing | `metadata/tracing.db` | `traces/spans/span_chunks/prompts/ragas/feedback`, giữ 30 ngày |
| Monitoring | `metadata/monitoring.db` | `monitored_sources` 10 rows, `guideline_versions`, `safety_alerts` |
| Vitals | `metadata/vitals.db` | logs theo `disease_type` |

## 5. Khoảng trống cần xử lý trước production

| # | Gap | Nói đơn giản |
|---|---|---|
| 1 | BYT scrape chưa có bằng chứng HTML live hiện hành | Có thể parse sai trang luật |
| 2 | FDA chưa backoff 429 | Có thể lỡ recall quan trọng |
| 3 | Hai binary ADA 2024/BYT QĐ5481 chưa được duyệt vào index serving | Không dùng chúng làm nguồn retrieval cho tới khi hash/provenance đạt |
| 4 | Live NVIDIA và benchmark phụ thuộc artifact/key | Kết quả offline không chứng minh chất lượng live |

## 6. Tham chiếu nhanh

- Code: `src/shared/config.py:240` hằng số, `src/chat/rag_pipeline.py:36` luồng, `src/shared/observability/tracing_db.py:32` schema, `src/shared/indexer.py:98` reindex, `src/monitors/scheduler.py` lịch 02:00/03:00.
- **Why business (3-5 dòng, chi tiết ở `docs/benchmark.md` phụ lục):** FreeStyle Libre bán 2-4M VND/bộ chứng minh người dân chịu chi cho monitoring; BHYT chi trả telehealth từ 1/7/2025 + VN chỉ 14 bác sĩ/10k người nên AI triage có giá trị; hướng bán B2B2C cho phòng khám thay vì thu phí lẻ từng bệnh nhân.
- **Run demo 5 phút:**
  - Backend: khôi phục bundle theo `deployment/README.md`, cấu hình NVIDIA rồi chạy `.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload --port 8000`.
  - Frontend: `cd frontend && npm install && npm run dev`, mở tracker log 260 → xem banner, mở previsit xem sparkline + SOAP.
- **Lưu ý y khoa:** demo-only, không chẩn đoán mới; SOAP không suy HbA1c hoặc kết luận đạt mục tiêu từ đường huyết tự đo.

### Tự kiểm tra

- [ ] Vẽ lại 5 hộp không nhìn tài liệu.
- [ ] Giải thích được RAG, privacy/provenance gate và HILT bằng 1 câu mỗi cái.
- [ ] Chạy được demo và chỉ ra file code của từng bước.
- [ ] Nói được tại sao P để trống và QĐ3192 không dùng cho ĐTĐ.
