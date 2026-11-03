# Kế hoạch kiểm soát payload NVIDIA — 02/11/2026

Trạng thái: đã triển khai một phần; chưa đạt toàn bộ cổng nghiệm thu. Bằng chứng và giới hạn: [PAYLOAD_PRIVACY_IMPLEMENTATION.md](PAYLOAD_PRIVACY_IMPLEMENTATION.md). Không thay tiêu chí hoặc trạng thái hoàn thành tác vụ 1–7.

## Kết quả rà code

- `src/shared/nvidia.py::embed_texts`: gửi nguyên `texts` trong JSON `input`; cả embed_query và embed_documents đi qua đây. PII có thể ra ngoài trước khi gọi chat.
- `src/shared/nvidia.py::_CompletionsNS._once`: chuyển kwargs sang SDK, chỉ thay model; không redact. Retry dùng cùng payload.
- `src/chat/generator.py`: format_context nối source_id, version, ngày xuất bản và content; ghép query vào user prompt, cả sync/stream. Không phải mọi metadata của ContextItem đều được gửi, nhưng metadata đã ghép vào chuỗi cũng cần kiểm soát.
- `src/chat/rag_pipeline.py`: ghép tài liệu, GHO và bộ nhớ ngắn hạn/tóm tắt/dài hạn trước generate. Preflight chỉ kiểm tra retrieval không bao phủ bộ nhớ hoặc evaluator.
- `src/reviews/evaluator.py`: gửi question, answer và context cho judge. Giới hạn 800 ký tự/context và 6000 ký tự không loại PII.
- ShortTermMemory/EpisodicMemory là singleton, accessor không nhận user_id; đọc không lọc người dùng. Nguy cơ lẫn dữ liệu giữa người dùng cần kiểm thử tái hiện. LongTermMemory có filter user_id khi retrieve, nhưng pipeline giữ biến global đổi theo request: phải kiểm tra request đồng thời.
- SOAP, triage NLU, rollup và summarizer cũng gọi chat client chung, cần regression khi sửa chốt gửi.
- Hàm redact_pii hiện chỉ áp dụng mood_notes. Regex hiện có không đủ bảo đảm tên tự do, địa chỉ tiếng Việt, ngày sinh hay định danh viết cách khoảng. Không dùng nhãn “already redacted” trong prompt làm bằng chứng.

Đây là kiểm tra tĩnh đường dữ liệu, chưa capture payload runtime, chưa quét toàn bộ index hoặc chứng minh context lượt chạy cũ có PII. Không gửi dữ liệu ra NVIDIA trong lần rà này.

## Thực hiện theo thứ tự

### 1. Capture offline tại ranh giới HTTP

- Tạo test transport chặn mạng cho OpenAI SDK và httpx embeddings. Capture payload ngay trước gửi, không gọi provider thật.
- Dùng DB/index/bộ nhớ thử riêng với dấu nhận diện tổng hợp khác nhau cho query, document, metadata, short-term, episodic, long-term, answer judge và GHO.
- Kiểm tra sync, stream, embeddings query/document, judge, retry/đổi model; xác nhận mọi điểm gửi được capture. Chặn mọi request mạng ngoài transport, không cho fixture fallback sang index repo.
- Lưu report loại trường và số lượng dấu nhận diện, không lưu khóa hoặc payload thật. Test lỗi cũng không dump payload/headers.
- Đạt khi có ma trận nguồn → request đích, và test hiện trạng tái hiện thiếu redact/lẫn memory bằng dữ liệu tổng hợp.

### 2. Cô lập bộ nhớ trước khi redact

- Đưa user/session identity từ auth tới các accessor short-term/episodic; không dùng user_id do client tự khai để chọn bộ nhớ.
- Dùng biến memory cục bộ theo request trong pipeline, sửa toàn bộ callers, streaming và cập nhật memory; tránh biến global bị request khác thay đổi.
- Long-term giữ lọc chủ sở hữu; test A/B xen kẽ và đồng thời, kể cả đường tóm tắt, export, cache và lỗi.
- Memory cũ không xác định chủ sở hữu không được đưa vào prompt; cách ly, không xóa tự động.
- Đạt khi không có dấu nhận diện của A trong bất kỳ request gửi hoặc response của B.

### 3. Chính sách dữ liệu và redact cục bộ

- Định nghĩa các loại cần bỏ/thay: tên bệnh nhân/người thân, điện thoại, email, CCCD/CMND, mã bệnh án/BHYT, địa chỉ cụ thể, ngày sinh đầy đủ, username và URL chứa định danh/token.
- Phân biệt tên tác giả/tài liệu công khai với tên bệnh nhân; giữ citation bằng ID ổn định không chứa PII. Không gửi đường dẫn máy cá nhân.
- Tối thiểu hóa dữ liệu: bỏ trường định danh không cần thiết; chỉ gửi dữ kiện lâm sàng cần trả lời. Giữ nguyên giá trị glucose, đơn vị, thời gian tương đối, dấu hiệu nguy hiểm và phủ định.
- Regex xử lý mẫu định dạng rõ; kiểm tra thông tin hồ sơ đã biết trong phạm vi đúng người dùng. Đánh giá bộ nhận diện tên/địa chỉ tiếng Việt chạy local nếu quy tắc chưa đủ; không dùng LLM bên ngoài để redact dữ liệu thô.
- Không tuyên bố đã ẩn danh tuyệt đối. Tổ hợp tuổi, địa điểm, thời điểm và bệnh sử vẫn có nguy cơ nhận diện lại. Nội dung không đủ chắc chắn phải bị chặn hoặc yêu cầu người dùng sửa trước khi gửi.
- Đạt khi bộ gold tổng hợp có nhãn PII được loại hết các span bắt buộc, đồng thời giữ đúng dữ kiện y khoa; đo false-positive/false-negative và lưu các giới hạn còn lại.

### 4. Chốt kiểm soát tại cả chat và embedding

- Thêm module dùng chung (dự kiến `src/shared/privacy.py`), gọi trước request chat và embeddings trong `src/shared/nvidia.py`.
- Kiểm tra toàn bộ phần dữ liệu payload: messages system/user/assistant/tool, content dạng list, tool arguments/results, metadata/name/user và extra_body có thể chứa dữ liệu. Các cấu trúc chưa hỗ trợ bị từ chối, không âm thầm bỏ qua.
- Làm sạch trước truncate, trước mọi retry; kiểm tra lại payload cuối cùng. Không sửa Authorization hoặc cấu hình model như dữ liệu bệnh nhân.
- Lỗi redact/kiểm tra phải dừng request; không fallback gửi nguyên văn, không ghi cache câu trả lời như thành công. Trả lỗi rõ cho caller; red-flag deterministic vẫn báo hỗ trợ y tế ngay.
- Thông báo/log chỉ chứa loại phát hiện, số lượng, mã lý do và phiên bản chính sách; không chứa giá trị PII, khóa hoặc bản gốc. Rà cả exception từ provider, tracing và LangSmith.
- Đạt khi transport capture xác nhận không còn marker PII ở mọi nhánh, kể cả retry và streaming; trường hợp bị chặn có 0 request ra ngoài.

### 5. Corpus và dữ liệu đã lưu

- Quét local read-only toàn bộ chunk/metadata và bộ nhớ liên quan; report chỉ có ID nội bộ, loại phát hiện và số lượng, không trích PII ra console.
- Phân loại nguồn guideline công khai, dữ liệu tổng hợp và dữ liệu người dùng. Không suy ra “an toàn” chỉ từ tên file.
- Index cũ phải qua chốt gửi khi đọc; dữ liệu mới được làm sạch trước embedding. Nếu cần rebuild, tạo index phiên bản mới trong thư mục thử, kiểm tra retrieval/citation rồi mới chuyển; không sửa/xóa index gốc tự động.
- Kiểm tra source bổ sung GHO, alias import `chat.*`/`src.chat.*` và mọi đường fallback; xác minh chính hàm pipeline gọi dùng index thử.
- Đạt khi mọi nguồn đưa vào prompt có provenance và trạng thái xử lý; không có fallback sang kho ngoài danh sách thử.

### 6. Xác minh offline rồi live, tiếp tục integration 1–7

- Unit: số điện thoại có dấu cách/+84, email, ID, tên/địa chỉ có dấu và không dấu, Unicode, JSON lồng, metadata, URL; đối chứng 69/70/250/251/299/300 mg/dL và phủ định triệu chứng không bị đổi.
- Integration offline: API → DB/index thật riêng → memory → retrieval → chat/judge/embedding transport capture; xác nhận phân quyền và concurrency A/B, mọi nhánh lỗi không gửi dữ liệu thô.
- Backend regression liên quan triage, SOAP, RAG, reviews, memory; benchmark retrieval/answer khi thay đổi nội dung embedding, có judge thật ở lượt live được phép, không dùng skip-judge để tuyên bố chất lượng.
- Live chỉ sau khi capture offline đạt: NVIDIA thật, DB/index thử thật, dữ liệu tổng hợp đã kiểm tra; không chấp nhận fallback/rule-only làm bằng chứng LLM thành công. Ghi model, endpoint, số request, kết quả và cấu hình; không ghi secret/payload nhạy cảm.
- Hoàn thiện Playwright 1–7 theo từng ô docs/TASKS.md, không mock API thuộc luồng, đối chiếu DB, build/tsc và test backend phù hợp. Chỉ đánh dấu done khi toàn bộ tiêu chí pass cùng snapshot code.

## Thứ tự triển khai tiếp theo đã chốt

1. Tạo index mới trong thư mục cô lập, chỉ từ bốn binary đã xác minh: WHO Classification 2019, WHO HEARTS-D 2020, WHO PEN 2020 và BYT QĐ3319/2017. Không sửa hoặc xóa index hiện tại.
2. Với từng chunk, tái tạo từ binary nguồn và kiểm tra được `source_id`, SHA-256 file, trang và hash nội dung chunk; không kế thừa niềm tin từ metadata/index cũ. Báo lỗi nếu trang không truy vết được.
3. Chuyển cấu hình bằng một con trỏ/cấu hình phiên bản có giá trị cũ được ghi lại để rollback. Chỉ chuyển sau audit index mới đạt; rollback không rebuild và không xóa index nào.
4. Chạy retrieval benchmark có dataset/config/metric/report và test câu hỏi ngoài phạm vi. Đạt khi không có hit từ bệnh khác hoặc source ngoài bốn nguồn, citation mở đúng trang, và chất lượng đạt ngưỡng benchmark đã công bố; không dùng `--skip-judge` để chứng minh chất lượng câu trả lời.
5. Mở rộng gold tên/địa chỉ tiếng Việt có nhãn span: có dấu, không dấu, viết tắt, tên người thân và địa chỉ tự do; thêm đối chứng y khoa/tác giả công khai. Báo false-negative/false-positive và giới hạn, không suy rộng từ tập nhỏ.
6. Audit persisted memory theo owner/provenance và chạy toàn luồng GHO injected qua transport capture; trường hợp thiếu owner, provenance hoặc hash phải bị cách ly/chặn.
7. Chỉ khi 1–6 đạt trên cùng snapshot mới chạy một NVIDIA live smoke với dữ liệu hoàn toàn tổng hợp. Ghi model, endpoint, số request và payload đã làm sạch ở dạng bằng chứng không chứa secret/PII.

ADA 2024 và BYT QĐ5481/2020 chỉ được thêm vào index mới sau khi tải được binary từ nguồn chính thức, đối chiếu SHA-256 và cập nhật manifest. Không whitelist tạm, không coi trang công bố hoặc tên file là bằng chứng binary.

## Bàn giao và giới hạn

Mỗi mốc cập nhật WORKFLOW_STATE.md local: SHA/diff, thời gian +07, lệnh, pass/fail/skip, report, phần chưa xác minh. Kết quả quét sạch hoặc redact thành công không chứng minh dữ liệu hoàn toàn không thể tái nhận diện. Chính sách lưu giữ của NVIDIA chưa được đánh giá trong kế hoạch kiểm tra code này.
