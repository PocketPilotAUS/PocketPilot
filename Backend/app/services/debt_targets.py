"""Read-only monthly targets from explicitly applied, saved repayment plans."""
import json
from decimal import Decimal
from sqlalchemy import inspect
from app.models.financial_plan import FinancialPlan


def applied_targets(db, user_id, year, month, regulars):
    # regulars: debt ID -> (required payment, opening amount left).
    targets = {key: value[0] for key, value in regulars.items()}
    extras, details = {}, {}
    if not inspect(db.get_bind()).has_table('financial_plans'):
        return targets, extras, details
    period = f'{year:04d}-{month:02d}'
    for row in db.query(FinancialPlan).filter_by(user_id=user_id).order_by(FinancialPlan.id).all():
        plan = json.loads(row.payload)
        if not plan.get('debtGoalSource') or not plan.get('budgetApplied'):
            continue
        if not (plan.get('budgetAppliedFrom') or '') <= period <= (plan.get('deadline') or '')[:7]:
            continue
        active = [debt_id for debt_id in plan.get('debtIds', []) if debt_id in regulars and regulars[debt_id][1] > 0]
        allocations = {debt_id: regulars[debt_id][0] for debt_id in active}
        # Keep the combined target when a loan is paid off: its freed payment
        # rolls into the remaining loans, following the plan's interest-rate order.
        available = max(Decimal(0), Decimal(str(plan['monthlyContribution'])) - sum(allocations.values(), Decimal(0)))
        priority = plan.get('loanPriority') or plan.get('debtIds', [])
        for debt_id in priority:
            if debt_id in allocations:
                extra = min(available, max(Decimal(0), regulars[debt_id][1] - allocations[debt_id]))
                allocations[debt_id] += extra
                available -= extra
        applied_extra = Decimal(0)
        for debt_id in plan.get('debtIds', []):
            if debt_id not in regulars:
                continue
            regular, opening = regulars[debt_id]
            if opening <= 0:
                continue
            amount = allocations.get(debt_id, regular)
            target = min(opening, max(regular, amount))
            targets[debt_id] = max(targets[debt_id], target)
            extra = max(Decimal(0), target - regular)
            applied_extra += extra
            details[debt_id] = {'id': row.id, 'monthly_payment': float(target), 'extra_payment': float(extra),
                                'deadline': plan['deadline']}
        extras[row.id] = float(applied_extra)
    return targets, extras, details
