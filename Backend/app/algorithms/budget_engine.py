import json
from decimal import Decimal, ROUND_UP, ROUND_DOWN


def calculate_plan(profile, expenses, sources, context, today):
    income = profile.income + profile.other_income
    spending = sum(expenses.values(), Decimal(0))
    available = income - spending
    warnings = []
    remaining = max(Decimal(0), profile.target_amount - (profile.current_amount or Decimal(0)))
    months = None
    if profile.deadline and profile.goal_kind != "spending":
        if profile.deadline <= today:
            raise ValueError("Choose a future deadline")
        # Save once in each calendar month starting this month, through deadline month.
        months = (profile.deadline.year - today.year) * 12 + profile.deadline.month - today.month + 1
    required = (remaining / months).quantize(Decimal("0.01"), rounding=ROUND_UP) if months else Decimal(0)
    if profile.goal_kind == "spending":
        required = max(Decimal(0), income - profile.target_amount)
    if available < 0:
        warnings.append(f"Monthly spending exceeds household income by AED {-available:.2f}. Close this shortfall before funding the goal.")
    gap = max(Decimal(0), required - available)
    flexible = [key for key in ("Entertainment", "Shopping", "Subscriptions") if key not in profile.protected_categories]
    flexible = [key for key in flexible if expenses[key] > 0]
    pool = sum((expenses[key] for key in flexible), Decimal(0))
    # An adjustable first scenario, not a claim that these costs are unnecessary.
    cut_total = min(gap, (pool * Decimal("0.30")).quantize(Decimal("0.01")))
    cuts = []
    allocated = Decimal(0)
    for index, key in enumerate(flexible):
        cut = (cut_total * expenses[key] / pool).quantize(Decimal("0.01"), rounding=ROUND_DOWN) if pool else Decimal(0)
        if index == len(flexible) - 1:
            cut = cut_total - allocated
        allocated += cut
        if cut > 0:
            cuts.append({"category": key, "monthlyAmount": float(cut), "reason": f"A proposed reduction toward your goal; review whether this is workable for your household of {profile.household_size}."})
    after = available + cut_total
    unresolved = max(Decimal(0), required - after)
    if unresolved:
        warnings.append(f"Even with these cuts, the goal needs AED {unresolved:.2f} more per month. Consider a later deadline, a smaller target or additional income; do not skip essential bills or minimum debt payments.")
    if profile.goal_kind == "debt":
        warnings.append("This target is an extra debt-payment allocation above the minimums entered. Interest and payoff dates require debt balances and rates; this is not an amortization schedule.")
    comparisons = []
    selected = profile.typical_months
    for key, amount in expenses.items():
        if selected:
            historical = (sum((Decimal(str(context["past_months"][m].get(key, 0))) for m in selected), Decimal(0)) / len(selected)).quantize(Decimal("0.01"))
            comparisons.append({"category": key, "historicalMonthly": float(historical), "plannedMonthly": float(amount), "difference": float(amount - historical)})
    if not selected:
        warnings.append("No complete, typical past months were confirmed. Recommendations use your estimates; recorded history remains a reference only.")
    for key, value in context["recurring_obligations"].items():
        if expenses[key] < Decimal(str(value)):
            warnings.append(f"Your {key} estimate is below active recurring commitments of AED {value:.2f}. Review for missing bills or outdated schedules.")
    history_advice = []
    if pool > 0:
        share = pool / income * 100 if income else Decimal(0)
        history_advice.append(f"Unprotected entertainment, shopping and subscriptions total AED {pool:.2f} monthly" + (f" ({share:.1f}% of available household income)." if income else ".") + f" Review these against your goal of {profile.goal}; these are candidates for change, not automatically unnecessary expenses.")
    ordered = sorted(selected, reverse=True)
    if len(ordered) >= 2:
        latest, previous = ordered[:2]
        for key in expenses:
            new = Decimal(str(context["past_months"][latest].get(key, 0)))
            old = Decimal(str(context["past_months"][previous].get(key, 0)))
            increase = new - old
            if increase >= 50 and (not old or increase / old >= Decimal("0.20")):
                history_advice.append(f"{key} rose from AED {old:.2f} in {previous} to AED {new:.2f} in {latest}. Was this a one-off cost or a change in the needs of the {profile.household_size} people supported? Confirm before treating it as avoidable.")
    elif selected:
        history_advice.append("Only one typical month was confirmed. It can provide a baseline, but not a month-to-month trend.")
    targets = dict(expenses)
    for cut in cuts:
        targets[cut["category"]] -= Decimal(str(cut["monthlyAmount"]))
    return {"ready": True, "title": profile.goal.strip(), "kind": profile.goal_kind,
            "profile": json.loads(profile.model_dump_json()),
            "income": float(income), "baselineSpending": float(spending), "availableBefore": float(available),
            "availableAfter": float(after), "monthlyContribution": float(max(Decimal(0), min(required, after))),
            "requiredMonthly": float(required), "unfundedMonthly": float(unresolved), "feasible": unresolved == 0,
            "months": months, "targetAmount": float(profile.target_amount), "savedAmount": float(profile.current_amount or 0),
            "deadline": profile.deadline.isoformat() if months else None,
            "allocations": [{"category": key, "baseline": float(value), "target": float(targets[key]), "source": sources[key]} for key, value in expenses.items()],
            "spendingCuts": cuts, "historyComparisons": comparisons, "historyAdvice": history_advice, "warnings": warnings,
            "assumptions": ["Amounts are AED per month; additional income is added only once.", "Essential categories and user-protected categories are not automatically cut.", "Suggested cuts are a reviewable scenario capped at 30% of unprotected entertainment, shopping and subscriptions.", "Goal contributions start this calendar month and include the deadline month. No investment returns are assumed.", "Planned allocations do not record transactions or savings progress."]}
