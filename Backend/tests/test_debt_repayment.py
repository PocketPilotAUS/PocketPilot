from datetime import date
from decimal import Decimal

import pytest
from app.services.debt_repayment import estimate, remaining_principal


def loan(principal=30000, rate=5, regular=566.14):
    return {'principal':principal,'annual_rate':rate,'regular':regular}


def test_shorter_term_recalculates_interest_and_total():
    result = estimate([loan()], months=24)
    assert result['monthly'] == pytest.approx(1316.15, abs=.01)
    assert result['months'] == 24
    assert result['total_repayment'] < result['baseline_total']
    assert result['remaining_interest'] < result['baseline_interest']
    assert result['interest_saved'] == pytest.approx(result['baseline_interest'] - result['remaining_interest'], abs=.01)
    assert result['total_repayment'] == pytest.approx(30000 + result['remaining_interest'], abs=.01)
    assert result['monthly'] < result['baseline_total'] / 24
    assert result['final_payment'] <= result['monthly']


def test_chosen_amount_recalculates_payoff_instead_of_dividing_old_total():
    result = estimate([loan()], payment=1500)
    assert result['months'] == 21
    assert result['interest_saved'] > 0
    assert result['total_repayment'] < result['baseline_total']
    assert estimate([loan()], payment=500) is None


def test_zero_rate_and_cent_rounding():
    result = estimate([loan(36000,0,600)], months=24)
    assert result['monthly'] == 1500 and result['total_repayment'] == 36000
    assert result['remaining_interest'] == result['interest_saved'] == 0
    small = estimate([loan(100,0,10)], months=3)
    assert small['monthly'] == 33.34 and small['total_repayment'] == 100
    assert small['final_payment'] == 33.32
    assert estimate([loan(0,5,0)], months=24) is None
    assert estimate([loan()], months=601) is None


def test_recorded_payments_reduce_principal_once_per_month_and_respect_reset():
    payments = [(date(2026,10,1),56614), (date(2026,10,15),10000), (date(2026,9,1),0)]
    principal = remaining_principal(30000,5,payments)
    assert principal == Decimal('29458.86')
    # Removing the extra payment restores only its principal deduction.
    assert remaining_principal(30000,5,payments[:1]) == Decimal('29558.86')
    assert remaining_principal(30000,5,[(date(2026,10,1),4000000)]) == 0
    result = estimate([loan(principal)],months=24)
    assert result['principal'] == 29458.86 and result['monthly'] < 1316.15


def test_multiple_loans_keep_minimums_and_reconcile_totals():
    loans = [loan(10000,6,193.33), loan(5000,12,111.23)]
    result = estimate(loans,months=24)
    assert result['months'] <= 24
    assert result['monthly'] >= 304.56
    assert result['total_repayment'] == pytest.approx(15000 + result['remaining_interest'],abs=.01)
    assert result['interest_saved'] > 0
    # Saving and previewing the reviewed payment must give precisely the same figures.
    confirmed = estimate(loans,payment=result['monthly'])
    assert confirmed == result
