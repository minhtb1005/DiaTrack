"""Clinician-entered medication schedules. No prescribing or dose inference."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from src.auth.dependencies import get_current_user, require_role, enforce_user_ownership
from src.auth.db import get_user_by_id
from src.auth.db import create_notification

DB_PATH = Path(os.getenv('MEDICATION_DB_PATH', 'metadata/medications.db'))
VN = timezone(timedelta(hours=7))
router = APIRouter(prefix='/v1/medications', tags=['medications'])


@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, doctor_id TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, approved_at TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS doses (plan_id TEXT NOT NULL, due_at TEXT NOT NULL, status TEXT NOT NULL, recorded_at TEXT NOT NULL, actor_id TEXT NOT NULL, PRIMARY KEY(plan_id,due_at))')
        conn.execute('CREATE TABLE IF NOT EXISTS plan_events (id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, actor_id TEXT NOT NULL, action TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS reminder_events (plan_id TEXT NOT NULL, due_at TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(plan_id,due_at,kind))')
        yield conn
        conn.commit()
    finally:
        conn.close()


class Plan(BaseModel):
    patient_id: str = Field(min_length=1, max_length=100)
    medicine: str = Field(min_length=1, max_length=200)
    prescribed_dose: str = Field(min_length=1, max_length=300)
    prescription_reference: str = Field(min_length=1, max_length=300)
    times: list[str] = Field(min_length=1, max_length=6)
    start_date: date
    end_date: date

    @field_validator('medicine', 'prescribed_dose', 'prescription_reference')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Không được để trống')
        return value.strip()

    @field_validator('times')
    @classmethod
    def valid_times(cls, values):
        import re
        if any(not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', v) for v in values):
            raise ValueError('Giờ phải có dạng HH:MM (giờ Việt Nam)')
        if len(set(values)) != len(values):
            raise ValueError('Giờ nhắc không được trùng')
        return sorted(values)

    @model_validator(mode='after')
    def valid_period(self):
        if not 0 <= (self.end_date-self.start_date).days <= 90:
            raise ValueError('Khoảng lịch phải từ 1 đến 91 ngày')
        return self


class DoseRecord(BaseModel):
    due_at: datetime
    status: Literal['taken', 'skipped']

    @field_validator('due_at')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError('Cần múi giờ cho thời điểm uống thuốc')
        return value


def occurrences(payload):
    start = date.fromisoformat(payload['start_date'])
    end = date.fromisoformat(payload['end_date'])
    for offset in range((end-start).days+1):
        for hour in payload['times']:
            yield datetime.combine(start+timedelta(days=offset), time.fromisoformat(hour), VN).isoformat()


def send_due_reminders(now: datetime | None = None) -> int:
    """Create one in-app reminder per due occurrence; scheduler calls this function."""
    now = (now or datetime.now(timezone.utc)).astimezone(VN)
    sent = 0
    with connection() as conn:
        for row in conn.execute("SELECT id,patient_id,payload FROM plans WHERE status='approved'"):
            payload = json.loads(row['payload'])
            recorded = {item['due_at'] for item in conn.execute('SELECT due_at FROM doses WHERE plan_id=?', (row['id'],))}
            for due_at in occurrences(payload):
                if due_at in recorded or datetime.fromisoformat(due_at) > now:
                    continue
                try:
                    conn.execute('INSERT INTO reminder_events VALUES (?,?,?,?)',
                                 (row['id'], due_at, 'due', datetime.now(timezone.utc).isoformat()))
                except sqlite3.IntegrityError:
                    continue
                create_notification(row['patient_id'], 'medication_due', 'Đến giờ xác nhận dùng thuốc',
                                    f"{payload['medicine']} lúc {due_at}. Xác nhận đã dùng hoặc bỏ liều; không tự uống bù.", row['id'])
                sent += 1
    return sent


@router.post('/reminders/run')
def run_reminders(admin=Depends(require_role('admin'))):
    return {'sent': send_due_reminders()}


def get_plan(conn, plan_id):
    row = conn.execute('SELECT * FROM plans WHERE id=?', (plan_id,)).fetchone()
    if row is None:
        raise HTTPException(404, 'Không tìm thấy lịch thuốc')
    return dict(row)


@router.post('/plans', status_code=201)
def create_plan(body: Plan, doctor=Depends(require_role('doctor'))):
    patient = get_user_by_id(body.patient_id)
    if not patient or patient['role'] != 'user':
        raise HTTPException(404, 'Không tìm thấy bệnh nhân')
    plan_id = str(uuid.uuid4())
    with connection() as conn:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute('INSERT INTO plans VALUES (?,?,?,?,?,?,NULL)', (plan_id,body.patient_id,doctor['id'],'draft',body.model_dump_json(),now))
        conn.execute('INSERT INTO plan_events VALUES (?,?,?,?,?,?)',
                     (str(uuid.uuid4()), plan_id, doctor['id'], 'created', 'Tạo bản nháp từ đơn đã nhập', now))
    return {'id':plan_id, 'status':'draft'}


@router.post('/plans/{plan_id}/approve')
def approve_plan(plan_id: str, doctor=Depends(require_role('doctor'))):
    with connection() as conn:
        plan = get_plan(conn,plan_id)
        if plan['doctor_id'] != doctor['id']:
            raise HTTPException(403, 'Chỉ bác sĩ tạo lịch được duyệt lịch này')
        if plan['status'] != 'draft':
            raise HTTPException(409, 'Lịch đã được duyệt')
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE plans SET status='approved',approved_at=? WHERE id=?", (now,plan_id))
        conn.execute('INSERT INTO plan_events VALUES (?,?,?,?,?,?)',
                     (str(uuid.uuid4()), plan_id, doctor['id'], 'approved', 'Bác sĩ duyệt lịch theo đơn', now))
    return {'id':plan_id,'status':'approved'}


@router.get('/patients/{patient_id}')
def list_plans(patient_id: str, user=Depends(get_current_user)):
    enforce_user_ownership(patient_id,user)
    now = datetime.now(VN)
    with connection() as conn:
        plans = conn.execute('SELECT * FROM plans WHERE patient_id=? ORDER BY created_at DESC',(patient_id,)).fetchall()
        if user['role'] == 'doctor':
            plans = [row for row in plans if row['doctor_id'] == user['id']]
        result=[]
        for row in plans:
            plan=dict(row)
            if user['role']=='user' and plan['status']=='draft':
                continue
            payload=json.loads(plan.pop('payload'))
            saved={r['due_at']:dict(r) for r in conn.execute('SELECT * FROM doses WHERE plan_id=?',(plan['id'],))}
            schedule=[]
            if plan['status']=='approved':
                for due in occurrences(payload):
                    record=saved.get(due)
                    schedule.append({'due_at':due,'status':record['status'] if record else ('overdue' if datetime.fromisoformat(due)<now else 'scheduled')})
            due_count=sum(datetime.fromisoformat(r['due_at'])<=now for r in schedule)
            taken=sum(r['status']=='taken' and datetime.fromisoformat(r['due_at'])<=now for r in schedule)
            missed_streak = current_streak = 0
            for item in sorted((r for r in schedule if datetime.fromisoformat(r['due_at']) <= now), key=lambda r: r['due_at']):
                current_streak = current_streak + 1 if item['status'] == 'skipped' else 0
                missed_streak = max(missed_streak, current_streak)
            events=[dict(r) for r in conn.execute('SELECT actor_id,action,reason,created_at FROM plan_events WHERE plan_id=? ORDER BY created_at', (plan['id'],))]
            result.append({**plan,**payload,'events':events,'schedule':schedule,'adherence':{'due':due_count,'taken':taken,'rate':taken/due_count if due_count else None,'missed_streak':missed_streak}})
    glucose_logs = []
    if user['role'] == 'doctor' and result:
        from src.diabetes.glucose_tracker import get_logs
        glucose_logs = get_logs(patient_id, limit=50, days=90)
    return {'plans':result,'glucose_logs':glucose_logs,'timezone':'Asia/Ho_Chi_Minh','disclaimer':'Tỷ lệ và dữ liệu đường huyết chỉ để đối chiếu; không chứng minh hiệu quả thuốc và không phải đề xuất đổi liều. Không tự đổi liều hoặc uống bù.'}


@router.post('/plans/{plan_id}/doses')
def record_dose(plan_id: str, body: DoseRecord, user=Depends(get_current_user)):
    due=body.due_at.astimezone(VN).isoformat()
    with connection() as conn:
        plan=get_plan(conn,plan_id)
        if user['role']!='user' or plan['patient_id']!=user['id']:
            raise HTTPException(403,'Chỉ bệnh nhân xác nhận việc dùng thuốc của mình')
        if plan['status']!='approved':
            raise HTTPException(409,'Lịch chưa được bác sĩ duyệt')
        if due not in set(occurrences(json.loads(plan['payload']))):
            raise HTTPException(422,'Thời điểm không thuộc lịch đã duyệt')
        if body.due_at > datetime.now(timezone.utc):
            raise HTTPException(422,'Chưa tới giờ xác nhận liều này')
        try:
            conn.execute('INSERT INTO doses VALUES (?,?,?,?,?)',(plan_id,due,body.status,datetime.now(timezone.utc).isoformat(),user['id']))
        except sqlite3.IntegrityError:
            raise HTTPException(409,'Liều này đã được ghi nhận; liên hệ bác sĩ nếu cần sửa')
    return {'status':body.status,'due_at':due}

class StopPlan(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator('reason')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Cần ghi lý do dừng lịch')
        return value.strip()


@router.post('/plans/{plan_id}/stop')
def stop_plan(plan_id: str, body: StopPlan, doctor=Depends(require_role('doctor'))):
    with connection() as conn:
        plan = get_plan(conn, plan_id)
        if plan['doctor_id'] != doctor['id']:
            raise HTTPException(403, 'Chỉ bác sĩ tạo lịch được dừng lịch này')
        if plan['status'] != 'approved':
            raise HTTPException(409, 'Chỉ dừng lịch đang áp dụng')
        conn.execute("UPDATE plans SET status='stopped' WHERE id=?", (plan_id,))
        conn.execute('INSERT INTO plan_events VALUES (?,?,?,?,?,?)',
                     (str(uuid.uuid4()), plan_id, doctor['id'], 'stopped', body.reason, datetime.now(timezone.utc).isoformat()))
    return {'id': plan_id, 'status': 'stopped'}
