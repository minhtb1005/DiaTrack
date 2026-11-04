from tests.booking_helpers import coordinator, first_slot, headers


def test_dashboard_is_aggregate_and_low_confidence_goes_to_human(client, make_user):
    patient, token = make_user()
    result, doctor, slot = first_slot(client, token, "không rõ nhu cầu")
    held = client.post("/v1/bookings/hold", json={"specialty": result["specialty_code"], "doctor_id": doctor["doctor_id"], "slot_date": slot["date"], "slot_time": slot["time"], "source": result["source"], "confidence": result["confidence"]}, headers=headers(token))
    assert held.status_code == 200
    _, coord_token = coordinator()
    dashboard = client.get("/v1/bookings/coordination/dashboard", headers=headers(coord_token))
    assert dashboard.status_code == 200
    data = dashboard.json()
    assert data["needs_human"][0]["id"] == held.json()["id"]
    assert "patient_id" not in data["needs_human"][0]
    assert client.get("/v1/bookings/coordination/dashboard", headers=headers(token)).status_code == 403
