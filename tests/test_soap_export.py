def test_only_signed_note_can_be_exported(client, make_user, doctor_user):
    patient, token = make_user()
    headers = {"Authorization": f"Bearer {token}"}
    doctor_headers = {"Authorization": f"Bearer {doctor_user['token']}"}
    note = client.post("/v1/soap/drafts", json={"patient_id": patient["id"], "transcript": "Tái khám đái tháo đường."}, headers=headers).json()
    assert client.get(f"/v1/soap/drafts/{note['id']}/export", headers=doctor_headers).status_code == 409
    assert client.post(f"/v1/soap/drafts/{note['id']}/sign", headers=doctor_headers).status_code == 200
    exported = client.get(f"/v1/soap/drafts/{note['id']}/export", headers=doctor_headers)
    assert exported.status_code == 200 and "SOAP BÀN GIAO" in exported.text
    assert client.get(f"/v1/soap/drafts/{note['id']}/export", headers=headers).status_code == 403
