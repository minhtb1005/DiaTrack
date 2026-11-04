def h(token): return {"Authorization": f"Bearer {token}"}


def test_profile_is_private_and_allergy_blocks_food(client, make_user):
    patient, token = make_user()
    other, other_token = make_user()
    saved = client.put("/v1/nutrition/profile", json={"allergies": ["trà sữa"], "preferences": ["ăn chay"]}, headers=h(token))
    assert saved.status_code == 200
    assert client.get(f"/v1/nutrition/profile/{patient['id']}", headers=h(other_token)).status_code == 403
    blocked = client.post("/v1/nutrition/meal-plans", json={"patient_id": patient["id"], "foods": [{"food_id": "BEV001", "grams": 100}]}, headers=h(token))
    assert blocked.status_code == 409
    unknown = client.get(f"/v1/nutrition/profile/{other['id']}", headers=h(other_token)).json()
    assert unknown["confirmed_no_allergies"] is False and unknown["status"] == "unknown"
