from pathlib import Path


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_doctor_edits_signs_and_final_is_immutable(client, make_user, doctor_user, monkeypatch, tmp_path):
    import src.care_store as store
    monkeypatch.setattr(store, "DB_PATH", Path(tmp_path / "care.db"))
    store.init_db()
    patient, patient_token = make_user()
    client.post("/v1/glucose", json={"user_id": patient["id"], "value_mgdl": 142, "context": "fasting"}, headers=_headers(patient_token))

    made = client.post("/v1/soap/drafts", json={"patient_id": patient["id"], "transcript": "Tôi hay khát nước."}, headers=_headers(patient_token))
    assert made.status_code == 200, made.text
    note = made.json()
    assert note["plan"] == "" and "thuốc đang dùng" in note["missing"]
    assert note["evidence"][0]["type"] == "transcript"

    edited = client.put(f"/v1/soap/drafts/{note['id']}", json={"subjective": "Khát nước [Transcript]", "objective": note["objective"], "assessment": "Bác sĩ đánh giá", "plan": "Kế hoạch do bác sĩ nhập"}, headers=_headers(doctor_user["token"]))
    assert edited.status_code == 200
    signed = client.post(f"/v1/soap/drafts/{note['id']}/sign", headers=_headers(doctor_user["token"]))
    assert signed.status_code == 200 and signed.json()["status"] == "signed"
    assert client.put(f"/v1/soap/drafts/{note['id']}", json={"subjective": "x", "objective": "x", "assessment": "x", "plan": "x"}, headers=_headers(doctor_user["token"])).status_code == 409
    assert client.post(f"/v1/soap/drafts/{note['id']}/sign", headers=_headers(patient_token)).status_code == 403
