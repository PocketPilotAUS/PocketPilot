from conftest import register_user, login_user, auth_headers


def test_ideal_budget_targets_customization_and_actuals(api_client):
    from app.routers.budget import DEFAULT_PERCENTAGES
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()['access_token'])
    url = '?year=2026&month=10'
    empty = api_client.get('/budget/monthly' + url, headers=headers).json()
    assert all(row['target'] is None for row in empty['ideal_budget']['allocations'])
    api_client.post('/transactions/', headers=headers, json={'amount': 2500, 'category': 'Rent', 'date': '2026-10-01'})
    api_client.post('/transactions/', headers=headers, json={'amount': 80, 'category': 'Groceries', 'date': '2026-10-01'})
    result = api_client.put('/budget/income' + url, headers=headers, json={'amount': 8500}).json()
    rows = {row['category']: row for row in result['ideal_budget']['allocations']}
    assert rows['Rent']['target'] == 2550
    assert rows['Rent']['spent'] == 2500
    assert rows['Food']['spent'] == 80
    assert sum(row['target'] for row in rows.values()) == 8500
    percentages = dict(DEFAULT_PERCENTAGES, Rent=35, Shopping=5)
    saved = api_client.put('/budget/plan' + url, headers=headers, json={'percentages': percentages})
    assert saved.status_code == 200
    assert saved.json()['ideal_budget']['customized'] is True
    assert saved.json()['ideal_budget']['allocations'][0]['target'] == 2975
    assert api_client.get('/budget/monthly?year=2026&month=11', headers=headers).json()['ideal_budget']['customized'] is False
    register_user(api_client, email='other@example.com')
    other = auth_headers(login_user(api_client, email='other@example.com').json()['access_token'])
    assert api_client.get('/budget/monthly' + url, headers=other).json()['ideal_budget']['customized'] is False
    percentages['Rent'] = 36
    assert api_client.put('/budget/plan' + url, headers=headers, json={'percentages': percentages}).status_code == 422
    percentages['Rent'] = True
    assert api_client.put('/budget/plan' + url, headers=headers, json={'percentages': percentages}).status_code == 422


def test_monthly_income_and_spending_are_isolated(api_client):
    headers = []
    for email in ["alice@example.com", "bob@example.com"]:
        register_user(api_client, email=email)
        headers.append(auth_headers(login_user(api_client, email=email).json()["access_token"]))
    alice, bob = headers
    assert api_client.get('/budget/monthly?year=2026&month=10').status_code == 401
    empty = api_client.get('/budget/monthly?year=2026&month=10', headers=alice).json()
    assert empty['income'] is None
    for amount, date in [(150, '2026-10-01'), (50, '2026-09-01')]:
        api_client.post('/transactions/', headers=alice, json={'amount': amount, 'category': 'Food', 'date': date})
    response = api_client.put('/budget/income?year=2026&month=10', headers=alice, json={'amount': '100.00'})
    assert response.status_code == 200
    assert response.json()['spent'] == 150
    assert response.json()['remaining'] == -50
    assert response.json()['spent_percentage'] == 150
    assert api_client.get('/budget/monthly?year=2026&month=10', headers=bob).json()['income'] is None
    response = api_client.put('/budget/income?year=2026&month=10', headers=alice, json={'amount': '200.25'})
    assert response.json()['remaining'] == 50.25
    assert api_client.get('/budget/monthly?year=2026&month=10', headers=alice).json()['income'] == 200.25
    assert api_client.get('/budget/monthly?year=2026&month=11', headers=alice).json()['income'] is None
    assert api_client.put('/budget/income?year=2026&month=10', headers=alice, json={'amount': -1}).status_code == 422
    assert api_client.put('/budget/income?year=2026&month=10', headers=alice, json={'amount': '1.001'}).status_code == 422
    zero = api_client.put('/budget/income?year=2026&month=10', headers=alice, json={'amount': 0}).json()
    assert zero['spent_percentage'] is None
    assert zero['remaining'] == -150
