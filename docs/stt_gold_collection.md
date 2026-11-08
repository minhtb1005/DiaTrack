# Thu thập gold audio STT tiếng Việt — pilot kỹ thuật

## Điều kiện bắt đầu

Không thu âm trước khi đơn vị sở hữu dữ liệu duyệt biểu mẫu đồng ý, nơi lưu, thời hạn giữ, người được truy cập và quy trình rút consent. Không dùng bệnh nhân thật hoặc thông tin sức khỏe thật trong câu đọc; mọi câu là dữ liệu tổng hợp.

## Ma trận pilot

Mục tiêu tối thiểu 30 người, cân bằng 10 người tự nhận giọng Bắc, 10 Trung, 10 Nam. Mỗi vùng cần ít nhất 5 người từ 60 tuổi trở lên; ghi `age_band`, không ghi ngày sinh. Mỗi người đọc bộ câu chuẩn trên hai điều kiện:

1. Phòng tương đối yên tĩnh bằng điện thoại của người tham gia.
2. Nhiễu sinh hoạt thông thường bằng cùng thiết bị; ghi loại nhiễu, không cố tạo môi trường nguy hiểm.

Mỗi câu đọc một lần; câu có số/red-flag đọc lại lần hai nếu người tham gia tự báo nói vấp. Giữ cả hai take và đánh dấu take được người ghi âm xác nhận. Đây là pilot để so model, không đủ để tuyên bố hiệu quả lâm sàng.

## Bộ câu bắt buộc

- Các biên số: 69, 70, 250, 251, 299, 300 mg/dL; số viết bằng chữ và đọc tự nhiên.
- Bối cảnh: lúc đói, trước ăn, sau ăn hai giờ, trước ngủ, ngẫu nhiên.
- Thời gian: giờ/phút, hôm nay/hôm qua, sáng/chiều/tối.
- Bốn nhóm red-flag trong `docs/project_requirements.json`: hạ đường huyết nặng; tăng đường huyết nguy hiểm; nhiễm trùng bàn chân; tim mạch/đột quỵ.
- Thuốc/HbA1c chỉ dùng tên và giá trị tổng hợp; không đọc đơn thuốc hoặc kết quả thật.
- Đối chứng không nguy hiểm và câu gần âm để đo false-positive.

Danh sách câu phải có `prompt_id`, `reference_text`, `expected_value`, `expected_context`, `expected_red_flag` và được khóa phiên bản trước khi thu.

## Consent và quyền rút dữ liệu

Người tham gia phải được giải thích bằng ngôn ngữ dễ hiểu:

- mục đích là đánh giá nhận dạng tiếng nói, không khám hoặc chẩn đoán;
- nội dung thu, metadata thu và bên được nghe/xử lý;
- audio có thể nhận dạng giọng nói dù đã bỏ tên;
- thời hạn lưu và biện pháp bảo vệ;
- tham gia tự nguyện, có thể dừng hoặc rút dữ liệu theo `participant_code`;
- có hay không việc dùng lại để huấn luyện model — mặc định pilot này là **không**, chỉ benchmark;
- thông tin liên hệ của đơn vị chịu trách nhiệm dữ liệu.

Biểu mẫu ký và bảng ánh xạ danh tính ↔ `participant_code` phải lưu tách biệt, mã hóa và không nằm trong repo. Manifest benchmark chỉ giữ `consent_version`, thời điểm đồng ý, phạm vi `benchmark_only` và trạng thái chưa rút consent.

## Lưu trữ và đặt tên

- Audio private: `<private-root>/<participant_code>/<recording_id>.wav`, PCM mono 16 kHz nếu chuẩn hóa; giữ hash của file gốc và file chuẩn hóa.
- Manifest private: JSONL theo [schema](stt_gold_manifest.schema.json).
- Không commit audio, consent, bảng ánh xạ hoặc manifest có đường dẫn thật.
- Chỉ evaluator được đọc audio. Báo cáo công bố dùng số tổng hợp; transcript lỗi không kèm mã người tham gia.

## Kiểm tra trước benchmark

- Consent hợp lệ, `withdrawn=false`, phạm vi có `benchmark_only`.
- Không thiếu vùng giọng/nhóm tuổi/thiết bị/điều kiện nhiễu đã cam kết.
- SHA-256 khớp file, audio mở được, có đúng một kênh sau chuẩn hóa.
- Hai người duyệt độc lập reference text và nhãn số/red-flag; bất đồng phải giải quyết trước khi khóa gold.
- Split theo người nói, không theo file: một người không được xuất hiện ở cả tuning và test.

## Gate để sang bước 4

Chỉ benchmark provider khi corpus đạt toàn bộ kiểm tra trên. Nếu thiếu consent, rút consent, sai hash hoặc thiếu một nhóm đã cam kết, dừng và báo thiếu; không bù bằng Piper hay STT mock.
