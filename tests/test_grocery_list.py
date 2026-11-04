def test_grocery_list_uses_approved_version(client, make_user, doctor_user):
    patient, token = make_user()
    ph = {"Authorization": f"Bearer {token}"}
    dh = {"Authorization": f"Bearer {doctor_user['token']}"}
    plan = client.post("/v1/nutrition/meal-plans", json={"patient_id": patient["id"], "scenario": "tet", "foods": [{"food_id": "BEV004", "grams": 70}]}, headers=ph).json()
    assert client.get(f"/v1/nutrition/meal-plans/{plan['id']}/grocery-list", headers=ph).status_code == 409
    client.post(f"/v1/nutrition/meal-plans/{plan['id']}/approve", headers=dh)
    result = client.get(f"/v1/nutrition/meal-plans/{plan['id']}/grocery-list", headers=ph)
    assert result.status_code == 200
    assert result.json()["items"] == [{"food_id": "BEV004", "name": "Nước mía", "grams": 70.0, "nutrition_known": True}]
