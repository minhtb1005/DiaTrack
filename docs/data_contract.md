# Hợp đồng dữ liệu — DiaTrack

> Nguồn hiện hành: `src/shared/config.py`, `src/shared/corpus_provenance.json`, `src/shared/corpus_provenance.py`, `scripts/build_verified_corpus_index.py` và `deployment/README.md`.

> Đọc xong tài liệu này, bạn có thể phân biệt corpus lưu trên đĩa với corpus đang phục vụ, giải thích cổng provenance và kiểm tra index trước khi chạy API.

## 1. Phạm vi dữ liệu

DiaTrack chỉ phục vụ đái tháo đường týp 2. Dữ liệu tăng huyết áp, hô hấp hoặc tâm thần còn trong repo là dữ liệu legacy/thử nghiệm; chúng không tự mở rộng phạm vi sản phẩm. `docs/project_requirements.json#scope_rules` là nguồn quyết định phạm vi và câu từ chối.

Các DB auth, vitals, tracing và monitoring nằm trong `metadata/`. Không dùng DB/index sản phẩm cho test có ghi; fixture phải trỏ tới bản sao hoặc thư mục thử cô lập.

## 2. Corpus lưu trên đĩa và corpus đang phục vụ

`data/raw/pdfs/` có thể chứa nhiều tài liệu hơn index serving. Việc file tồn tại trên đĩa không có nghĩa tài liệu được phép retrieval hoặc gửi ra provider.

Index serving hiện hành lấy từ `NVIDIA_PDF_DB_DIR`, mặc định là `embeddings/pdf_db_nvidia_verified_20261102`. Manifest hiện duyệt bốn binary cho external send:

| Source ID | Vai trò |
|---|---|
| `who_classification_diabetes_2019` | Phân loại đái tháo đường của WHO |
| `who_hearts_d_diabetes_2020` | Quản lý đái tháo đường trong HEARTS-D |
| `who_pen_2020_ncd` | Can thiệp NCD tuyến ban đầu; chỉ dùng phần phù hợp phạm vi |
| `byt_qd3319_hd_chandoan_dtd_type2_2017` | Hướng dẫn đái tháo đường týp 2 của Bộ Y tế |

ADA 2024 và BYT QĐ5481 có binary đã đối chiếu trong manifest nhưng `approved_for_external_send=false`; chúng là ứng viên cho index tiếp theo, chưa thuộc active index. QĐ3192 và tài liệu các bệnh khác không dùng để trả lời như nguồn DiaTrack.

GHO là tool aggregate riêng (`data/processed/gho_stats.db`), không phải PDF chunk. Hash và quyền gửi của tool cũng được khai báo trong manifest.

## 3. Embedding và kho vector

Runtime chat chỉ hỗ trợ NVIDIA. Embedding mặc định dùng `nvidia/nemotron-3-embed-1b`, 2048 chiều; local `all-MiniLM-L6-v2`, 384 chiều chỉ là lựa chọn cấu hình cục bộ. Query phải dùng đúng model/dimension đã tạo index; không trộn vector store giữa provider hoặc model.

Strategy phục vụ mặc định là `hybrid_section_semantic`. Index verified được build vào thư mục version mới và script từ chối ghi đè thư mục không rỗng.

Các thư mục `pdf_db`/`pdf_db_openai` và số row 11.428 trong tài liệu/benchmark cũ là artifact lịch sử, không phải hợp đồng serving hiện hành.

## 4. Kiểm tra nguồn gốc và dữ liệu riêng tư

Mỗi chunk verified mang ít nhất `source_id`, `source_sha256`, `page_numbers`, `content_sha256`, `chunking_strategy` và `provenance_version`. Sidecar `verified_manifest.json` liệt kê hash nội dung theo nguồn/trang.

API kiểm tra lúc startup:

1. `NVIDIA_PDF_DB_DIR` và strategy resolve đúng bên trong thư mục index.
2. Hash sidecar khớp manifest.
3. Source binary còn khớp SHA-256 và được duyệt.
4. Mọi Chroma row khớp bộ `(source_id, page_numbers, content_sha256)` trong sidecar.

Ngay trước chat sync/stream, context lại được kiểm provenance; payload đi qua privacy gate trước SDK NVIDIA. Memory riêng theo owner là nguồn private có chủ đích nhưng vẫn phải qua redaction.

## 5. Tạo index và đưa tài liệu vào sử dụng

Guideline monitor tải bản mới vào `data/raw/staging/<source>/<version>/`, kiểm PDF/dedup rồi tạo review. Chỉ bản được role phù hợp duyệt mới được promote vào corpus.

Promotion vào corpus không tự biến tài liệu thành source serving. Muốn thay index:

1. Cập nhật manifest với binary/hash/quyền gửi đã được xác minh.
2. Chạy `scripts/build_verified_corpus_index.py --output <thư-mục-version-mới>`; không dùng active directory.
3. Audit source, chunk, sidecar và benchmark retrieval/scope.
4. Chỉ đổi `NVIDIA_PDF_DB_DIR` sau khi các cổng đạt; giữ index cũ để rollback.

Không chạy build live chỉ để sửa tài liệu. Script gọi NVIDIA embeddings và có thể gửi nội dung corpus đã duyệt ra provider.

## 6. Kiểm chứng nhanh trên Windows

```powershell
.\.venv\Scripts\python.exe -c "from src.shared.config import NVIDIA_PDF_DB_DIR, DEFAULT_CHUNK_STRATEGY, NVIDIA_EMBEDDING_MODEL; print(NVIDIA_PDF_DB_DIR, DEFAULT_CHUNK_STRATEGY, NVIDIA_EMBEDDING_MODEL)"
.\.venv\Scripts\python.exe -c "from src.shared.corpus_provenance import validate_serving_index; print(validate_serving_index())"
```

Nếu checkout mới chưa có bundle, làm theo `deployment/README.md`. Không coi thư mục Chroma tồn tại là bằng chứng index hợp lệ; preflight phải pass.

## 7. Ràng buộc thường gặp

- Không commit DB, index, source binary, key hoặc dữ liệu bệnh nhân.
- Không dùng metadata row count lịch sử làm expected value cho checkout khác.
- Không thêm file vào corpus rồi giả định index tự cập nhật.
- Không gửi context khi source/hash/provenance chưa đạt; lỗi phải fail closed.
- Test crawl/seed/reindex phải xác nhận đường ghi trước và dùng dữ liệu cô lập.

### Tự kiểm tra

- [ ] Nói được vì sao file có trên đĩa chưa chắc được retrieval.
- [ ] Kể được bốn source của active serving index và hai source chưa được duyệt gửi.
- [ ] Chạy được `validate_serving_index()` hoặc giải thích chính xác vì sao checkout thiếu bundle.
- [ ] Phân biệt promotion corpus với chuyển active index.
