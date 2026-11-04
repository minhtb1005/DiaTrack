from src.auth.db import create_user
from src.auth.security import create_access_token, hash_password


def headers(token): return {"Authorization": f"Bearer {token}"}


def coordinator():
    user = create_user(f"coord_{__import__('uuid').uuid4().hex[:8]}", None, hash_password("Test@123"), None, "receptionist", is_verified=True)
    return user, create_access_token({"sub": user["id"], "role": "receptionist"})


def first_slot(client, token, need="nội tiết"):
    result = client.post("/v1/bookings/suggest", json={"need": need}, headers=headers(token)).json()
    doctor = result["suggestions"][0]
    slot = doctor["slots"][0]
    return result, doctor, slot
