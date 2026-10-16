import { formatDisplayAmount } from "../../preferences/currency";
import React, { useState } from "react";
import { Pressable } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import IncomeDonut from "../IncomeDonut";
import { incomeChart } from "../../utils/incomeChart";
import {
  ChevronDown,
  ChevronUp,
  Lightbulb,
  CircleCheck,
  ChartNoAxesColumn,
  AlertCircle,
  Trash2,
} from "lucide-react-native";
import { useAITheme } from "./useAITheme";
import { createPlanningStyles } from "../../styles/PlanningStyles";
import type { FinancialPlan, PlanSuggestion, SpendingStatus } from "../../types/plans";
import { formatAED, formatPercent } from "../../utils/dashboard";
import { formatPlanningDate } from "../../utils/planningDate";
import { percentOf, planScenario } from "../../utils/planVisuals";
import SpendingStatusPanel from "./SpendingStatusPanel";
import { statusMessage } from "../../utils/spendingStatus";
// Keep backend amounts and recommendations intact while presenting common messages plainly.
function friendlyInsight(message: string): string {
  const match = message.match(/Unprotected (.+?) total (AED\s*[\d,.]+) monthly.*?\.\s*(.*)/i);
  if (match) {
    return `You're budgeting ${match[2]} a month for ${match[1]}. Take a look at these expenses to see whether you'd like to put more toward your goal. ${match[3]}`;
  }
  return message;
}
function friendlyWarning(message: string): string {
  if (/No complete, typical past months were confirmed/i.test(message)) {
    return "We don't have enough confirmed, representative spending history yet. For now, this plan uses your estimates. Tracking and confirming more months will help make future recommendations more reliable.";
  }
  const rent = message.match(/Your Rent estimate is below active recurring commitments of (AED\s*[\d,.]+)/i);
  if (rent) {
    return `Your rent estimate looks lower than your recorded recurring commitments (${rent[1]}). Double-check your rent and bills so your plan reflects what you actually need to pay.`;
  }
  return message;
}
// status: this month's verified spending check (saved plans only)
type Props = { plan: FinancialPlan; onSave?: () => void; onEdit?: (suggestion?: PlanSuggestion) => void; onDelete?: () => void; busy?: boolean;
  status?: SpendingStatus | null; apiBaseUrl?: string; onStatusChange?: (status: SpendingStatus) => void };
export default function FinancialPlanCard({ plan, onSave, onEdit, onDelete, busy = false, status = null, apiBaseUrl, onStatusChange }: Props) {
  const { palette, chartColors } = useAITheme();
  const s = createPlanningStyles(palette);
  const [openAdvice, setOpenAdvice] = useState<"recommendations" | "insights" | "warnings" | "assumptions" | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "spending" | "advice">("overview");
  const [autoReview, setAutoReview] = useState(false);
  const live = !!plan.id && status?.has_budget ? status : null;
  // This month differs from the plan's assumptions: say "planned" instead of an unqualified verdict
  const qualified = !!live && live.level >= 1;
  // A goal-risk warning (level 2 or 3) is the primary status: planned figures are then shown
  // neutrally, never as green "on track" messages
  const warning = !!live && live.level >= 2;
  const good = warning ? null : s.accentText;
  const riskTone = live?.level === 3 ? s.dangerText : live?.level === 2 ? s.warnText : s.accentText;
  // Overview figures use the recommended scenario, as before
  const proposed = true;
  const [selected, setSelected] = useState<string | null>(null);
  const scenario = planScenario(plan, proposed);
  // The Spending chart shows the user's own estimates; recommendations are listed separately
  // Budget-goal plans follow this month's approved budget, including accepted adjustments
  const rows = plan.budgetGoalSource && live
    ? live.categories.map((row, i) => ({ category: row.category, baseline: row.budget, target: row.budget, source: "approved monthly budget", color: chartColors[i % chartColors.length], amount: row.budget }))
    : plan.allocations.map((row, i) => ({ ...row, color: chartColors[i % chartColors.length], amount: row.baseline }));
  const baselineSpending = rows.reduce((sum, row) => sum + row.amount, 0);
  const changes = rows.filter(row => Math.abs(row.baseline - row.target) > .005);
  const changeSavings = changes.reduce((sum, row) => sum + row.baseline - row.target, 0);
  const chartIncome = plan.budgetGoalSource && live?.income != null ? live.income : plan.income;
  const chart = incomeChart(rows.map(row => ({ label: row.category, amount: row.amount, color: row.color })), chartIncome);
  const focus = rows.find(row => row.category === selected);
  const goalPercent = percentOf(plan.savedAmount, plan.targetAmount);
  const spendingGoal = plan.kind === "spending";
  const savingsGoal = plan.kind === "savings";
  const preferredSavings = savingsGoal
    ? (plan.preferredMonthlySavings ?? (plan.profile.preferred_monthly_savings == null
        // Budget-goal plans store their planned amount as the monthly contribution
        ? (plan.budgetGoalSource ? plan.monthlyContribution : null) : Number(plan.profile.preferred_monthly_savings)))
    : null;
  const hasPreferredSavings = preferredSavings !== null && Number.isFinite(preferredSavings);
  const preferredAmount = preferredSavings ?? 0;
  const fundingTarget = plan.fundingTarget ?? (hasPreferredSavings ? preferredAmount : plan.requiredMonthly);
  const deadlineGap = hasPreferredSavings ? Math.max(0, plan.requiredMonthly - preferredAmount) : 0;
  const remainingGoal = Math.max(0, plan.targetAmount - plan.savedAmount);
  const estimatedMonths = savingsGoal
    ? (plan.estimatedMonthsAtPreferred ?? (fundingTarget > 0 ? Math.ceil(remainingGoal / fundingTarget) : remainingGoal === 0 ? 0 : null))
    : null;
  const contributionAffordable = scenario.shortfall <= 0.005;
  const onSchedule = plan.feasible && deadlineGap <= 0.005;
  const select = (category: string) => setSelected(current => current === category ? null : category);
  return <View style={s.card}>
    <View style={s.planHeading}>
      <Text style={s.planEyebrow}>{plan.id ? "SAVED PLAN" : "DRAFT PLAN"}</Text>
      <Text localize={false} style={s.title}>{plan.title}</Text>
      {plan.profile.household_size != null && <Text style={s.text}>{plan.profile.household_size} {plan.profile.household_size === 1 ? "person" : "people"} supported{plan.deadline ? ` · Target ${formatPlanningDate(plan.deadline)}` : ""}</Text>}
      {plan.budgetGoalSource && plan.profile.household_size == null && plan.deadline && <Text style={s.text}>Target {formatPlanningDate(plan.deadline)}</Text>}
    </View>
    <View style={[s.scenarioSwitch, { marginBottom: 8 }]} accessibilityRole="tablist">
      {(["overview", "spending", "advice"] as const).map(tab => (
        <Pressable key={tab} accessibilityRole="tab" accessibilityState={{ selected: activeTab === tab }}
          onPress={() => setActiveTab(tab)}
          style={[s.scenarioOption, activeTab === tab && s.scenarioActive]}>
          <Text style={[s.scenarioLabel, activeTab === tab && s.scenarioLabelActive]}>
            {tab === "overview" ? "Overview" : tab === "spending" ? "Spending" : "Advice"}
          </Text>
        </Pressable>
      ))}
    </View>
    {activeTab === "overview" && <>
      {/* Current status first: the warning, then this month's real position */}
      <SpendingStatusPanel status={live} compact onOpen={() => { setAutoReview(true); setActiveTab("spending"); }} />
      {live && live.available_projected != null && <>
        {/* Actual position this month: recorded spending plus what is still expected */}
        <Text style={s.metricHeading}>Current position · this month</Text>
        <View style={s.metricGrid}>
          <View style={s.metric}><Text style={s.metricLabel}>Expected spending</Text><Text style={s.metricValue}>{formatAED(live.projected_spending)}</Text></View>
          <View style={s.metric}><Text style={s.metricLabel}>Available after spending</Text><Text style={[s.metricValue, live.available_projected < 0 ? s.dangerText : riskTone]}>{formatAED(live.available_projected)}</Text></View>
          <View style={s.metric}><Text style={s.metricLabel}>Goal savings needed</Text><Text style={s.metricValue}>{formatAED(live.required_contributions)}</Text></View>
          <View style={s.metric}><Text style={s.metricLabel}>Left after savings</Text><Text style={[s.metricValue, live.available_projected - live.required_contributions < 0 ? s.dangerText : riskTone]}>{formatAED(live.available_projected - live.required_contributions)}</Text></View>
        </View>
        <Text style={s.caption}>{`Includes ${formatAED(live.recorded_spending)} already spent. ${live.forecast_confidence === "low"
          ? "Not enough history for a spending forecast, so the rest assumes your remaining planned budget."
          : live.forecast_confidence === "moderate" ? "The rest is estimated from your spending pace and upcoming bills; limited history, so treat it as an estimate."
            : "The rest is estimated from your spending pace, your past months and upcoming bills."}`}</Text>
      </>}
      {live && <Text style={s.metricHeading}>Planned scenario · from your saved budget</Text>}
      <View style={s.metricGrid}>
        <View style={s.metric}><Text style={s.metricLabel}>Monthly income</Text><Text style={s.metricValue}>{formatAED(plan.income)}</Text></View>
        <View style={s.metric}><Text style={s.metricLabel}>Monthly costs</Text><Text style={s.metricValue}>{formatAED(scenario.spending)}</Text></View>
        <View style={s.metric}><Text style={s.metricLabel}>{scenario.available < 0 ? "Expense deficit" : "Available after costs"}</Text><Text style={[s.metricValue, scenario.available < 0 ? s.dangerText : good]}>{formatAED(Math.abs(scenario.available))}</Text></View>
        <View style={s.metric}>
          <Text style={s.metricLabel}>Left After Goal Funding</Text>
          <Text
            style={[
              s.metricValue,
              scenario.available - scenario.contribution < 0
                ? s.dangerText
                : good,
            ]}
          >
            {formatAED(scenario.available - scenario.contribution)}
          </Text>
        </View>
      </View>
      <View style={s.visualSection}>
        <View style={s.sectionHeading}><Text style={s.sectionTitle}>{spendingGoal ? "Spending ceiling" : "Monthly goal funding"}</Text><Text style={[s.sectionStat, scenario.shortfall > .005 ? s.dangerText : good]}>{scenario.shortfall > .005 ? "Needs adjustment" : qualified ? "Fits planned budget" : "Fits monthly budget"}</Text></View>
        <Text style={s.fundingValue}>{formatAED(spendingGoal ? scenario.spending : scenario.contribution)}<Text style={s.text}> / month</Text></Text>
        {spendingGoal && (
          <Text style={s.text}>
            Monthly spending ceiling: {formatAED(plan.targetAmount)}
          </Text>
        )}
        {spendingGoal && plan.targetAmount > 0 && <>
          <View accessibilityRole="progressbar" accessibilityLabel="Spending ceiling used" accessibilityValue={{ min: 0, max: 100, now: Math.round(percentOf(scenario.spending, plan.targetAmount)) }} style={s.progressTrack}>
            <View style={[s.progressFill, scenario.spending > plan.targetAmount && s.ceilingExceeded, { width: `${percentOf(scenario.spending, plan.targetAmount)}%` }]} />
          </View>
          <Text style={s.text}>{scenario.spending > plan.targetAmount ? `${formatAED(scenario.spending - plan.targetAmount)} above your spending ceiling.` : `${formatAED(plan.targetAmount - scenario.spending)} below your spending ceiling.`}</Text>
        </>}
        {!spendingGoal && fundingTarget > 0 && <>
          <View accessibilityRole="progressbar" accessibilityLabel="Monthly goal funding" accessibilityValue={{ min: 0, max: 100, now: Math.round(scenario.fundedPercent) }} style={s.progressTrack}>
            <View style={[s.progressFill, warning && s.progressFillPlanned, { width: `${scenario.fundedPercent}%` }]} />
          </View>
          <Text style={s.text}>{scenario.fundedPercent >= 99.995 ? (qualified ? "Fully funded by your planned budget." : "Fully funded by your budget.") : `${formatPercent(scenario.fundedPercent)} of monthly savings covered.`}</Text>
        </>}
        {scenario.shortfall > .005 && <Text style={s.shortfall}>{formatAED(scenario.shortfall)} more needed per month{proposed ? " after proposed cuts" : " before cuts"}.</Text>}
        {scenario.expenseDeficit > .005 && <Text style={s.error}>Costs exceed income by {formatAED(scenario.expenseDeficit)}. This deficit must be covered before funding the goal.</Text>}
        {!spendingGoal && remainingGoal === 0 && <Text style={s.text}>The entered progress already meets the target.</Text>}
        <Text style={s.caption}>This is a calculated scenario based on your estimates, not recorded savings.</Text>
      </View>
        {savingsGoal && <View style={s.visualSection}>
          <Text style={s.sectionTitle}>{qualified ? "Your planned savings" : "Your savings plan"}</Text>
          <View style={{ gap: 10, marginTop: 8 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 12 }}>
              <Text style={[s.text, { flex: 1 }]}>Needed by deadline</Text>
              <Text style={s.label}>{formatAED(plan.requiredMonthly)} / month</Text>
            </View>
            <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 12 }}>
              <Text style={[s.text, { flex: 1 }]}>You plan to save</Text>
              <Text style={s.label}>{hasPreferredSavings ? `${formatAED(preferredAmount)} / month` : "Not set"}</Text>
            </View>
            {hasPreferredSavings && <>
              <Text style={[s.text, deadlineGap > 0.005 ? s.dangerText : good]}>
                {deadlineGap > 0.005
                  ? `${formatAED(deadlineGap)}/month short of deadline target.`
                  : preferredAmount > plan.requiredMonthly + 0.005
                    ? `${formatAED(preferredAmount - plan.requiredMonthly)}/month above deadline target.`
                    : warning ? "The planned amount meets the deadline target." : "On target for your deadline."}
              </Text>
              <Text style={[s.text, !contributionAffordable ? s.dangerText : good]}>
                {contributionAffordable
                  ? (qualified ? "Fits your planned monthly budget." : "Fits your monthly budget.")
                  : `Budget shortfall: ${formatAED(scenario.shortfall)}/month.`}
              </Text>
            </>}
            {estimatedMonths !== null && <Text style={s.text}>
              {remainingGoal === 0
                ? "You've already reached the savings target."
                : `${qualified ? "Planned completion" : "Estimated completion"}: ${estimatedMonths} ${estimatedMonths === 1 ? "month" : "months"}.`}
            </Text>}
            {estimatedMonths === null && remainingGoal > 0 && <Text style={s.text}>
              No completion estimate at AED 0 monthly savings.
            </Text>}
          </View>
          {remainingGoal > 0 && (deadlineGap > 0.005 || !contributionAffordable) && (
            <View
              style={{
                marginTop: 14,
                padding: 12,
                borderRadius: 12,
                borderWidth: 1,
                borderColor: palette.textMuted,
                gap: 7,
              }}
            >
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <AlertCircle size={17} color={palette.danger} />
                <Text style={[s.label, { flex: 1 }]}> 
                  {deadlineGap > 0.005 && contributionAffordable
                    ? "Consider extending your deadline"
                    : deadlineGap > 0.005
                      ? "Consider adjusting your deadline or budget"
                      : "Consider adjusting your budget"}
                </Text>
              </View>
              <Text style={s.text}>
                {deadlineGap > 0.005 && contributionAffordable
                  ? `Your ${formatAED(preferredAmount)}/month savings fit your budget, but not your deadline.${estimatedMonths !== null ? ` At this rate, you'll need about ${estimatedMonths} months.` : ""}`
                  : deadlineGap > 0.005
                    ? `Your savings are below the deadline target, and your monthly budget is short by ${formatAED(scenario.shortfall)}.`
                    : `Your monthly budget is short by ${formatAED(scenario.shortfall)}. Review expenses or lower your contribution.`}
              </Text>
              {onEdit && <Text style={s.caption}>Use Adjust My Plan below to change your target date or savings amount.</Text>}
            </View>
          )}
        </View>}
      {onSave && <Pressable style={[s.button, busy && s.muted]} disabled={busy} onPress={onSave}><Text style={s.buttonText}>{busy ? "Saving…" : "Save Plan"}</Text></Pressable>}
      {onEdit && <Pressable style={[s.button, s.secondary, busy && s.muted]} disabled={busy} onPress={() => onEdit()}><Text style={s.secondaryText}>Adjust My Plan</Text></Pressable>}
      {!spendingGoal && <View style={s.visualSection}>
        <View style={s.sectionHeading}><Text style={s.sectionTitle}>{plan.kind === "debt" ? "Debt Already Repaid" : "Already Saved Toward Your Goal"}</Text><Text style={s.sectionStat}>{formatPercent(goalPercent)}</Text></View>
        <View style={s.progressTrack} accessibilityRole="progressbar" accessibilityLabel="Entered goal progress" accessibilityValue={{ min: 0, max: 100, now: Math.round(goalPercent) }}><View style={[s.progressFill, { width: `${goalPercent}%` }]} /></View>
        {plan.kind === "debt"
          ? <Text style={s.text}>{formatAED(plan.savedAmount)} entered toward {formatAED(plan.targetAmount)}</Text>
          : <Text style={s.text}>{formatAED(plan.savedAmount)} saved toward {formatAED(plan.targetAmount)} · {formatAED(remainingGoal)} remaining</Text>}
        {!!plan.contributedAmount && <Text style={s.caption}>Includes {formatAED(plan.contributedAmount)} you assigned to this goal in Savings.</Text>}
        <Text style={s.caption}>This tracks the progress you've entered so far, not future savings predicted by PocketPilot.</Text>
      </View>}
      {onDelete && <Pressable style={[s.deleteAction, s.deleteRow]} disabled={busy} onPress={onDelete} accessibilityRole="button" accessibilityLabel="Delete Plan">
        <Trash2 size={17} color={palette.danger} /><Text style={s.error}>Delete Plan</Text>
      </Pressable>}
    </>}
    {activeTab === "spending" && <>
      <View style={s.visualSection}>
        <Text style={s.sectionTitle}>Your monthly budget</Text>
        <Text style={s.caption}>Your saved monthly estimates · Tap a category for details</Text>
        <View style={s.planChart}>
          <IncomeDonut chart={chart} size={200} grey={palette.textMuted} danger={palette.danger} selected={selected} onSelect={select} />
          <View pointerEvents="none" style={s.planChartCenter}>
            <Text style={s.chartLabel}>{focus ? focus.category : chart.validIncome ? "Monthly income" : "Income needed"}</Text>
            <Text style={s.chartCurrency}>AED</Text>
            <Text style={s.chartValue} adjustsFontSizeToFit numberOfLines={1}>{focus ? formatDisplayAmount(focus.amount) : chart.validIncome ? formatDisplayAmount(plan.income) : "—"}</Text>
            {focus && chart.validIncome && <Text style={s.caption}>{formatPercent(focus.amount / plan.income * 100)} of income</Text>}
          </View>
        </View>
        {baselineSpending === 0 && <Text style={s.text}>No monthly costs entered.</Text>}
        {chart.overBy > 0 && <Text style={s.error}>Costs exceed income by {formatAED(chart.overBy)}.</Text>}
        <View style={s.chartLegend}>
          {rows.map(row => <Pressable key={row.category} accessibilityRole="button" accessibilityState={{ selected: selected === row.category }}
            accessibilityLabel={`${row.category}, ${formatAED(row.amount)}${chart.validIncome ? `, ${formatPercent(row.amount / plan.income * 100)} of income` : ""}`}
            onPress={() => select(row.category)} style={[s.chartLegendRow, selected === row.category && s.legendSelected]}>
            <View style={[s.chartDot, { backgroundColor: row.color }]} /><Text style={s.legendCategory}>{row.category}</Text>
            <View style={s.legendNumbers}><Text style={s.legendAmount}>{formatAED(row.amount)}</Text><Text style={s.caption}>{chart.validIncome ? formatPercent(row.amount / plan.income * 100) : "—"}</Text></View>
          </Pressable>)}
          {chart.validIncome && <View style={s.chartLegendRow}>
            <View style={[s.chartDot, { backgroundColor: palette.textMuted }]} /><Text style={s.legendCategory}>Left after costs</Text>
            <View style={s.legendNumbers}><Text style={s.legendAmount}>{formatAED(chart.remaining!)}</Text><Text style={s.caption}>{formatPercent(chart.remainingPercent!)}</Text></View>
          </View>}
        </View>
      </View>
      {live && <SpendingStatusPanel status={live} apiBaseUrl={apiBaseUrl} autoStart={autoReview} planId={plan.id} onEditPlan={onEdit} onStatusChange={next => { setAutoReview(false); onStatusChange?.(next); }} />}
      {changes.length > 0 && <View style={s.visualSection}>
        <Text style={s.sectionTitle}>Recommended changes</Text>
        <>
              {changes.map(row => <View key={row.category} style={s.changeRow}>
                <View style={{ flex: 1, gap: 2 }}>
                  <Text style={s.label}>{row.category}</Text>
                  <Text style={s.caption}>{formatAED(row.baseline)} → <Text style={s.accentText}>{formatAED(row.target)}</Text> recommended</Text>
                </View>
                <Text style={[s.label, row.baseline > row.target ? s.accentText : s.dangerText]}>{row.baseline > row.target ? `Save ${formatAED(row.baseline - row.target)}` : `+${formatAED(row.target - row.baseline)}`}<Text style={s.caption}> /mo</Text></Text>
              </View>)}
              {changeSavings > .005 && <Text style={s.text}>Together these free up {formatAED(changeSavings)} per month.</Text>}
              <Text style={s.caption}>Suggestions only. Your saved budget stays as you entered it.</Text>
        </>
      </View>}
    </>}
    {activeTab === "advice" && <>
      {(["recommendations", "insights", "warnings", "assumptions"] as const)
        .filter(section => section !== "warnings" || plan.warnings.length > 0)
        .map(section => {
          const expanded = openAdvice === section;
          const title = section === "recommendations" ? "Recommendations"
            : section === "insights" ? "Spending Insights"
            : section === "warnings" ? `Things to Double-Check (${plan.warnings.length})`
            : "Assumptions & History";
          const iconColor = section === "warnings" ? "#E6A25A" : palette.accent;
          return <View key={section} style={{ marginBottom: 10 }}>
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ expanded }}
              onPress={() => setOpenAdvice(current => current === section ? null : section)}
              style={[s.button, s.secondary, { borderRadius: 14, paddingHorizontal: 14 }]}
            >
              <View style={{ flexDirection: "row", alignItems: "center", gap: 10, width: "100%" }}>
                {section === "recommendations" ? <Lightbulb size={19} color={iconColor} />
                  : section === "insights" ? <ChartNoAxesColumn size={19} color={iconColor} />
                  : section === "warnings" ? <AlertCircle size={19} color={iconColor} />
                  : <CircleCheck size={19} color={iconColor} />}
                <Text style={[s.secondaryText, { flex: 1, textAlign: "left" }]}>{title}</Text>
                {expanded ? <ChevronUp size={18} color={palette.text} /> : <ChevronDown size={18} color={palette.text} />}
              </View>
            </Pressable>
            {expanded && <View style={[s.detailSection, { marginTop: 8, gap: 10 }]}>
              {section === "recommendations" && <>
        {live && (statusMessage(live) || live.adjustments.length > 0) && <View style={s.detailSection}>
          <Text style={s.label}>This month</Text>
          {live.level === 1 && <Text style={s.text}>{live.over_budget.length
            ? `For the rest of the month, keep ${live.over_budget[0].category} spending to what you've already recorded and use the remaining budget in other categories carefully. You don't need a new budget unless more categories go over.`
            : "Keep an eye on your remaining spending for the rest of the month."}</Text>}
          {live.level === 2 && <Text style={s.text}>Projected spending puts your savings goal at risk. Review an AI adjustment plan in the Spending tab before spending more in flexible categories.</Text>}
          {live.level === 3 && <Text style={s.text}>Recorded spending and upcoming bills already leave too little for your goal this month. Review an AI recovery plan in the Spending tab, and consider lowering this month's contribution or extending the deadline with Adjust My Plan.</Text>}
          {live.adjustments.length > 0 && (() => {
            const latest = live.adjustments[live.adjustments.length - 1];
            return <Text style={s.text}>{`On ${latest.accepted_on} you set spending limits: ${latest.changes.map(change => `${change.category} ${formatAED(change.limit ?? change.proposed)}`).join(", ")}. Keep to these amounts for the rest of the month.`}</Text>;
          })()}
        </View>}
        <View style={{ gap: 6, padding: 12, borderRadius: 12, borderWidth: 1, borderColor: palette.textMuted }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              {onSchedule && scenario.expenseDeficit <= 0.005 && !warning && (
                <CircleCheck size={16} color={palette.accent} />
              )}
              <Text style={[s.label, { flexShrink: 1 }, !onSchedule || scenario.expenseDeficit > 0.005 ? s.dangerText : good]}>
            {scenario.expenseDeficit > 0.005
              ? "Your monthly costs are higher than your income"
              : scenario.shortfall > 0.005
                ? "A few changes could help you reach your goal"
                : !onSchedule ? "Monthly savings won’t meet the deadline" : warning ? "Planned scenario: your saved budget fits this goal" : qualified ? "Based on your plan, your goal looks achievable" : "Your goal looks achievable"}
              </Text>
            </View>
          <Text style={s.text}>
            {scenario.expenseDeficit > 0.005
              ? `Your estimated costs exceed income by ${formatAED(scenario.expenseDeficit)} per month. Start by checking your expenses and see where you can make room for your goal.`
              : scenario.shortfall > 0.005
                ? `To reach your goal on this timeline, you would need to free up another ${formatAED(scenario.shortfall)} per month. Try reviewing flexible spending or adjusting your target date.`
                : !onSchedule ? `To meet the deadline, save ${formatAED(plan.requiredMonthly)}/month or choose a later date.`
                  : warning ? "This month's actual spending doesn't follow that plan; see This month above." : "Your monthly savings fit your budget and deadline, based on your estimates."}
          </Text>
        </View>
        <Text style={s.text}>{changes.length > 0
          ? `See the Spending tab for ${changes.length} suggested budget ${changes.length === 1 ? "change" : "changes"}.`
          : "No specific cuts are suggested right now. You can still review flexible expenses if you'd like extra breathing room."}</Text>
              </>}
              {section === "insights" && <>
        {plan.historyAdvice?.length ? (
          plan.historyAdvice.map((advice, i) => (
            <Text key={`history-advice-${i}`} style={s.text}>{friendlyInsight(advice)}</Text>
          ))
        ) : (
          <Text style={s.text}>As you track and confirm more spending history, PocketPilot can offer more personalized insights.</Text>
        )}
              </>}
              {section === "warnings" && <>
          {plan.warnings.map((warning, i) => (
            <View key={`warning-main-${i}`} style={{ paddingVertical: 5 }}>
              <Text style={s.error}>{friendlyWarning(warning)}</Text>
            </View>
          ))}
              </>}
              {section === "assumptions" && <>
          {plan.historyComparisons.length > 0 && <Text style={s.label}>Historical Comparisons</Text>}
          {plan.historyComparisons.map(row => (
            <Text key={row.category} style={s.text}>
              {row.category}: historical average {formatAED(row.historicalMonthly)}; estimate {formatAED(row.plannedMonthly)}.
            </Text>
          ))}
          {plan.assumptions.length > 0 && <Text style={s.label}>Calculation Assumptions</Text>}
          {plan.assumptions.map((note, i) => (
            <Text key={`note-${i}`} style={s.caption}>{note}</Text>
          ))}
          {plan.historyComparisons.length === 0 && plan.assumptions.length === 0 && (
            <Text style={s.text}>No additional history or assumptions are available.</Text>
          )}
              </>}
            </View>}
          </View>;
        })}
    </>}
  </View>;
}
 