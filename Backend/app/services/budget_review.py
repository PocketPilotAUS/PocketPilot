"""Explain budget changes from completed-month evidence, not model arithmetic."""
import re
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from statistics import median
from sqlalchemy import inspect
from app.models.transaction import Transaction
from app.models.recurring import RecurringExpense

CENT = Decimal("0.01")


def amount(value):
    return Decimal(str(value or 0)).quantize(CENT, ROUND_HALF_UP)


def analyze_history(budget, history, goal_contributions=0, extra_commitments=0):
    allocations = budget["ideal_budget"]["allocations"]
    planned = sum((amount(row["target"]) for row in allocations if row["target"] is not None), Decimal(0))
    income = None if budget["income"] is None else amount(budget["income"])
    goals, commitments = amount(goal_contributions), amount(extra_commitments)
    room = income - planned - goals - commitments if income is not None else None
    rows = []
    increases = Decimal(0)
    for allocation in allocations:
        category, target = allocation["category"], allocation["target"]
        values = [(month, amount(categories[category])) for month, categories in history.items() if category in categories]
        row = {"category": category, "target": target, "historical_months": [month for month, _ in values],
               "monthly_values": [{"month": month, "amount": float(value)} for month, value in values]}
        if allocation.get("automatic"):
            rows.append(dict(row, status="managed_debt_commitment"))
            continue
        if target is None or not values:
            rows.append(dict(row, status="insufficient_history"))
            continue
        target = amount(target)
        average = (sum((value for _, value in values), Decimal(0)) / len(values)).quantize(CENT, ROUND_HALF_UP)
        difference = average - target
        tolerance = max(Decimal(25), target * Decimal("0.05")).quantize(CENT)
        row.update(average=float(average), difference=float(difference), tolerance=float(tolerance))
        if difference <= tolerance:
            row["status"] = "within_normal_variation" if abs(difference) <= tolerance else "below_budget_not_a_problem"
        elif len(values) < 2:
            row["status"] = "insufficient_history"
        else:
            ordered = sorted(value for _, value in values)
            centre = amount(median(ordered))
            unusual = len(values) >= 3 and max(ordered) - centre > max(Decimal(50), centre * Decimal("0.15"))
            repeated = sum(value - target > tolerance for _, value in values)
            rounded = (average / 10).to_integral_value(rounding=ROUND_CEILING) * 10
            increase = rounded - target
            if unusual or repeated < 2:
                row["status"] = "ask_if_high_month_was_unusual"
                row["high_month"] = max(values, key=lambda item: item[1])[0]
            else:
                row["status"] = "discuss_increase" if room is not None and increase <= max(room, 0) else "discuss_affordability"
                row.update(suggested_target=float(rounded), increase=float(increase))
                increases += increase
        rows.append(row)
    if room is None or increases > max(room, 0):
        for row in rows:
            if row.get("status") == "discuss_increase":
                row["status"] = "discuss_affordability"
    proposed = planned + increases
    return {"history_months": sorted(history), "history_completeness": "Recorded months only; transaction count does not prove complete records.",
            "rounding_rule": "Keep actuals exact; round proposed increases upward to the next 10 in the displayed currency.",
            "variation_rule": "An overrun is material only above both AED 25 and 5 percent of that category budget; normally require at least two such months.",
            "categories": rows, "planned_total": float(planned), "required_contributions": float(goals),
            "extra_commitments": float(commitments), "available_for_increases": float(max(room, 0)) if room is not None else None,
            "proposed_total": float(proposed), "total_increase": float(increases),
            "increases_fit": increases <= max(room, 0) if room is not None else None,
            "remaining_after_proposal": float(income - proposed - goals - commitments) if income is not None else None,
            "affordability_note": "Provisional after saved budget, active goal contributions and known recurring costs above budget; unlisted costs may remain."}


def budget_review_context(db, user_id, budget, today):
    cutoff = min(date(budget["year"], budget["month"], 1), today.replace(day=1))
    start_index = max(12, cutoff.year * 12 + cutoff.month - 1 - 3)
    start = date(start_index // 12, start_index % 12 + 1, 1)
    records = db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.date >= start, Transaction.date < cutoff).all()
    counts, history = {}, {}
    canonical = {row["category"].strip().casefold(): row["category"] for row in budget["ideal_budget"]["allocations"]}
    for record in records:
        month = record.date.strftime("%Y-%m")
        counts[month] = counts.get(month, 0) + 1
        category = canonical.get(record.category.strip().casefold(), record.category)
        group = history.setdefault(month, {})
        group[category] = group.get(category, Decimal(0)) + amount(record.amount)
    history = {month: values for month, values in history.items() if counts[month] >= 5}
    from app.services.spending_monitor import active_goals
    goals = sum((amount(goal["monthlyContribution"]) for goal in active_goals(db, user_id, budget["year"], budget["month"])), Decimal(0))
    targets = {row["category"].strip().casefold(): amount(row["target"]) for row in budget["ideal_budget"]["allocations"]}
    from app.services.planning import ALIASES
    recurring = {}
    if inspect(db.get_bind()).has_table("recurring_expenses"):
        for row in db.query(RecurringExpense).filter_by(user_id=user_id, active=True).all():
            key = row.category.strip().casefold()
            if key not in targets:
                key = ALIASES.get(key, key).casefold()
            recurring[key] = recurring.get(key, Decimal(0)) + Decimal(row.amount_cents) / 100
    extra = sum((max(Decimal(0), value - targets.get(key, Decimal(0))) for key, value in recurring.items()), Decimal(0))
    result = analyze_history(budget, history, goals, extra)
    result["excluded_sparse_months"] = sorted(month for month, count in counts.items() if count < 5)
    result["current_month_note"] = "The current month is incomplete. Treat current spending and upcoming payments as changing observations, never a completed-month baseline."
    return result


def clean_review_placeholders(reply):
    return re.sub(r"\[\s*(?:your\s+name|assistant(?:'s)?\s+name|insert\s+name|name\s+here)\s*\]", "PocketPilot", reply, flags=re.I)


def round_displayed_review(review):
    """After currency conversion, keep suggestions at clean displayed amounts."""
    increases = Decimal(0)
    for row in review["categories"]:
        if "suggested_target" not in row:
            continue
        rounded = (amount(row["average"]) / 10).to_integral_value(rounding=ROUND_CEILING) * 10
        row["suggested_target"] = float(rounded)
        row["increase"] = float(rounded - amount(row["target"]))
        increases += amount(row["increase"])
    room = review["available_for_increases"]
    review["increases_fit"] = increases <= amount(room) if room is not None else None
    for row in review["categories"]:
        if "suggested_target" in row:
            row["status"] = "discuss_increase" if review["increases_fit"] else "discuss_affordability"
    delta = increases - amount(review["total_increase"])
    review["total_increase"] = float(increases)
    review["proposed_total"] = float(amount(review["planned_total"]) + increases)
    if review["remaining_after_proposal"] is not None:
        review["remaining_after_proposal"] = float(amount(review["remaining_after_proposal"]) - delta)



def format_budget_review(review, currency="AED", language="en"):
    """Render verified comparisons without letting the model invent the report."""
    from calendar import month_name
    def text(value):
        return re.sub(r"[`*|]", "", " ".join(str(value).split()))
    def cash(value):
        return f"{currency} {amount(value):,.2f}"
    count = len(review["history_months"])
    words = {
        "en": {"intro": f"Hi! 👋 Here's how your spending over the last {count} recorded months compares with your budget.",
               "empty": "Hi! 👋 Here's your saved budget. There isn't enough previous spending recorded to compare it yet.",
               "average": "average", "budget": "Budget", "unset": "not set",
               "normal": "Your listed budget categories generally match your recorded spending. Small differences don't call for a change.",
               "keep": "Would you like to keep these targets?", "limited": "Some categories still have limited history; I wouldn't change those targets yet.",
               "spike": "{category} was higher mainly in {month}, so I wouldn't change its budget yet.",
               "spike_question": "Was that an unusual month for {category}?",
               "raise": "A {target} budget for {category} could better reflect your repeated spending, if your saved budget covers your other costs.",
               "raise_question": "Would you prefer that allowance or try to stay with your current target?",
               "tight": "Some repeated spending is above budget, but I wouldn't raise the targets without checking affordability after your commitments and goals.",
               "tight_question": "Would you prefer to explore spending less or discuss which budgets you could adjust?",
               "history_question": "Do you have another completed month's spending to compare?"},
        "ar": {"intro": f"مرحبًا! 👋 هذه مقارنة إنفاقك خلال آخر {count} أشهر مسجلة بميزانيتك.",
               "empty": "مرحبًا! 👋 هذه ميزانيتك المحفوظة. لا توجد سجلات إنفاق سابقة كافية للمقارنة بعد.",
               "average": "المتوسط", "budget": "الميزانية", "unset": "غير محددة",
               "normal": "تتوافق فئات ميزانيتك عمومًا مع الإنفاق المسجل. الفروق الصغيرة لا تستدعي تغييرًا.",
               "keep": "هل تود الإبقاء على هذه المبالغ؟", "limited": "سجل بعض الفئات محدود؛ لا أنصح بتغيير مبالغها بعد.",
               "spike": "كان إنفاق {category} أعلى خصوصًا في {month}، لذلك لا أنصح بتغيير ميزانيتها بعد.",
               "spike_question": "هل كان ذلك شهرًا غير معتاد لإنفاق {category}؟",
               "raise": "قد تعكس ميزانية {target} لفئة {category} إنفاقك المتكرر بصورة أفضل، إذا كانت ميزانيتك تغطي تكاليفك الأخرى.",
               "raise_question": "هل تفضل هذا المبلغ أم محاولة الالتزام بالمبلغ الحالي؟",
               "tight": "بعض الإنفاق المتكرر أعلى من الميزانية، لكن لا أنصح بزيادة المبالغ قبل مراجعة قدرتك بعد الالتزامات والأهداف.",
               "tight_question": "هل تفضل استكشاف تقليل الإنفاق أم مناقشة الميزانيات التي يمكنك تعديلها؟",
               "history_question": "هل لديك إنفاق شهر مكتمل آخر للمقارنة؟"},
        "zh": {"intro": f"你好！👋 以下是最近{count}个有记录月份的支出与你预算的比较。",
               "empty": "你好！👋 这是你保存的预算。目前还没有足够的历史支出记录进行比较。",
               "average": "平均", "budget": "预算", "unset": "未设置",
               "normal": "所列预算与已记录支出总体一致。小幅差异无需调整。",
               "keep": "你想保留这些预算吗？", "limited": "部分分类的历史记录有限，暂时不建议调整。",
               "spike": "{category}的支出主要在{month}较高，因此暂时不建议调整预算。",
               "spike_question": "那个月的{category}支出是否属于特殊情况？",
               "raise": "如果已保存的预算覆盖其他开支，将{category}预算设为{target}可能更符合你的持续支出。",
               "raise_question": "你更倾向于这个额度，还是尝试保持当前预算？",
               "tight": "部分持续支出超过预算，但提高额度前，需要先核对现有承诺和目标后的负担能力。",
               "tight_question": "你想先探索减少支出，还是讨论哪些预算可以调整？",
               "history_question": "你还有其他完整月份的支出记录可供比较吗？"},
    }.get(language)
    if words is None:
        return format_budget_review(review, currency, "en")
    lines = [words["intro"] if count else words["empty"], ""]
    for row in review["categories"]:
        category = text(row["category"])
        target = cash(row["target"]) if row["target"] is not None else words["unset"]
        average = f"{cash(row['average'])} {words['average']} · " if row.get("average") is not None else ""
        lines.append(f"• {category}: {average}{words['budget']} {target}")
    unusual = [row for row in review["categories"] if row["status"] == "ask_if_high_month_was_unusual"]
    raises = [row for row in review["categories"] if row["status"] == "discuss_increase"]
    constrained = [row for row in review["categories"] if row["status"] == "discuss_affordability"]
    if unusual:
        row = max(unusual, key=lambda item: item.get("difference", 0))
        category = text(row["category"])
        month = month_name[int(row["high_month"].split("-")[1])] if language == "en" else row["high_month"]
        explanation = words["spike"].format(category=category, month=month)
        question = words["spike_question"].format(category=category)
    elif constrained:
        explanation, question = words["tight"], words["tight_question"]
    elif raises:
        row = max(raises, key=lambda item: item["increase"])
        explanation = words["raise"].format(category=text(row["category"]), target=cash(row["suggested_target"]))
        question = words["raise_question"]
    elif any(row["status"] == "insufficient_history" for row in review["categories"]):
        explanation, question = words["limited"], words["history_question"]
    else:
        explanation, question = words["normal"], words["keep"]
    return "\n".join(lines) + "\n\n" + explanation + "\n\n" + question
