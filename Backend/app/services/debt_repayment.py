"""Fixed-rate monthly reducing-balance estimates. No ledger or loan writes."""
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP, localcontext

CENT = Decimal('.01')
MAX_MONTHS = 600


def money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def remaining_principal(balance, annual_rate, payments):
    """Estimate principal after applied payments; a month incurs interest once.

    The existing ledger deliberately deducts whole payments from a fixed total.
    Reconstruct principal here only, without changing that recording behaviour.
    Payments marked applied=0 preceded the user's latest balance reset.
    """
    principal = money(balance)
    rate = Decimal(str(annual_rate)) / 1200
    grouped = {}
    for paid_on, cents in payments:
        if cents > 0:
            month = paid_on.strftime('%Y-%m')
            grouped[month] = grouped.get(month, Decimal(0)) + Decimal(cents) / 100
    for month in sorted(grouped):
        principal = max(Decimal(0), principal + money(principal * rate) - grouped[month])
    return principal


def simulate(loans, payment=None, max_months=MAX_MONTHS):
    """Regular payments, or a fixed total with extra sent to higher rates first."""
    balances = [money(loan['principal']) for loan in loans]
    rates = [Decimal(str(loan['annual_rate'])) / 1200 for loan in loans]
    regular = [money(loan['regular']) for loan in loans]
    total_paid = interest_paid = Decimal(0)
    last_payment = Decimal(0)
    initial_payments = []
    priority = sorted(range(len(loans)), key=lambda i: (-rates[i], i))
    for month in range(1, max_months + 1):
        if not any(balances):
            return {'months': month - 1, 'total': total_paid, 'interest': interest_paid, 'final_payment': last_payment, 'initial_payments': initial_payments}
        interest = [money(balance * rate) for balance, rate in zip(balances, rates)]
        due = [balance + charge for balance, charge in zip(balances, interest)]
        paid = [min(value, minimum) for value, minimum in zip(due, regular)]
        if payment is not None:
            extra = money(payment) - sum(paid, Decimal(0))
            if extra < 0:
                return None
            for i in priority:
                addition = min(extra, due[i] - paid[i])
                paid[i] += addition
                extra -= addition
        following = [value - amount for value, amount in zip(due, paid)]
        if month == 1:
            initial_payments = list(paid)
        if sum(following, Decimal(0)) >= sum(balances, Decimal(0)):
            return None  # Payment does not amortize the debt.
        last_payment = sum(paid, Decimal(0))
        total_paid += last_payment
        interest_paid += sum(interest, Decimal(0))
        balances = following
    if any(balances):
        return None
    return {'months': max_months, 'total': total_paid, 'interest': interest_paid, 'final_payment': last_payment, 'initial_payments': initial_payments}


def payment_for_term(principal, annual_rate, months):
    if principal <= 0:
        return Decimal(0)
    rate = Decimal(str(annual_rate)) / 1200
    with localcontext() as ctx:
        ctx.prec = 40
        raw = principal / months if rate == 0 else principal * rate / (1 - (1 + rate) ** -months)
        payment = raw.quantize(CENT, rounding=ROUND_CEILING)
    # Cent-rounded monthly interest can leave a few cents after an analytic payment.
    # Confirm the payment meets the requested term using the same simulation.
    loan = {'principal': principal, 'annual_rate': annual_rate, 'regular': payment}
    while simulate([loan], max_months=months) is None:
        payment += CENT
        loan['regular'] = payment
    return payment


def estimate(loans, months=None, payment=None):
    loans = [loan for loan in loans if money(loan['principal']) > 0]
    if not loans:
        return None
    regular = sum((money(loan['regular']) for loan in loans), Decimal(0))
    baseline = simulate(loans)
    if baseline is None:
        return None
    if payment is None:
        if not isinstance(months, int) or not 1 <= months <= MAX_MONTHS:
            return None
        payment = sum((max(money(loan['regular']), payment_for_term(money(loan['principal']), loan['annual_rate'], months))
                       for loan in loans), Decimal(0))
    else:
        payment = money(payment)
    if payment < regular:
        return None
    proposed = simulate(loans, payment)
    if proposed is None:
        return None
    return {'monthly': float(payment), 'months': proposed['months'],
            'principal': float(sum((money(loan['principal']) for loan in loans), Decimal(0))),
            'total_repayment': float(proposed['total']), 'remaining_interest': float(proposed['interest']),
            'baseline_total': float(baseline['total']), 'baseline_interest': float(baseline['interest']),
            'interest_saved': float(max(Decimal(0), baseline['interest'] - proposed['interest'])),
            'loan_payments': {str(loan['debt_id']): float(value) for loan, value in zip(loans, proposed['initial_payments']) if loan.get('debt_id') is not None},
            'final_payment': float(proposed['final_payment'])}
