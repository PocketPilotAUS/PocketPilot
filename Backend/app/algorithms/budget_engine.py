import json
from decimal import Decimal, ROUND_UP, ROUND_DOWN


def calculate_plan(profile, expenses, sources, context, today):
    income = profile.income + profile.other_income
    spending = sum(expenses.values(), Decimal(0))
    available = income - spending
    warnings = []

    remaining = max(
        Decimal(0),
        profile.target_amount - (profile.current_amount or Decimal(0))
    )

    months = None
    if profile.deadline and profile.goal_kind != "spending":
        if profile.deadline <= today:
            raise ValueError("Choose a future deadline")

        # One contribution in each calendar month, including this month.
        months = (
            (profile.deadline.year - today.year) * 12
            + profile.deadline.month - today.month
            + 1
        )

    required = (
        (remaining / months).quantize(
            Decimal("0.01"), rounding=ROUND_UP
        )
        if months else Decimal(0)
    )

    if profile.goal_kind == "spending":
        required = max(Decimal(0), income - profile.target_amount)

    preferred = (
        profile.preferred_monthly_savings
        if profile.goal_kind == "savings"
        else None
    )

    # The user's chosen contribution drives the proposed monthly budget.
    # The deadline requirement remains a separate comparison.
    funding_target = preferred if preferred is not None else required

    if available < 0:
        warnings.append(
            f"Monthly spending exceeds household income by AED {-available:.2f}. "
            "Close this shortfall before funding the goal."
        )

    gap = max(Decimal(0), funding_target - available)

    flexible = [
        key for key in ("Entertainment", "Shopping", "Subscriptions")
        if key not in profile.protected_categories
    ]
    flexible = [key for key in flexible if expenses[key] > 0]

    pool = sum((expenses[key] for key in flexible), Decimal(0))

    # Reviewable scenario capped at 30% of flexible spending.
    cut_total = min(
        gap,
        (pool * Decimal("0.30")).quantize(Decimal("0.01"))
    )

    cuts = []
    allocated = Decimal(0)

    for index, key in enumerate(flexible):
        cut = (
            (cut_total * expenses[key] / pool).quantize(
                Decimal("0.01"), rounding=ROUND_DOWN
            )
            if pool else Decimal(0)
        )

        if index == len(flexible) - 1:
            cut = cut_total - allocated

        allocated += cut

        if cut > 0:
            cuts.append({
                "category": key,
                "monthlyAmount": float(cut),
                "reason": (
                    "A proposed reduction toward your goal; review whether "
                    f"this is workable for your household of {profile.household_size}."
                )
            })

    after = available + cut_total

    unresolved = max(Decimal(0), funding_target - after)

    if unresolved:
        warnings.append(
            f"Even with these cuts, your planned contribution needs "
            f"AED {unresolved:.2f} more per month. Consider adjusting "
            "expenses, your contribution, or your income; do not skip "
            "essential bills or minimum debt payments."
        )

    # What can actually be allocated under the proposed budget.
    contribution = max(Decimal(0), min(funding_target, after))

    # Feasibility of meeting the original deadline, not merely affording
    # the user's preferred monthly contribution.
    deadline_feasible = (
        unresolved == 0
        and (
            preferred is None
            or preferred >= required
            or remaining == 0
        )
    )

    estimated_months = None

    if profile.goal_kind == "savings":
        if remaining == 0:
            estimated_months = 0
        elif funding_target > 0:
            estimated_months = int(
                (remaining / funding_target).to_integral_value(
                    rounding=ROUND_UP
                )
            )

        if preferred is not None:
            if preferred < required and remaining > 0:
                difference = required - preferred
                warnings.append(
                    f"Your preferred savings of AED {preferred:.2f}/month "
                    f"is AED {difference:.2f} below the amount needed "
                    "to meet your deadline."
                )

            if preferred > after:
                warnings.append(
                    f"Your preferred savings of AED {preferred:.2f}/month "
                    "is above the amount available under the proposed budget."
                )

            if preferred == 0 and remaining > 0:
                warnings.append(
                    "Saving AED 0 per month will not make progress "
                    "toward this goal."
                )

    if profile.goal_kind == "debt":
        warnings.append(
            "This target is an extra debt-payment allocation above "
            "the minimums entered. Interest and payoff dates require "
            "debt balances and rates; this is not an amortization schedule."
        )

    comparisons = []
    selected = profile.typical_months

    for key, amount in expenses.items():
        if selected:
            historical = (
                sum(
                    (
                        Decimal(str(context["past_months"][m].get(key, 0)))
                        for m in selected
                    ),
                    Decimal(0)
                ) / len(selected)
            ).quantize(Decimal("0.01"))

            comparisons.append({
                "category": key,
                "historicalMonthly": float(historical),
                "plannedMonthly": float(amount),
                "difference": float(amount - historical)
            })

    if not selected:
        warnings.append(
            "No complete, typical past months were confirmed. "
            "Recommendations use your estimates; recorded history "
            "remains a reference only."
        )

    for key, value in context["recurring_obligations"].items():
        if expenses[key] < Decimal(str(value)):
            warnings.append(
                f"Your {key} estimate is below active recurring "
                f"commitments of AED {value:.2f}. Review for missing "
                "bills or outdated schedules."
            )

    history_advice = []

    if pool > 0:
        share = pool / income * 100 if income else Decimal(0)

        history_advice.append(
            f"Unprotected entertainment, shopping and subscriptions "
            f"total AED {pool:.2f} monthly"
            + (
                f" ({share:.1f}% of available household income)."
                if income else "."
            )
            + f" Review these against your goal of {profile.goal}; "
            "these are candidates for change, not automatically "
            "unnecessary expenses."
        )

    ordered = sorted(selected, reverse=True)

    if len(ordered) >= 2:
        latest, previous = ordered[:2]

        for key in expenses:
            new = Decimal(
                str(context["past_months"][latest].get(key, 0))
            )
            old = Decimal(
                str(context["past_months"][previous].get(key, 0))
            )
            increase = new - old

            if increase >= 50 and (
                not old or increase / old >= Decimal("0.20")
            ):
                history_advice.append(
                    f"{key} rose from AED {old:.2f} in {previous} "
                    f"to AED {new:.2f} in {latest}. Was this a one-off "
                    "cost or a change in the needs of the "
                    f"{profile.household_size} people supported? "
                    "Confirm before treating it as avoidable."
                )

    elif selected:
        history_advice.append(
            "Only one typical month was confirmed. It can provide "
            "a baseline, but not a month-to-month trend."
        )

    targets = dict(expenses)

    for cut in cuts:
        targets[cut["category"]] -= Decimal(
            str(cut["monthlyAmount"])
        )

    return {
        "ready": True,
        "title": profile.goal.strip(),
        "kind": profile.goal_kind,
        "profile": json.loads(profile.model_dump_json()),
        "income": float(income),
        "baselineSpending": float(spending),
        "availableBefore": float(available),
        "availableAfter": float(after),
        "monthlyContribution": float(contribution),
        "requiredMonthly": float(required),
        "preferredMonthlySavings": (
            float(preferred) if preferred is not None else None
        ),
        "fundingTarget": float(funding_target),
        "unfundedMonthly": float(unresolved),
        "feasible": deadline_feasible,
        "contributionAffordable": unresolved == 0,
        "estimatedMonthsAtPreferred": estimated_months,
        "months": months,
        "targetAmount": float(profile.target_amount),
        "savedAmount": float(profile.current_amount or 0),
        "deadline": profile.deadline.isoformat() if months else None,
        "allocations": [
            {
                "category": key,
                "baseline": float(value),
                "target": float(targets[key]),
                "source": sources[key]
            }
            for key, value in expenses.items()
        ],
        "spendingCuts": cuts,
        "historyComparisons": comparisons,
        "historyAdvice": history_advice,
        "warnings": warnings,
        "assumptions": [
            "Amounts are AED per month; additional income is added only once.",
            "Essential categories and user-protected categories are not automatically cut.",
            "Suggested cuts are a reviewable scenario capped at 30% of unprotected entertainment, shopping and subscriptions.",
            "Goal contributions start this calendar month and include the deadline month. No investment returns are assumed.",
            "Estimated completion months assume the chosen monthly contribution is consistently made; they are not guaranteed dates.",
            "Planned allocations do not record transactions or savings progress."
        ]
    }