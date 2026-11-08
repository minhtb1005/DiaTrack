from datetime import datetime, timedelta

from tests.booking_helpers import coordinator, first_slot, headers


def test_reschedule_needs_approval_and_reminder_needs_consent(client, make_user, monkeypatch):
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
    appointment = datetime.fromisoformat(f"{next_slot['date']}T{next_slot['time']}:00+07:00")
    monkeypatch.setenv("BOOKING_REMINDER_NOW", (appointment - timedelta(hours=1)).isoformat())
    assert client.post("/v1/bookings/reminders/run", headers=headers(coord_token)).json()["sent"] == 1
    assert client.post("/v1/bookings/reminders/run", headers=headers(coord_token)).json()["sent"] == 0


def test_reminder_is_not_sent_outside_24_hour_window(client, make_user, monkeypatch):
    _, token = make_user()
    result, doctor, slot = first_slot(client, token)
    _, coord_token = coordinator()
    booking = client.post("/v1/bookings/hold", json={"specialty": result["specialty_code"], "doctor_id": doctor["doctor_id"], "slot_date": slot["date"], "slot_time": slot["time"], "source": result["source"], "consent_reminder": True}, headers=headers(token)).json()
    client.post(f"/v1/bookings/{booking['id']}/confirm", headers=headers(token))
    client.post(f"/v1/bookings/{booking['id']}/approve", headers=headers(coord_token))
    appointment = datetime.fromisoformat(f"{slot['date']}T{slot['time']}:00+07:00")
    monkeypatch.setenv("BOOKING_REMINDER_NOW", (appointment - timedelta(hours=25)).isoformat())
    assert client.post("/v1/bookings/reminders/run", headers=headers(coord_token)).json()["sent"] == 0


def test_reschedule_parent_must_be_owned_and_approved(client, make_user):
    _, token = make_user()
    _, other_token = make_user()
    result, doctor, slot = first_slot(client, token)
    payload = {"specialty": result["specialty_code"], "doctor_id": doctor["doctor_id"], "slot_date": slot["date"], "slot_time": slot["time"], "source": result["source"]}
    held = client.post("/v1/bookings/hold", json=payload, headers=headers(token)).json()
    next_slot = doctor["slots"][1]
    attempt = client.post("/v1/bookings/hold", json={**payload, "slot_date": next_slot["date"], "slot_time": next_slot["time"], "parent_id": held["id"]}, headers=headers(other_token))
    assert attempt.status_code == 404
    own_attempt = client.post("/v1/bookings/hold", json={**payload, "slot_date": next_slot["date"], "slot_time": next_slot["time"], "parent_id": held["id"]}, headers=headers(token))
    assert own_attempt.status_code == 409
