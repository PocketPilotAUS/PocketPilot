"""Goal scenarios based on saved planned budgets, never transaction totals."""
import calendar
import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_UP

FLEXIBLE = {"entertainment", "shopping", "subscriptions"}
ESSENTIAL = {"rent", "housing", "food", "groceries", "food and groceries", "transport", "transportation", "fuel", "bills", "utilities", "internet"}


def fingerprint(budget):
    values = {"income": budget["income"], "year": budget["year"], "month": budget["month"],
              "allocations": [(row["category"], row["target"]) for row in budget["ideal_budget"]["allocations"]]}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def deadline_for(today, amount, available):
    if amount <= 0:
        return today.isoformat()
    if available <= 0:
        return None
    months = int((amount / available).to_integral_value(rounding=ROUND_UP))
    index = today.year * 12 + today.month - 1 + months - 1
    year, month = divmod(index, 12)
    if year > 9998:
        return None
    return date(year, month + 1, calendar.monthrange(year, month + 1)[1]).isoformat()


def assess(profile, budget, today, choices=None):
    profile = dict(profile)
    chosen = profile.get("monthly_contribution")
    if chosen is not None and profile.get("target_amount") is not None:
        remaining = max(Decimal(0), Decimal(str(profile["target_amount"])) - Decimal(str(profile.get("current_amount") or 0)))
        profile["deadline"] = deadline_for(today, remaining, Decimal(str(chosen)))
    allocations = budget["ideal_budget"]["allocations"]
    baseline = {row["category"]: Decimal(str(row["target"])) for row in allocations}
    income = Decimal(str(budget["income"]))
    total = sum(baseline.values(), Decimal(0))
    available = income - total
    protected = set(profile.get("protected_categories", [])) | set((choices or {}).get("protected", []))
    folded = {name.casefold() for name in protected}
    if "*" in folded:
        protected.update(baseline)
    protected.update(name for name in baseline if name.casefold() in folded)
    targets = (choices or {}).get("targets", {})
    accepted = {name: Decimal(str(value)) for name, value in targets.items()
                if name in baseline and name not in protected and Decimal(str(value)) <= baseline[name]}
    accepted_cut = sum((baseline[name] - value for name, value in accepted.items()), Decimal(0))
    after = available + accepted_cut
    result = {"ready": False, "budget_fingerprint": fingerprint(budget), "income": float(income),
              "planned_total": float(total), "availableBefore": float(available), "availableAfter": float(after),
              "missing": [], "suggestions": [], "accepted": [{"category": name, "target": float(value)} for name, value in accepted.items()],
              "protected": sorted(protected), "assumption": "Saved planned budget only; unlisted costs are excluded. No budget changes are saved."}
    for field in ("goal", "target_amount", "deadline"):
        if profile.get(field) is None:
            result["missing"].append(field)
    if result["missing"]:
        return result
    deadline = date.fromisoformat(str(profile["deadline"]))
    if deadline <= today:
        result["missing"] = ["future deadline"]
        return result
    remaining = max(Decimal(0), Decimal(str(profile["target_amount"])) - Decimal(str(profile.get("current_amount") or 0)))
    months = (deadline.year - today.year) * 12 + deadline.month - today.month + 1
    required = Decimal(str(chosen)) if chosen is not None else (remaining / months).quantize(Decimal(".01"), rounding=ROUND_UP)
    gap = max(Decimal(0), required - after)
    suggested = []
    outstanding = gap
    # Reviewable reductions, never approved amounts or market-price judgments.
    for essential in (False, True):
        candidates = [(name, value) for name, value in baseline.items()
                      if name not in protected and name not in accepted and value > 0
                      and (name.casefold() in ESSENTIAL if essential else name.casefold() in FLEXIBLE)]
        for name, value in sorted(candidates, key=lambda row: row[1], reverse=True):
            if outstanding <= 0:
                break
            cut = min(outstanding, (value * Decimal(".30")).quantize(Decimal(".01")))
            if cut <= 0:
                continue
            outstanding -= cut
            suggested.append({"category": name, "baseline": float(value), "target": float(value - cut),
                              "monthlyAmount": float(cut), "essential": essential})
    scenario_available = after + sum((Decimal(str(row["monthlyAmount"])) for row in suggested), Decimal(0))
    result.update(ready=True, goal=profile["goal"], deadline=deadline.isoformat(), months=months,
                  targetAmount=float(Decimal(str(profile["target_amount"]))), savedAmount=float(Decimal(str(profile.get("current_amount") or 0))),
                  progress_known=profile.get("current_amount") is not None, requiredMonthly=float(required),
                  unfundedMonthly=float(gap), feasible=gap == 0, suggestions=suggested,
                  scenarioAvailable=float(scenario_available), scenarioUnfunded=float(max(Decimal(0), required - scenario_available)),
                  later_deadline=deadline_for(today, remaining, after) if gap else None,
                  scenario_deadline=deadline_for(today, remaining, scenario_available) if outstanding > 0 else None,
                  no_surplus=after <= 0)
    return result


def draft_plan(profile, budget, today, choices=None):
    from uuid import uuid4
    values = dict(profile)
    chosen = values.get("monthly_contribution")
    if chosen is not None and values.get("target_amount") is not None:
        remaining = max(Decimal(0), Decimal(str(values["target_amount"])) - Decimal(str(values.get("current_amount") or 0)))
        if remaining <= 0:
            return None
        values["deadline"] = deadline_for(today, remaining, Decimal(str(chosen)))
    result = assess(values, budget, today, choices)
    if not result["ready"] or values.get("goal_kind") not in ("savings", "debt"):
        return None
    contribution = Decimal(str(chosen)) if chosen is not None else Decimal(str(result["requiredMonthly"]))
    if contribution <= 0 or contribution > Decimal(str(result["availableAfter"])):
        return None
    accepted = {row["category"]: row["target"] for row in result["accepted"]}
    allocations = [{"category": row["category"], "baseline": row["target"],
                    "target": accepted.get(row["category"], row["target"]), "source": "saved planned monthly budget"}
                   for row in budget["ideal_budget"]["allocations"]]
    cuts = [{"category": row["category"], "monthlyAmount": round(row["baseline"] - row["target"], 2),
             "reason": "Explicitly accepted for this goal scenario; your saved budget is unchanged."}
            for row in allocations if row["target"] < row["baseline"]]
    values["income"] = budget["income"]
    signature = hashlib.sha256(json.dumps({"profile": values, "budget": fingerprint(budget), "accepted": result["accepted"]}, sort_keys=True).encode()).hexdigest()
    # Goal drafts retain user goal details, not invented household facts.
    return {"ready": True, "title": values["goal"], "kind": values["goal_kind"], "profile": values,
            "budgetGoalSource": True, "confirmationKey": str(uuid4()), "draftFingerprint": signature, "budgetFingerprint": fingerprint(budget),
            "budgetChoices": choices or {}, "income": result["income"], "baselineSpending": result["planned_total"],
            "availableBefore": result["availableBefore"], "availableAfter": result["availableAfter"],
            "monthlyContribution": float(contribution), "requiredMonthly": result["requiredMonthly"],
            "unfundedMonthly": 0, "feasible": True, "targetAmount": result["targetAmount"], "savedAmount": result["savedAmount"],
            "months": result["months"], "deadline": values["deadline"], "allocations": allocations, "spendingCuts": cuts,
            "historyComparisons": [], "historyAdvice": [], "warnings": [] if result["progress_known"] else ["Starting goal savings are assumed to be zero unless you tell us otherwise."],
            "assumptions": ["If you follow this planned budget every month, the projected monthly surplus can fund this goal.",
                            "This is not money already saved or a bank balance.",
                            "Contributions start this calendar month and include the target month. No returns are assumed.",
                            "Confirming saves a plan only; it does not record savings, transactions or budget changes."]}
