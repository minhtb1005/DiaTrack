from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.auth.dependencies import get_current_user, require_role
from src.care_store import connect, dump, load, now, row, uid
from src.diabetes.nutrition_lookup import _load_foods

router = APIRouter(prefix="/v1/nutrition", tags=["nutrition-workflow"])


class ProfileIn(BaseModel):
    allergies: list[str] = []
    preferences: list[str] = []
    confirmed_no_allergies: bool = False


class FoodPortion(BaseModel):
    food_id: str
    grams: float = Field(gt=0, le=5000)


class PlanIn(BaseModel):
    patient_id: str
    foods: list[FoodPortion] = Field(min_length=1)
    scenario: Literal["standard", "tet", "vegetarian"] = "standard"


class MealLogIn(BaseModel):
    patient_id: str
    foods: list[FoodPortion]
    eaten_at: str
    plan_id: str | None = None
    glucose_log_id: int | None = None


def _profile(patient_id: str) -> dict[str, Any] | None:
    with connect() as c:
        p = row(c.execute("SELECT * FROM nutrition_profiles WHERE patient_id=?", (patient_id,)).fetchone())
    if p:
        p["allergies"] = load(p.pop("allergies_json"))
        p["preferences"] = load(p.pop("preferences_json"))
        p["confirmed_no_allergies"] = bool(p["confirmed_no_allergies"])
    return p


def _check_owner(patient_id: str, user: dict[str, Any]) -> None:
    if user["role"] == "user" and patient_id != user["id"]:
        raise HTTPException(403, "Forbidden")


def _resolve_foods(portions: list[FoodPortion], patient_id: str) -> list[dict[str, Any]]:
    foods = {f["food_id"]: f for f in _load_foods()}
    profile = _profile(patient_id)
    allergies = [a.casefold() for a in (profile or {}).get("allergies", [])]
    output = []
    for portion in portions:
        food = foods.get(portion.food_id)
        if not food:
            output.append({"food_id": portion.food_id, "grams": portion.grams, "nutrition": None, "source": None, "status": "unknown"})
            continue
        searchable = " ".join([food["names"].get("vi", ""), food["names"].get("en", ""), *(food["names"].get("aliases_vi") or [])]).casefold()
        blocked = next((a for a in allergies if a and a in searchable), None)
        if blocked:
            raise HTTPException(409, f"Món bị chặn do dị ứng đã khai báo: {blocked}")
        factor = portion.grams / 100
        nutrition = {k: round(float(v) * factor, 2) for k, v in food["nutrition_per_100g"].items()}
        output.append({"food_id": food["food_id"], "name": food["names"]["vi"], "grams": portion.grams, "nutrition": nutrition, "source": food["metadata"]["source"], "status": "known"})
    return output


@router.put("/profile")
def put_profile(payload: ProfileIn, user=Depends(get_current_user)):
    if payload.confirmed_no_allergies and payload.allergies:
        raise HTTPException(422, "Cannot confirm no allergies while listing allergies")
    with connect() as c:
        c.execute("INSERT INTO nutrition_profiles VALUES(?,?,?,?,?) ON CONFLICT(patient_id) DO UPDATE SET allergies_json=excluded.allergies_json,preferences_json=excluded.preferences_json,confirmed_no_allergies=excluded.confirmed_no_allergies,updated_at=excluded.updated_at", (user["id"], dump(payload.allergies), dump(payload.preferences), int(payload.confirmed_no_allergies), now()))
    return _profile(user["id"])


@router.get("/profile/{patient_id}")
def get_profile(patient_id: str, user=Depends(get_current_user)):
    _check_owner(patient_id, user)
    profile = _profile(patient_id)
    return profile or {"patient_id": patient_id, "allergies": [], "preferences": [], "confirmed_no_allergies": False, "status": "unknown"}


@router.post("/meal-plans")
def create_plan(payload: PlanIn, user=Depends(get_current_user)):
    _check_owner(payload.patient_id, user)
    meals = _resolve_foods(payload.foods, payload.patient_id)
    plan_id, created = uid(), now()
    with connect() as c:
        c.execute("INSERT INTO meal_plans VALUES(?,?,?,?,?,?,?,?,?,?)", (plan_id, payload.patient_id, payload.scenario, dump(meals), "draft", 1, user["id"], None, created, None))
    return {"id": plan_id, "patient_id": payload.patient_id, "scenario": payload.scenario, "meals": meals, "status": "draft", "warning": "Bản nháp chờ chuyên gia duyệt; không thay thế chế độ điều trị. Không nhịn ăn hoặc đổi thuốc nếu chưa hỏi bác sĩ."}


@router.post("/meal-plans/{plan_id}/approve")
def approve_plan(plan_id: str, user=Depends(require_role("specialist", "doctor", "admin"))):
    reviewed = now()
    with connect() as c:
        plan = row(c.execute("SELECT * FROM meal_plans WHERE id=?", (plan_id,)).fetchone())
        if not plan:
            raise HTTPException(404, "Meal plan not found")
        if plan["status"] != "draft":
            raise HTTPException(409, "Meal plan already reviewed")
        c.execute("UPDATE meal_plans SET status='approved',reviewed_by=?,reviewed_at=? WHERE id=?", (user["id"], reviewed, plan_id))
    return get_plan(plan_id, user)


@router.get("/meal-plans/{plan_id}")
def get_plan(plan_id: str, user=Depends(get_current_user)):
    with connect() as c:
        plan = row(c.execute("SELECT * FROM meal_plans WHERE id=?", (plan_id,)).fetchone())
    if not plan:
        raise HTTPException(404, "Meal plan not found")
    _check_owner(plan["patient_id"], user)
    plan["meals"] = load(plan.pop("meals_json"))
    return plan


@router.post("/meal-logs")
def create_meal_log(payload: MealLogIn, user=Depends(get_current_user)):
    _check_owner(payload.patient_id, user)
    foods = _resolve_foods(payload.foods, payload.patient_id)
    log_id = uid()
    with connect() as c:
        c.execute("INSERT INTO meal_logs VALUES(?,?,?,?,?,?,?)", (log_id, payload.patient_id, payload.plan_id, dump(foods), payload.eaten_at, payload.glucose_log_id, now()))
    return {"id": log_id, "patient_id": payload.patient_id, "foods": foods, "eaten_at": payload.eaten_at, "glucose_log_id": payload.glucose_log_id, "interpretation": "Liên kết thời điểm chỉ để đối chiếu; không chứng minh nguyên nhân hoặc chẩn đoán."}


@router.get("/meal-plans/{plan_id}/grocery-list")
def grocery_list(plan_id: str, user=Depends(get_current_user)):
    plan = get_plan(plan_id, user)
    if plan["status"] != "approved":
        raise HTTPException(409, "Grocery list requires an approved plan")
    return {"plan_id": plan_id, "version": plan["version"], "items": [{"food_id": x["food_id"], "name": x.get("name", x["food_id"]), "grams": x["grams"], "nutrition_known": x["nutrition"] is not None} for x in plan["meals"]]}
