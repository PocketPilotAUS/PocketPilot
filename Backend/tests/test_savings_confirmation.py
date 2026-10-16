from datetime import date
from uuid import uuid4
from test_savings import headers, setup, BODY
from app.models.income import MonthlyIncome
from app.models.savings import MonthlySavings


def total(client, auth, year=2020, month=1):
    return client.get(f"/savings?year={year}&month={month}", headers=auth).json()


def test_reviewed_amount_is_confirmed_and_replaces_on_correction(api_client, db_session):
    auth = setup(api_client, db_session)
    row = api_client.put("/savings/confirm", json={**BODY, "actual_saved": 2000}, headers=auth).json()
    assert row["saved"] == 2000 and row["leftover"] == 3000
    assert total(api_client, auth)["total_saved"] == 2000
    # Confirming the same month again corrects it; it is never added twice.
    assert api_client.put("/savings/confirm", json={**BODY, "actual_saved": 2500}, headers=auth).json()["saved"] == 2500
    assert total(api_client, auth)["total_saved"] == 2500
    assert db_session.query(MonthlySavings).count() == 1


def test_confirmed_amount_cannot_exceed_calculated_savings(api_client, db_session):
    auth = setup(api_client, db_session)
    response = api_client.put("/savings/confirm", json={**BODY, "actual_saved": 3000.01}, headers=auth)
    assert response.status_code == 422 and "extra savings" in response.json()["detail"]
    assert db_session.query(MonthlySavings).count() == 0
    assert api_client.put("/savings/confirm", json={**BODY, "actual_saved": -1}, headers=auth).status_code == 422


def test_month_can_be_confirmed_only_after_it_ends(api_client, db_session, monkeypatch):
    auth = headers(api_client)
    db_session.add(MonthlyIncome(user_id=1, year=2026, month=10, amount_cents=1000000))
    db_session.commit()
    october = {"year": 2026, "month": 10, "expected_income": 10000, "expected_spent": 0, "extra_debt_payments": 0}
    monkeypatch.setattr("app.routers.savings.today", lambda: date(2026, 10, 16))
    assert total(api_client, auth, 2026, 10)["can_confirm"] is False
    assert api_client.put("/savings/confirm", json=october, headers=auth).status_code == 422
    monkeypatch.setattr("app.routers.savings.today", lambda: date(2026, 10, 31))
    assert api_client.put("/savings/confirm", json=october, headers=auth).status_code == 422
    monkeypatch.setattr("app.routers.savings.today", lambda: date(2026, 11, 1))
    assert total(api_client, auth, 2026, 10)["can_confirm"] is True
    assert api_client.put("/savings/confirm", json=october, headers=auth).json()["saved"] == 10000
    # Future months are never confirmable.
    assert api_client.put("/savings/confirm", json={**october, "month": 12}, headers=auth).status_code == 422


def test_extra_savings_do_not_change_income_or_spending(api_client, db_session):
    auth = setup(api_client, db_session)
    before = total(api_client, auth)
    api_client.post("/savings/manual", headers=auth, json={"label": "Work bonus", "amount": 500, "request_key": str(uuid4())})
    after = total(api_client, auth)
    assert after["total_saved"] == before["total_saved"] + 500
    assert (after["income"], after["spent"], after["debt_payments"]) == (before["income"], before["spent"], before["debt_payments"])
