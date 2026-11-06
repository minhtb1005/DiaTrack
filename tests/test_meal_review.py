def test_expert_approves_and_meal_log_links_only_explicit_glucose(client, make_user, doctor_user):
    patient, token = make_user()
    ph = {"Authorization": f"Bearer {token}"}
    dh = {"Authorization": f"Bearer {doctor_user['token']}"}
    plan = client.post("/v1/nutrition/meal-plans", json={"patient_id": patient["id"], "foods": [{"food_id": "BEV002", "grams": 100}]}, headers=ph).json()
    assert client.post(f"/v1/nutrition/meal-plans/{plan['id']}/approve", headers=ph).status_code == 403
    edited = client.put(f"/v1/nutrition/meal-plans/{plan['id']}", json={"foods": [{"food_id": "BEV002", "grams": 150}]}, headers=dh).json()
    assert edited["version"] == 2 and edited["meals"][0]["grams"] == 150
    assert client.post(f"/v1/nutrition/meal-plans/{plan['id']}/approve", headers=dh).status_code == 200
    meal = client.post("/v1/nutrition/meal-logs", json={"patient_id": patient["id"], "foods": [{"food_id": "BEV002", "grams": 100}], "eaten_at": "2026-11-04T08:00:00+07:00"}, headers=ph).json()
    assert meal["glucose_log_id"] is None and "không chứng minh" in meal["interpretation"]
    listed = client.get(f"/v1/nutrition/meal-logs/{patient['id']}", headers=ph).json()
    assert listed["logs"][0]["id"] == meal["id"] and listed["logs"][0]["foods"][0]["source"]
    rejected = client.post("/v1/nutrition/meal-logs", json={"patient_id": patient["id"], "foods": [{"food_id": "BEV002", "grams": 100}], "eaten_at": "2026-11-04T10:00:00+07:00", "glucose_log_id": 999999}, headers=ph)
    assert rejected.status_code == 422
