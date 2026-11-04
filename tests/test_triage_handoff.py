from src.triage.review_queue import create_case, handoff_for


def _proposal():
    return {
        "proposed_priority": "soon",
        "rationale": "Có triệu chứng cần nhân viên y tế xem xét. Đây chỉ là đề xuất phân luồng, không phải chẩn đoán.",
        "source": "docs/project_requirements.json#projects[258-triage].problem (protocol mô phỏng); docs/project_requirements.json#scope_rules",
    }


def test_handoff_preserves_session_data_and_marks_missing(client, make_user, admin_client):
    owner, owner_token = make_user(role="user")
    other, other_token = make_user(role="user")
    case_id = create_case(owner["id"], "Tê chân từ sáng", 180, None, _proposal())

    handoff = handoff_for(case_id)
    assert handoff["symptoms"] == "Tê chân từ sáng"
    assert handoff["latest_glucose_mgdl"] == 180
    assert handoff["missing_information"] == ["Thời điểm bắt đầu triệu chứng"]
    assert handoff["notice"].startswith("Phiếu bàn giao không phải chẩn đoán")
    assert len(handoff["sources"]) == 2

    path = f"/v1/triage/reviews/{case_id}/handoff"
    assert client.get(path, headers={"Authorization": f"Bearer {owner_token}"}).status_code == 200
    admin_headers = {"Authorization": f"Bearer {admin_client['token']}"}
    assert client.get(path, headers=admin_headers).status_code == 200
    assert client.get(path, headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
    assert other["id"] not in client.get(path, headers=admin_headers).text
