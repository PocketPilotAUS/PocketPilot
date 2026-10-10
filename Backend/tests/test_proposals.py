import json
from conftest import register_user, login_user, auth_headers


def test_proposal_requires_confirmation_and_is_idempotent(api_client, monkeypatch):
    headers = []
    for email in ['alice@example.com', 'bob@example.com']:
        register_user(api_client, email=email)
        headers.append(auth_headers(login_user(api_client, email=email).json()['access_token']))
    alice, bob = headers
    action = {'kind': 'expense', 'amount': '3000.00', 'category': 'Rent', 'date': '2026-10-10'}
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({'reply': 'Please confirm this payment.', 'action': action}))
    response = api_client.post('/ai/chat', headers=alice, json={'messages': [{'role': 'user', 'content': 'I paid AED 3000 rent today'}]})
    assert response.status_code == 200
    proposal = response.json()['proposal']
    assert api_client.get('/transactions/', headers=alice).json() == []
    path = '/ai/proposals/' + proposal['id'] + '/confirm'
    assert api_client.post(path).status_code == 401
    assert api_client.post(path, headers=bob).status_code == 404
    assert api_client.post(path, headers=alice).status_code == 200
    assert api_client.post(path, headers=alice).status_code == 200
    rows = api_client.get('/transactions/', headers=alice).json()
    assert len(rows) == 1 and rows[0]['amount'] == 3000
    assert api_client.get('/budget/monthly?year=2026&month=10', headers=alice).json()['spent'] == 3000
    assert api_client.get('/transactions/', headers=bob).json() == []


def test_income_and_dismissal(api_client, monkeypatch):
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()['access_token'])
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({'reply': 'Confirm income', 'action': {'kind': 'income', 'amount': 8000, 'year': 2026, 'month': 10}}))
    def propose():
        return api_client.post('/ai/chat', headers=headers, json={'messages': [{'role': 'user', 'content': 'Monthly income is AED 8000'}]}).json()['proposal']['id']
    proposal = propose()
    assert api_client.get('/budget/monthly?year=2026&month=10', headers=headers).json()['income'] is None
    assert api_client.post('/ai/proposals/'+proposal+'/dismiss', headers=headers).status_code == 200
    assert api_client.post('/ai/proposals/'+proposal+'/confirm', headers=headers).status_code == 409
    proposal = propose()
    assert api_client.post('/ai/proposals/'+proposal+'/confirm', headers=headers).status_code == 200
    assert api_client.get('/budget/monthly?year=2026&month=10', headers=headers).json()['income'] == 8000
