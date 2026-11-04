from src.triage.review_queue import audit_report, create_case, decide


def test_audit_report_separates_reviewer_disagreement_and_red_flags(client, make_user, doctor_user):
    patient, _ = make_user()
    proposal = {
        "proposed_priority": "routine",
        "rationale": "Đề xuất thử; không phải chẩn đoán.",
        "source": "project_requirements.json v1",
    }
    first = create_case(patient["id"], "tê chân nhẹ", 140, "hôm nay", proposal)
    second = create_case(patient["id"], "mắt mờ", 180, "hai ngày", proposal)
    decide(first, doctor_user["user"]["id"], "approved", "routine", "Theo dõi theo hướng dẫn.", None)
    decide(second, doctor_user["user"]["id"], "revised", "soon", "Liên hệ cơ sở y tế để được hỗ trợ.", "Điều chỉnh mức")

    report = audit_report()
    assert report["reviewed_cases"] >= 2
    assert report["disagreement_count"] >= 1
    assert report["disagreement_rate"] == report["disagreement_count"] / report["reviewed_cases"]
    assert report["gold"]["version"] == 1
    assert report["gold"]["red_flag_cases"] > 0
    assert report["gold"]["red_flag_failures"] == []
    assert "requester_id" not in report and "message" not in report

    headers = {"Authorization": f"Bearer {doctor_user['token']}"}
    response = client.get("/v1/triage/audit/report", headers=headers)
    assert response.status_code == 200
    outsider, token = make_user()
    assert outsider["id"] != patient["id"]
    assert client.get("/v1/triage/audit/report", headers={"Authorization": f"Bearer {token}"}).status_code == 403
