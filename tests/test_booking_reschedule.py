from tests.booking_helpers import coordinator, first_slot, headers


def test_reschedule_needs_approval_and_reminder_needs_consent(client, make_user):
    patient, token = make_user()
    result, doctor, slot = first_slot(client, token)
    _, coord_token = coordinator()
    base = {"specialty": result["specialty_code"], "doctor_id": doctor["doctor_id"], "slot_date": slot["date"], "slot_time": slot["time"], "source": result["source"], "consent_reminder": False}
    old = client.post("/v1/bookings/hold", json=base, headers=headers(token)).json()
    client.post(f"/v1/bookings/{old['id']}/confirm", headers=headers(token))
    client.post(f"/v1/bookings/{old['id']}/approve", headers=headers(coord_token))
    next_slot = doctor["slots"][1]
    new = client.post("/v1/bookings/hold", json={**base, "slot_date": next_slot["date"], "slot_time": next_slot["time"], "parent_id": old["id"], "consent_reminder": True}, headers=headers(token)).json()
    client.post(f"/v1/bookings/{new['id']}/confirm", headers=headers(token))
    assert client.get(f"/v1/bookings/{old['id']}", headers=headers(token)).json()["status"] == "approved"
    client.post(f"/v1/bookings/{new['id']}/approve", headers=headers(coord_token))
    assert client.get(f"/v1/bookings/{old['id']}", headers=headers(token)).json()["status"] == "rescheduled"
    assert client.post("/v1/bookings/reminders/run", headers=headers(coord_token)).json()["sent"] == 1
    assert client.post("/v1/bookings/reminders/run", headers=headers(coord_token)).json()["sent"] == 0
