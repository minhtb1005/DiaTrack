from tests.booking_helpers import coordinator, first_slot, headers


def test_hold_confirm_then_coordinator_approves_and_slot_is_unique(client, make_user):
    patient, token = make_user()
    _, other_token = make_user()
    result, doctor, slot = first_slot(client, token)
    payload = {"specialty": result["specialty_code"], "doctor_id": doctor["doctor_id"], "slot_date": slot["date"], "slot_time": slot["time"], "source": result["source"]}
    held = client.post("/v1/bookings/hold", json=payload, headers=headers(token))
    assert held.status_code == 200, held.text
    booking_id = held.json()["id"]
    assert client.post(f"/v1/bookings/{booking_id}/confirm", headers=headers(other_token)).status_code == 404
    assert client.post("/v1/bookings/hold", json=payload, headers=headers(other_token)).status_code == 409
    assert client.post(f"/v1/bookings/{booking_id}/confirm", headers=headers(token)).status_code == 200
    _, coord_token = coordinator()
    approved = client.post(f"/v1/bookings/{booking_id}/approve", headers=headers(coord_token))
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
