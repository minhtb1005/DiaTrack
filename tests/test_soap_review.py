def test_review_has_reference_and_audit(client, make_user, doctor_user):
    patient, token = make_user()
    made = client.post("/v1/soap/drafts", json={"patient_id": patient["id"], "transcript": "Đang dùng metformin, HbA1c chưa có."}, headers={"Authorization": f"Bearer {token}"}).json()
    review = client.get(f"/v1/soap/drafts/{made['id']}/review", headers={"Authorization": f"Bearer {doctor_user['token']}"})
    assert review.status_code == 200
    assert review.json()["icd_suggestions"][0]["code"] == "E11.x"
    assert review.json()["icd_suggestions"][0]["source"].startswith("https://icd.who.int/")
    assert review.json()["audit"][0]["action"] == "created"
