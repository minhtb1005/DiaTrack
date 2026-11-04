from datetime import datetime, timedelta, timezone
import pytest


@pytest.fixture(autouse=True)
def isolated_medications(monkeypatch, tmp_path):
    import src.medications.router as module
    monkeypatch.setattr(module, 'DB_PATH', tmp_path / 'medications.db')


def headers(token):
    return {'Authorization': 'Bearer ' + token}


def prescription(patient):
    today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
    return {'patient_id':patient['id'], 'medicine':'Thuốc mô phỏng', 'prescribed_dose':'Theo đơn mô phỏng đã nhập',
            'prescription_reference':'TEST-ONLY-001', 'times':['00:00'], 'start_date':today, 'end_date':today}


def test_doctor_sees_exact_adherence_and_glucose_without_dose_inference(client, make_user, doctor_user):
    patient, token = make_user()
    body = prescription(patient)
    plan_id = client.post('/v1/medications/plans', json=body, headers=headers(doctor_user['token'])).json()['id']
    client.post(f'/v1/medications/plans/{plan_id}/approve', headers=headers(doctor_user['token']))
    patient_view = client.get(f'/v1/medications/patients/{patient["id"]}', headers=headers(token)).json()
    due_at = patient_view['plans'][0]['schedule'][0]['due_at']
    client.post(f'/v1/medications/plans/{plan_id}/doses', json={'due_at':due_at, 'status':'skipped'}, headers=headers(token))
    measured = datetime.now(timezone.utc) - timedelta(hours=1)
    client.post('/v1/glucose', json={'user_id':patient['id'], 'value_mgdl':180, 'measured_at':measured.isoformat(), 'context':'random'}, headers=headers(token))

    report = client.get(f'/v1/medications/patients/{patient["id"]}', headers=headers(doctor_user['token'])).json()
    adherence = report['plans'][0]['adherence']
    assert adherence == {'due':1, 'taken':0, 'rate':0, 'missed_streak':1}
    assert report['glucose_logs'][0]['value_mgdl'] == 180
    assert 'không chứng minh hiệu quả thuốc' in report['disclaimer']
    assert 'không phải đề xuất đổi liều' in report['disclaimer']
