# AGENTS.md — DiaTrack

## Phạm vi và nguồn sự thật

- Chỉ đái tháo đường týp 2. Nguồn phạm vi hiện hành: `docs/project_requirements.json` (`scope_rules` và 6 project): `258-triage`, `260` (thuốc), `262` (SOAP), `264` (đường huyết tại nhà), `266` (dinh dưỡng), `258-booking`.
- Đề 267 và 273 không nằm trong JSON hiện hành; chỉ thêm khi người dùng sửa nguồn phạm vi. Bệnh khác chỉ là bệnh đi kèm hoặc biến chứng.
- Giữ ràng buộc an toàn: không chẩn đoán, kê đơn/đổi/ngưng liều; red-flag luôn chuyển hỗ trợ y tế; ngoài phạm vi trả câu từ chối cố định. Plan của SOAP dành cho bác sĩ.
- Dùng `feature_list.json` làm danh sách tính năng, use case, trạng thái và tiêu chí chấp nhận. `docs/TASKS_ARCHIVE.md` chỉ là bằng chứng lịch sử, không cập nhật trạng thái ở đó. Không ghi tiến độ vào README; không tự hạ tiêu chí để đạt. Tiêu chí sai/thiếu: ghi vào state và báo người dùng.

## Bắt đầu phiên

1. Đọc file này, yêu cầu mới nhất, `docs/project_requirements.json` (đặc biệt `scope_rules`) và [README](README.md); xem [bản đồ repo](README.md#repository-map).
2. Đọc `feature_list.json`; tiếp tục feature `in_progress` nếu có. Nếu không, chọn một feature `partial` hoặc `todo` theo `priority` và `dependencies`, trừ khi người dùng giao việc khác. Chỉ một feature được `in_progress` (WIP = 1); các feature `partial` là backlog chưa đạt, không phải đang triển khai đồng thời.
3. Đọc **Trạng thái hiện hành** và mục liên quan trong `WORKFLOW_STATE.md` local, nếu có.
4. Đối chiếu `git status`, code, test và hợp đồng liên quan trước khi tin ghi chú; giữ nguyên thay đổi có sẵn.

Nếu thiếu tài liệu tác vụ, ghi nhận và chỉ hỏi khi thiếu thông tin thực sự chặn việc được giao. Nếu thiếu state, tra PR/commit trước, không suy ra việc đã xong.

## Vòng làm việc

Mặc định một agent lập kế hoạch, triển khai và tự xác minh một feature. Khi thay đổi tác động tới phân quyền, cách ly dữ liệu giữa bệnh nhân hoặc cảnh báo khẩn, agent chính giao QA cho một agent độc lập trong ngữ cảnh mới. Nếu không có agent độc lập, ghi rõ giới hạn và để bước QA mở.

Agent chính bàn giao ID feature/use case, hợp đồng, tiêu chí, snapshot code, lệnh kiểm tra và vị trí bằng chứng. QA kiểm tra trên cùng snapshot bằng dữ liệu tổng hợp, trả kết quả kỳ vọng/thực tế và giới hạn theo từng tiêu chí. Sai hành vi thì chuyển lại cho người triển khai. Mâu thuẫn hợp đồng thì chuyển lại cho người lập kế hoạch. Agent chính ghi kết quả vào `evidence` và cập nhật trạng thái theo WIP = 1. Chỉ tách Planner riêng khi được giao hoặc khi chạy thí nghiệm ba vai.

1. Chốt phạm vi nhỏ: đầu vào/đầu ra, lỗi, tiêu chí xong; với sức khỏe thêm nguồn dẫn và đường xử lý an toàn.
2. Đọc tài liệu phù hợp: [API](docs/api_contract.md), [dữ liệu](docs/data_contract.md), [kiến trúc](docs/architecture_diagram.md), [đánh giá](docs/evaluation.md). Giữ hợp đồng và nguồn dẫn; sửa UI thì cập nhật test/selector.
3. Triển khai → test liên quan → thao tác UI nếu ảnh hưởng UI → ghi bằng chứng → cập nhật state. Chỉ hoàn thành khi hành vi thực tế đạt tiêu chí và hết lỗi chặn; video demo/cảm giác hài lòng không thay kiểm thử.
4. Cập nhật feature và tiêu chí trong `feature_list.json` kèm lệnh/kết quả. Đối chiếu từng use case trước khi viết test và trước khi chuyển `done`; `historical_check` không thay bằng chứng trên code hiện hành. Bàn giao mục tiêu, file/commit/PR, bằng chứng, giới hạn, rủi ro, việc mở và bước tiếp theo.

## Kiểm tra PR thí điểm

Dùng `python scripts/feature_status.py --base <SHA-nhánh-gốc>` và `python scripts/test_feature_status.py`. Thay đổi code/test khai danh sách ID ở `affected_features` cấp đầu của ledger. Khi cập nhật feature partial, ghi đường dẫn file tracked vào `implementation_ref` và các ID còn mở vào `remaining_criteria`. Khi blocked, ghi cả nguyên nhân và điều kiện tiếp tục. Mỗi tiêu chí khai báo mảng `tests` chứa pytest node ID cụ thể. Mảng rỗng nghĩa là chưa ánh xạ. CI chạy các test đã khai báo một lần trong môi trường tổng hợp, lưu JUnit và criteria.json theo commit, rồi dùng báo cáo đó khi xét done. Chỉ gắn test bao phủ đủ tiêu chí. Trường `requires_qa` mặc định true; chỉ đặt false khi tiêu chí không cần QA độc lập. Hiện T01-AC02 đã được ánh xạ và QA. Các tiêu chí chưa có ánh xạ bằng chứng sẽ chặn đề nghị done mới.

Workflow đọc quyết định duyệt hợp đồng từ GitHub review trên đúng commit, của người khác tác giả PR thuộc biến repository `PRODUCT_REVIEWERS` (các login cách nhau bằng khoảng trắng). Khi chưa cấu hình người duyệt, cổng từ chối sửa hợp đồng. Bản QA thí điểm ghi snapshot các file đã duyệt, CI chạy lại test trên checkout của PR và lưu JUnit theo commit. Quyền sửa cổng và bảo vệ main thuộc bước 5.

## Xác minh

Dùng Python `.venv` trên Windows; không in/commit secret hoặc dữ liệu bệnh nhân. Cấu hình container nằm ở [Compose](docker-compose.yml), [Dockerfile backend](Dockerfile) và [Dockerfile frontend](frontend/Dockerfile); đọc cấu hình thực tế trước khi vận hành, không suy ra build đã đạt từ việc có file.

| Phạm vi | Kiểm tra |
|---|---|
| Backend/API/DB | `.\.venv\Scripts\python.exe -m pytest tests/test_<module>.py -q`; thêm toàn bộ `pytest -q` khi môi trường cho phép. Dùng fixture `client` và auth helper ở `tests/conftest.py`. |
| Frontend | Trong `frontend/`: `npx tsc --noEmit`, `npm run build`; sửa luồng UI thì chạy `npm run test:e2e -- <spec>`. Chuẩn bị backend/seed phù hợp với spec. |
| RAG/chunking | Test liên quan + benchmark theo [hướng dẫn](docs/benchmark.md) / `scripts/run_benchmarks.py`; ghi dataset, provider, cấu hình, metric, report. `--skip-judge` không chứng minh chất lượng câu trả lời. |
| Triage/labs/solvers | Test module; benchmark `--services` khi đổi logic được gold set bao phủ; kiểm tra nguy hiểm và từ chối ngoài phạm vi. |

Trước crawl/seed/test/eval, đọc script và xác nhận đường ghi. Fixture không bảo đảm mọi DB/index/module đã cô lập: dùng DB/index sao chép hoặc môi trường riêng, chỉ dọn đúng dữ liệu thử. Không chạy benchmark live chỉ để sửa tài liệu. Thiếu dịch vụ/key/seed hoặc bỏ test phải ghi **chưa xác minh đầy đủ**, nêu rõ lý do.

### Nguồn bằng chứng kiểm thử

- Phạm vi: <tính năng/PR>
- Code lúc chạy: <branch, commit SHA, PR số>; nếu chưa commit, ghi file thay đổi và vị trí diff/snapshot.
- Thời điểm: <ngày giờ và múi giờ>
- Lệnh và kết quả: <lệnh chính xác, số pass/fail/skip>
- Tra cứu: <URL CI run + job, PR Checks, hoặc report/log local>
- Giới hạn: <test chưa chạy, dữ liệu/dịch vụ thiếu, thay đổi sau lúc test>

Bằng chứng phải khớp code, dữ liệu, dependency và cấu hình; mới hơn không tự có hiệu lực. Ghi kết quả cũ là lịch sử/thay thế, không xóa dấu vết lỗi còn mở; không ghi pass nếu chưa chạy. Commit message có thể kèm thời gian/múi giờ, lệnh, kết quả và nơi tra cứu.

## State, compact và bàn giao

- Sau mỗi thay đổi/mốc triển khai/kiểm thử, sau chốt phạm vi và trước compact/dừng/chuyển phiên: cập nhật ngay **Trạng thái hiện hành** ở đầu `WORKFLOW_STATE.md`. Lịch sử mới nhất → cũ nhất; không chỉ nối cuối file.
- Giữ đủ: mục tiêu/tiêu chí, nhánh/HEAD/file chưa commit, đã xong/đang làm/bị chặn, quyết định/lý do, lệnh/kết quả/thời điểm/code lúc test và bước tiếp theo đầu tiên.
- State chỉ local, không commit hoặc `git add -f`; không chứa secret/dữ liệu nhạy cảm. Sang clone khác: bàn giao ngắn trong PR hoặc trực tiếp, không yêu cầu công khai nhật ký dài.
- Khi state quá dài, lặp bối cảnh hoặc trước handoff dài hạn: chỉ compact lịch sử ổn định sau khi ghi đủ bằng chứng. Đọc và dùng skill cave-man nếu có; nếu không thì compact thủ công, không tự cài skill. Xem diff để giữ quyết định, bằng chứng, blocker và việc mở; không biến việc chưa xong thành hoàn thành.
- Phiên tiếp theo đối chiếu state với code/git và chạy lại kiểm tra bị ảnh hưởng trước khi dùng bằng chứng cũ.
