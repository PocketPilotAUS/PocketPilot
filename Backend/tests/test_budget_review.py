import json
from datetime import date
from decimal import Decimal
from app.services.budget_review import analyze_history, budget_review_context, clean_review_placeholders, round_displayed_review, format_budget_review
from app.core.currency import display_context
from app.models.transaction import Transaction
from conftest import register_user, login_user, auth_headers


def budget(targets, income=10000):
    return {"year": 2026, "month": 10, "income": income,
            "ideal_budget": {"allocations": [{"category": name, "target": value} for name, value in targets.items()]}}


def test_small_differences_do_not_trigger_changes():
    history = {f"2026-{month:02d}": {"Bills": bills, "Groceries": groceries} for month, bills, groceries in [
        (7, 742.60, 478.35), (8, 708.80, 537.60), (9, 665.90, 521.65)]}
    result = analyze_history(budget({"Bills":700, "Groceries":500}), history)
    assert all(row['status'] == 'within_normal_variation' for row in result['categories'])
    assert result['categories'][0]['average'] == 705.77
    assert result['categories'][1]['average'] == 512.53
    assert result['total_increase'] == 0


def test_high_month_requires_a_question_not_automatic_increase():
    history = {f'2026-{month:02d}': {'Shopping': value} for month, value in [(7,529.4),(8,618.75),(9,462.3)]}
    row = analyze_history(budget({'Shopping':500}), history)['categories'][0]
    assert row['average'] == 536.82
    assert row['status'] == 'ask_if_high_month_was_unusual' and row['high_month'] == '2026-08'
    assert 'suggested_target' not in row


def test_consistent_overrun_rounding_and_affordability():
    history = {f'2026-{month:02d}': {'Shopping': value} for month, value in [(7,530),(8,535.4),(9,545)]}
    result = analyze_history(budget({'Shopping':500}), history)
    row = result['categories'][0]
    assert row['average'] == 536.8 and row['suggested_target'] == 540
    assert row['status'] == 'discuss_increase' and result['proposed_total'] == 540
    constrained = analyze_history(budget({'Shopping':500}, income=1000), history, goal_contributions=480, extra_commitments=30)
    assert constrained['categories'][0]['status'] == 'discuss_affordability'
    assert constrained['available_for_increases'] == 0 and not constrained['increases_fit']


def test_combined_increases_cannot_exceed_available_money():
    history = {f'2026-{month:02d}': {'Shopping':540, 'Entertainment':540} for month in [7,8,9]}
    result = analyze_history(budget({'Shopping':500,'Entertainment':500}, income=1050), history)
    assert result['total_increase'] == 80 and not result['increases_fit']
    assert all(row['status']=='discuss_affordability' for row in result['categories'])


def test_sparse_history_and_missing_income_are_not_zero():
    result = analyze_history(budget({'Shopping':500}, income=None), {'2026-09':{'Shopping':700}})
    assert result['categories'][0]['status'] == 'insufficient_history'
    assert result['increases_fit'] is None
    assert analyze_history(budget({'Food':600}), {})['categories'][0]['status'] == 'insufficient_history'


def test_placeholder_cleanup_preserves_other_text():
    assert clean_review_placeholders('Best, [Your Name] 😊') == 'Best, PocketPilot 😊'
    assert clean_review_placeholders('Hello Karim!') == 'Hello Karim!'


def test_display_currency_rounding_reconciles_total():
    history = {f'2026-{month:02d}': {'Shopping':value} for month,value in [(7,530),(8,535.4),(9,545)]}
    result = display_context(analyze_history(budget({'Shopping':500}, income=1000), history), Decimal('1.94'))
    round_displayed_review(result)
    assert result['categories'][0]['suggested_target'] == 1050
    assert result['planned_total'] + result['total_increase'] == result['proposed_total']
    assert result['remaining_after_proposal'] == 890


def test_review_context_excludes_current_month_and_cannot_save(api_client, db_session, monkeypatch):
    register_user(api_client)
    auth = auth_headers(login_user(api_client).json()['access_token'])
    saved = api_client.put('/budget/setup?year=2026&month=10',headers=auth,json={
        'income':10000,'categories':[{'name':'Shopping','amount':500}]}).json()
    for month, total in [(7,530),(8,535.4),(9,545),(10,9000)]:
        for day in range(1,6):
            db_session.add(Transaction(user_id=1,date=date(2026,month,day),category='Shopping',amount=total/5))
    register_user(api_client, email='bob@example.com')
    db_session.add(Transaction(user_id=2,date=date(2026,9,1),category='Shopping',amount=99999))
    db_session.commit()
    result = budget_review_context(db_session,1,saved,date(2026,10,17))
    assert result['history_months'] == ['2026-07','2026-08','2026-09']
    assert result['categories'][0]['average'] == 536.8
    def generate(messages):
        raise AssertionError("Verified budget reviews must not call the model")
    monkeypatch.setattr('app.routers.chat.generate_chat_reply',generate)
    response=api_client.post('/ai/chat',headers=auth,json={'review_budget':{'year':2026,'month':10},'messages':[{'role':'user','content':'Review my budget'}]})
    assert response.status_code == 200
    reply = response.json()['reply']
    assert 'AED 536.80 average' in reply and 'Budget AED 500.00' in reply
    assert 'AED 540.00' in reply and reply.count('?') == 1
    assert not any(token in reply for token in ['**', '`', '----', '[Your Name]', '|'])
    assert response.json()['proposal'] is None and response.json()['plan'] is None
    assert api_client.get('/budget/monthly?year=2026&month=10',headers=auth).json()['ideal_budget']['allocations'][0]['target']==500


def test_goal_and_recurring_commitments_reduce_affordability_without_double_counting(api_client, db_session):
    from app.models.recurring import RecurringExpense
    from app.models.financial_plan import FinancialPlan
    from uuid import uuid4
    register_user(api_client)
    auth = auth_headers(login_user(api_client).json()['access_token'])
    saved = api_client.put('/budget/setup?year=2026&month=10',headers=auth,json={
        'income':5000,'categories':[{'name':'Rent','amount':3000},{'name':'Bills','amount':700}]}).json()
    for category, value in [('Rent',300000), ('Utilities',60000), ('Gym',10000)]:
        db_session.add(RecurringExpense(user_id=1,request_key=str(uuid4()),amount_cents=value,category=category,
            day=20,next_date=date(2026,10,20),active=True))
    db_session.add(FinancialPlan(id=str(uuid4()),user_id=1,payload=json.dumps({
        'kind':'savings','title':'Laptop','monthlyContribution':500,'deadline':'2027-03-31'})))
    db_session.commit()
    result = budget_review_context(db_session,1,saved,date(2026,10,17))
    assert result['required_contributions'] == 500
    assert result['extra_commitments'] == 100
    assert result['available_for_increases'] == 700


def test_simple_review_preserves_every_saved_target_and_questions_spike():
    targets = {'Rent':3000, 'Entertainment':500, 'Food':600, 'Transport':500,
               'Shopping':500, 'Subscriptions':120, 'Bills':700, 'Groceries':500}
    history = {f'2026-{month:02d}': dict(targets, Shopping=value)
               for month,value in [(7,529.4),(8,618.75),(9,462.3)]}
    reply = format_budget_review(analyze_history(budget(targets), history))
    assert reply.count('• ') == 8 and reply.count('?') == 1
    assert 'Food: AED 600.00 average · Budget AED 600.00' in reply
    assert 'Entertainment: AED 500.00 average · Budget AED 500.00' in reply
    assert 'Shopping: AED 536.82 average · Budget AED 500.00' in reply
    assert 'mainly in August' in reply and 'Was that an unusual month' in reply
    assert not any(token in reply for token in ['**', '`', '|', 'Critical', 'household', 'one-off event'])


def test_plain_review_variation_and_localization():
    review = analyze_history(budget({'Bills':700}), {f'2026-{month:02d}':{'Bills':705} for month in [7,8,9]})
    assert "Small differences don't call for a change" in format_budget_review(review)
    converted = display_context(review, Decimal('1.94'))
    round_displayed_review(converted)
    assert 'CNY 1,367.70' in format_budget_review(converted, 'CNY')
    assert 'المتوسط' in format_budget_review(review, language='ar')
    assert '预算' in format_budget_review(review, language='zh')
