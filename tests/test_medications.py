from datetime import datetime, timedelta, timezone
import pytest


@pytest.fixture(autouse=True)
def isolated_medications(monkeypatch, tmp_path):
    import src.medications.router as module
    monkeypatch.setattr(module, 'DB_PATH', tmp_path / 'medications.db')


def headers(token):
    return {'Authorization': 'Bearer ' + token}


def prescription(patient):
    today=datetime.now(timezone(timedelta(hours=7))).date().isoformat()
    return {'patient_id':patient['id'],'medicine':'Thuốc mô phỏng','prescribed_dose':'Theo đơn mô phỏng đã nhập','prescription_reference':'TEST-ONLY-001','times':['00:00'],'start_date':today,'end_date':today}


def test_approval_ownership_and_single_confirmation(client, make_user, doctor_user):
    patient,token=make_user()
    other,other_token=make_user()
    body=prescription(patient)
    assert client.post('/v1/medications/plans',json=body,headers=headers(token)).status_code==403
    response=client.post('/v1/medications/plans',json=body,headers=headers(doctor_user['token']))
    assert response.status_code==201,response.text
    plan_id=response.json()['id']
    path='/v1/medications/patients/'+patient['id']
    assert client.get(path,headers=headers(token)).json()['plans']==[]
    assert client.get(path,headers=headers(other_token)).status_code==403
    approval='/v1/medications/plans/'+plan_id+'/approve'
    assert client.post(approval,headers=headers(token)).status_code==403
    assert client.post(approval,headers=headers(doctor_user['token'])).status_code==200
    assert client.post(approval,headers=headers(doctor_user['token'])).status_code==409
    plan=client.get(path,headers=headers(token)).json()['plans'][0]
    dose={'due_at':plan['schedule'][0]['due_at'],'status':'taken'}
    dose_path='/v1/medications/plans/'+plan_id+'/doses'
    assert client.post(dose_path,json=dose,headers=headers(other_token)).status_code==403
    assert client.post(dose_path,json=dose,headers=headers(token)).status_code==200
    assert client.post(dose_path,json=dose,headers=headers(token)).status_code==409
    assert client.get(path,headers=headers(token)).json()['plans'][0]['adherence']['rate']==1


@pytest.mark.parametrize('change',[{'times':['25:00']},{'times':['08:00','08:00']},{'medicine':'  '},{'end_date':'2000-01-01'}])
def test_invalid_schedule(client,make_user,doctor_user,change):
    patient,_=make_user()
    response=client.post('/v1/medications/plans',json={**prescription(patient),**change},headers=headers(doctor_user['token']))
    assert response.status_code==422,response.text


def test_future_and_unapproved_doses_rejected(client,make_user,doctor_user):
    patient,token=make_user()
    body=prescription(patient)
    tomorrow=(datetime.now(timezone(timedelta(hours=7))).date()+timedelta(days=1)).isoformat()
    body.update(start_date=tomorrow,end_date=tomorrow)
    plan_id=client.post('/v1/medications/plans',json=body,headers=headers(doctor_user['token'])).json()['id']
    dose={'due_at':tomorrow+'T00:00:00+07:00','status':'taken'}
    path='/v1/medications/plans/'+plan_id
    assert client.post(path+'/doses',json=dose,headers=headers(token)).status_code==409
    client.post(path+'/approve',headers=headers(doctor_user['token']))
    assert client.post(path+'/doses',json=dose,headers=headers(token)).status_code==422
    dose['due_at']='2000-01-01T00:00:00+07:00'
    assert client.post(path+'/doses',json=dose,headers=headers(token)).status_code==422

def test_doctor_stops_schedule_preserving_history(client, make_user, doctor_user):
    patient, token = make_user()
    plan_id = client.post('/v1/medications/plans', json=prescription(patient), headers=headers(doctor_user['token'])).json()['id']
    path = '/v1/medications/plans/' + plan_id
    client.post(path+'/approve', headers=headers(doctor_user['token']))
    listing = '/v1/medications/patients/' + patient['id']
    due = client.get(listing, headers=headers(token)).json()['plans'][0]['schedule'][0]['due_at']
    assert client.post(path+'/stop', json={'reason':'Đổi đơn'}, headers=headers(token)).status_code == 403
    assert client.post(path+'/stop', json={'reason':' '}, headers=headers(doctor_user['token'])).status_code == 422
    assert client.post(path+'/stop', json={'reason':'Đơn mô phỏng đã kết thúc'}, headers=headers(doctor_user['token'])).status_code == 200
    stopped = client.get(listing, headers=headers(token)).json()['plans'][0]
    assert stopped['status'] == 'stopped'
    assert stopped['schedule'] == []
    assert [event['action'] for event in stopped['events']] == ['created', 'approved', 'stopped']
    assert stopped['events'][-1]['reason'] == 'Đơn mô phỏng đã kết thúc'
    assert client.post(path+'/doses', json={'due_at':due,'status':'taken'}, headers=headers(token)).status_code == 409


def test_other_doctor_cannot_approve_or_stop_and_audit_is_preserved(client, make_user, doctor_user, admin_client):
    patient, token = make_user()
    username = 'doc_other_' + patient['id'][:6]
    password = 'OtherDoc@123'
    created = client.post('/v1/auth/register', json={'username':username, 'password':password, 'role':'doctor'},
                          headers=headers(admin_client['token']))
    assert created.status_code in (200, 201), created.text
    login = client.post('/v1/auth/login-json', json={'username':username, 'password':password})
    other_token = login.json()['access_token']

    response = client.post('/v1/medications/plans', json=prescription(patient), headers=headers(doctor_user['token']))
    plan_id = response.json()['id']
    path = '/v1/medications/plans/' + plan_id
    assert client.post(path+'/approve', headers=headers(other_token)).status_code == 403
    assert client.post(path+'/approve', headers=headers(doctor_user['token'])).status_code == 200
    assert client.post(path+'/stop', json={'reason':'Không có quyền'}, headers=headers(other_token)).status_code == 403

    patient_plan = client.get('/v1/medications/patients/'+patient['id'], headers=headers(token)).json()['plans'][0]
    assert patient_plan['status'] == 'approved'
    assert [event['action'] for event in patient_plan['events']] == ['created', 'approved']
    assert all(event['actor_id'] == doctor_user['user']['id'] for event in patient_plan['events'])


def test_due_reminder_is_outside_page_and_idempotent(client, make_user, doctor_user, admin_client):
    patient, token = make_user()
    plan_id = client.post('/v1/medications/plans', json=prescription(patient), headers=headers(doctor_user['token'])).json()['id']
    client.post('/v1/medications/plans/'+plan_id+'/approve', headers=headers(doctor_user['token']))
    run = '/v1/medications/reminders/run'
    assert client.post(run, headers=headers(token)).status_code == 403
    assert client.post(run, headers=headers(admin_client['token'])).json()['sent'] == 1
    assert client.post(run, headers=headers(admin_client['token'])).json()['sent'] == 0
    notifications = client.get('/v1/auth/notifications', headers=headers(token)).json()['notifications']
    matching = [item for item in notifications if item['type'] == 'medication_due']
    assert len(matching) == 1
    assert 'không tự uống bù' in matching[0]['body']
