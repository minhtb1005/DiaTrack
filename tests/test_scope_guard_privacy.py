from src.diabetes.scope_guard import is_out_of_scope


def test_non_diabetes_diseases_stop_before_rag():
    assert is_out_of_scope("Điều trị hen phế quản như thế nào?")
    assert is_out_of_scope("Phác đồ COPD hiện nay là gì?")
    assert is_out_of_scope("Tôi cần tư vấn điều trị trầm cảm.")
