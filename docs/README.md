# Bắt đầu với tài liệu DiaTrack

DiaTrack hiện chỉ hỗ trợ đái tháo đường týp 2. Khi tài liệu và code khác nhau, ưu tiên `project_requirements.json` cho phạm vi và an toàn, `TASKS.md` cho trạng thái nghiệm thu, rồi đến code và test hiện hành.

## Thứ tự đọc

1. [`project_requirements.json`](project_requirements.json), đặc biệt `scope_rules`: phạm vi, sáu project và ràng buộc an toàn.
2. [`TASKS.md`](TASKS.md): tác vụ, tiêu chí chấp nhận và bằng chứng; các kết quả cũ chỉ là lịch sử của đúng snapshot đã ghi.
3. [`architecture_diagram.md`](architecture_diagram.md): luồng hệ thống và bản đồ module.
4. [`api_contract.md`](api_contract.md) và [`data_contract.md`](data_contract.md): hợp đồng API, dữ liệu, corpus và index.
5. [`PAYLOAD_PRIVACY_IMPLEMENTATION.md`](PAYLOAD_PRIVACY_IMPLEMENTATION.md): ranh giới gửi dữ liệu, cô lập memory và provenance.
6. [`../deployment/README.md`](../deployment/README.md): khôi phục bundle RAG đã xác minh cho checkout mới.
7. [`evaluation.md`](evaluation.md) và [`benchmark.md`](benchmark.md): cách kiểm tra; benchmark tháng 9/2026 là số liệu lịch sử OpenAI, không đại diện runtime NVIDIA hiện hành.

Đọc tài liệu chuyên đề như monitoring, voice, dữ liệu tổng hợp hoặc security khi công việc chạm đúng phần đó.

## Chạy local trên Windows

Yêu cầu tối thiểu: Python `.venv`, Node.js/npm, file cấu hình local và bundle RAG đã xác minh. Bundle không nằm trong Git; lấy qua kênh deployment rồi làm theo [`deployment/README.md`](../deployment/README.md). Không rebuild vào thư mục index đang phục vụ.

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload --port 8000
Set-Location frontend
npm install
npm run dev
```

Backend dùng NVIDIA cho chat và mặc định cho embedding. Startup sẽ dừng nếu index, manifest, source hash hoặc Chroma rows không khớp. Không in key hoặc dữ liệu bệnh nhân khi xử lý lỗi.

Frontend mặc định ở `http://localhost:3000`. Nếu đổi cổng, đặt đúng `FRONTEND_URL` cho backend; biến chỉ dùng trong test harness không tự thay CORS runtime.

## Kiểm tra thay đổi

- Backend/API/DB: dùng `.\.venv\Scripts\python.exe -m pytest ...` với fixture và DB/index cô lập.
- Frontend: `npx tsc --noEmit`, `npm run build`; thay luồng UI thì chạy Playwright trên backend thật và dữ liệu thử cô lập.
- RAG: test liên quan, audit provenance và benchmark theo [`benchmark.md`](benchmark.md). `--skip-judge` không chứng minh chất lượng câu trả lời.
- Live provider chỉ chạy với dữ liệu tổng hợp đã qua privacy/provenance gate; ghi rõ provider, dataset, cấu hình và snapshot code.

Quy tắc bằng chứng đầy đủ và cách cập nhật state nằm trong [`../AGENTS.md`](../AGENTS.md).
