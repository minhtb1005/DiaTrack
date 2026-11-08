def test_only_signed_note_can_be_exported_as_pdf(client, make_user, doctor_user):
    patient, token = make_user()
    headers = {"Authorization": f"Bearer {token}"}
    doctor_headers = {"Authorization": f"Bearer {doctor_user['token']}"}
    note = client.post("/v1/soap/drafts", json={"patient_id": patient["id"], "transcript": "Tái khám đái tháo đường."}, headers=headers).json()
    assert client.get(f"/v1/soap/drafts/{note['id']}/export", headers=doctor_headers).status_code == 409
    note["plan"] = "Kế hoạch đã ký do bác sĩ nhập"
    assert client.put(f"/v1/soap/drafts/{note['id']}", json={key: note[key] for key in ("subjective", "objective", "assessment", "plan")}, headers=doctor_headers).status_code == 200
    assert client.post(f"/v1/soap/drafts/{note['id']}/sign", headers=doctor_headers).status_code == 200
    exported = client.get(f"/v1/soap/drafts/{note['id']}/export", headers=doctor_headers)
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/pdf"
    assert exported.headers["content-disposition"].endswith('.pdf"')
    assert exported.content.startswith(b"%PDF")
    import fitz
    with fitz.open(stream=exported.content, filetype="pdf") as pdf:
        text = "".join(page.get_text() for page in pdf)
    assert "SOAP BÀN GIAO" in text and "Kế hoạch đã ký do bác sĩ nhập" in text
    assert client.get(f"/v1/soap/drafts/{note['id']}/export", headers=headers).status_code == 403
