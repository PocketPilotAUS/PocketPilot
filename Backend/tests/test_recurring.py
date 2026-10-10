from datetime import date
from uuid import uuid4
from conftest import register_user, login_user, auth_headers
from app.routers.recurring import sync_recurring, due_date
from app.models.transaction import Transaction
from app.models.recurring import RecurringExpense


def test_month_end():
    assert due_date(2027, 2, 31) == date(2027, 2, 28)
    assert due_date(2028, 2, 31) == date(2028, 2, 29)
    assert due_date(2027, 4, 31) == date(2027, 4, 30)


def test_schedule_catchup_edits_and_stop(api_client, db_session, monkeypatch):
    monkeypatch.setattr('app.routers.recurring.today_local', lambda: date(2027, 1, 31))
    headers = []
    for email in ['alice@example.com','bob@example.com']:
        register_user(api_client,email=email)
        headers.append(auth_headers(login_user(api_client,email=email).json()['access_token']))
    alice,bob = headers
    body = {'amount':'100.25','category':'Rent','description':'Monthly','day':31,'request_key':str(uuid4())}
    assert api_client.post('/recurring/',json=body).status_code == 401
    response = api_client.post('/recurring/',headers=alice,json=body)
    assert response.status_code == 201
    schedule_id=response.json()['id']
    assert response.json()['next_date']=='2027-02-28'
    assert api_client.post('/recurring/',headers=alice,json=body).json()['id']==schedule_id
    assert db_session.query(Transaction).count()==1
    assert api_client.get('/recurring/',headers=bob).json()==[]
    monkeypatch.setattr('app.routers.recurring.today_local',lambda: date(2027,4,30))
    rows=api_client.get('/transactions/',headers=alice).json()
    assert [row['date'] for row in rows]==['2027-01-31','2027-02-28','2027-03-31','2027-04-30']
    assert api_client.get('/transactions/',headers=alice).json()==rows
    payload={'amount':'200','category':'Housing','description':'Monthly','day':15}
    assert api_client.put(f'/recurring/{schedule_id}',headers=bob,json=payload).status_code==404
    result=api_client.put(f'/recurring/{schedule_id}',headers=alice,json=payload)
    assert result.status_code==200 and result.json()['next_date']=='2027-05-15'
    assert db_session.query(Transaction).filter(Transaction.amount==100.25).count()==4
    monkeypatch.setattr('app.routers.recurring.today_local',lambda: date(2027,5,15))
    rows=api_client.get('/transactions/',headers=alice).json()
    assert rows[-1]['amount']==200 and rows[-1]['category']=='Housing'
    assert api_client.post(f'/recurring/{schedule_id}/stop',headers=bob).status_code==404
    assert api_client.post(f'/recurring/{schedule_id}/stop',headers=alice).status_code==200
    monkeypatch.setattr('app.routers.recurring.today_local',lambda: date(2027,7,31))
    assert len(api_client.get('/transactions/',headers=alice).json())==5
    # Deleting an occurrence must not cause it to be regenerated.
    api_client.delete(f"/transactions/{rows[-1]['id']}",headers=alice)
    assert len(api_client.get('/transactions/',headers=alice).json())==4
