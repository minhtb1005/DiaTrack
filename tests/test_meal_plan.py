def test_meal_plan_has_scaled_sourced_values_and_unknown_is_not_invented(client, make_user):
    patient, token = make_user()
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/v1/nutrition/profile", json={"allergies": [], "preferences": []}, headers=headers)
    response = client.post("/v1/nutrition/meal-plans", json={"patient_id": patient["id"], "foods": [{"food_id": "BEV002", "grams": 200}, {"food_id": "MISSING", "grams": 50}]}, headers=headers)
    assert response.status_code == 200, response.text
    meals = response.json()["meals"]
    assert meals[0]["nutrition"]["energy_kcal"] == 84.0 and meals[0]["source"]
    assert meals[1]["nutrition"] is None and meals[1]["status"] == "unknown"
    assert response.json()["status"] == "draft"
