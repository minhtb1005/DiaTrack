"""The current project scope requires one fixed out-of-scope response."""

from src.diabetes.scope_guard import is_out_of_scope, safeguard_response


FIXED_REPLY = (
    "Hệ thống chỉ hỗ trợ theo dõi đái tháo đường. Nội dung này nằm ngoài phạm vi an toàn của hệ thống, "
    "vui lòng hỏi bác sĩ ở lần khám tới."
)


def test_out_of_scope_topics_share_exact_reply():
    for question in ("Tôi nên uống kháng sinh nào?", "Tư vấn điều trị hen suyễn", "Điều trị tăng huyết áp"):
        assert is_out_of_scope(question)
        assert safeguard_response(question) == FIXED_REPLY


def test_diabetes_question_not_rejected():
    assert not is_out_of_scope("Tôi nên ghi đường huyết sau ăn thế nào?")
