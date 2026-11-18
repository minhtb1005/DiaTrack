# Khi nào DiaTrack được đánh dấu một tính năng là hoàn tất?

**Bản đề xuất chờ duyệt · 19/11/2026**

Ở `task-9`, một bài kiểm thử phiếu bàn giao đã chạy đạt. Nhưng khi bệnh nhân còn thiếu dữ kiện, hệ thống chưa cấp mã ca. Người dùng vì thế chưa thể mở phiếu theo tiêu chí AC04. Nếu agent đề nghị chuyển tính năng này sang `done`, GitHub cần chỉ ra **AC04 còn bị chặn** và ngăn gộp thay đổi vào `main`. Đây là tình huống dùng để nghiệm thu chính kế hoạch này.

[Chắc chắn] Khi rà soát ngày 19/11, danh sách có 27 tính năng. Trong đó, 23 mục mang trạng thái `done` từ trước khi có trường bằng chứng riêng. GitHub báo nhánh `main` chưa được bảo vệ và repo có 0 workflow Actions. Bản chuyển đổi sang [feature_list.json](../feature_list.json) còn ở máy local.

## Agent được đề nghị trạng thái nào?

| Trạng thái | Điều người duyệt cần thấy |
|---|---|
| `todo` | Việc nằm trong danh sách chờ. |
| `in_progress` | Tính năng đã đủ phụ thuộc để bắt đầu. Tại mỗi thời điểm chỉ có một tính năng đang làm. |
| `partial` | Đã có phần triển khai cụ thể. Agent chỉ ra phần đó trong code và liệt kê các tiêu chí còn thiếu hoặc chưa kiểm tra. Chẳng hạn, API đã lưu được phiếu nhưng chưa kiểm tra thao tác tải lại trên trình duyệt. |
| `blocked` | Muốn đi tiếp cần một quyết định hoặc điều kiện bên ngoài. Trường `blocked_reason` ghi tiêu chí nào bị chặn, vì sao và điều gì sẽ gỡ chặn. Với AC04, chủ sản phẩm cần chốt có cho mở phiếu nháp khi chưa đủ dữ kiện hay không. |
| `done` | Mỗi tiêu chí bắt buộc có bằng chứng đạt trên phiên bản code được xét. Thay đổi liên quan đến phân quyền, cách ly dữ liệu bệnh nhân hoặc cảnh báo khẩn còn cần kết luận đạt của QA độc lập theo [AGENTS.md](../AGENTS.md). |

## Thứ tự triển khai sau khi duyệt

1. **Chốt mốc ban đầu.** Rà bản chuyển đổi, đưa danh sách tính năng và tài liệu lưu trữ vào Git. Ghi rõ 23 mục hoàn tất kế thừa từ lịch sử. Lần đầu kiểm tra phải nhận đúng mốc này. Khi một PR sửa hành vi đã nghiệm thu hoặc đổi tiêu chí, nó phải chỉ ra tính năng bị ảnh hưởng để kiểm tra lại phần liên quan.
2. **Viết chương trình kiểm tra trạng thái.** So sánh danh sách trước và sau PR. Kiểm tra ID, phụ thuộc, giới hạn một việc đang làm và các điều kiện trong bảng trên. Nếu tác giả xóa hoặc nới tiêu chí, yêu cầu quyết định của người có quyền duyệt yêu cầu sản phẩm. Thử trên bản sao của danh sách với cả thay đổi hợp lệ, hai việc cùng đang làm và trường hợp xóa AC04 để đóng `task-9`.
3. **Nối từng tiêu chí thí điểm với bằng chứng thực.** Planner chốt hành vi kỳ vọng. Executor chạy test và ghi mã tiêu chí, phiên bản code, môi trường, lệnh và nơi xem kết quả. Hệ thống kiểm tra PR đọc kết quả của đúng test từ báo cáo do lượt chạy tạo ra. Với tiêu chí cần quan sát bằng tay, QA ghi kỳ vọng, kết quả thực tế và quyết định trên cùng phiên bản. Báo cáo phải mở được từ PR, dùng dữ liệu tổng hợp và tránh đưa thông tin bệnh nhân hoặc khóa truy cập vào log.
4. **Chạy thử trên PR trước khi bật chặn.** Dùng bản sao của `task-9` để thử đường bị từ chối. Dùng ca bệnh nhân A lưu 110 mg/dL và bệnh nhân B không thể đọc hoặc ghi thay để thử đường đạt có QA độc lập. Đổi qua báo cáo của commit cũ, bỏ qua test hoặc bỏ kết luận QA đều phải khiến check báo rõ tiêu chí còn thiếu. Một use case đạt chỉ xác nhận các tiêu chí nó thực sự kiểm tra.
5. **Bật điều kiện bắt buộc trên GitHub.** Sau khi hai ca thử cho kết quả dự kiến, yêu cầu PR và check đạt trước khi gộp vào `main`. Giới hạn quyền đẩy trực tiếp và quyền bỏ qua check của tài khoản agent. Người có quyền duyệt phải kiểm soát cả thay đổi đối với workflow, chương trình kiểm tra và các test dùng để nghiệm thu. Kiểm chứng bằng một PR thử bị GitHub chặn thật, sau đó sửa nguyên nhân và quan sát check chạy lại.

## Phạm vi đề nghị duyệt

**Đề nghị duyệt bước 1–4 trước.** Sản phẩm bàn giao ở mốc này là một PR có thể xem được cả trường hợp đạt lẫn lý do bị từ chối. Bước 5 tác động tới mọi người đang làm việc trên `main`, nên kế hoạch tách việc bật bảo vệ nhánh thành một quyết định sau thí điểm.

Người duyệt vẫn cần đánh giá test có phản ánh đúng hành vi hay không. Ví dụ, một test xác nhận bệnh nhân A đọc được phiếu của mình chưa chứng minh rằng bệnh nhân B bị từ chối. Chương trình có thể xác minh test nào đã chạy. QA chịu trách nhiệm kiểm tra điều test thực sự chứng minh.
