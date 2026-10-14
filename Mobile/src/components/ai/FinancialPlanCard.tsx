import { formatDisplayAmount } from "../../preferences/currency";
import React, { useState } from "react";
import { Pressable } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import IncomeDonut from "../IncomeDonut";
import { incomeChart } from "../../utils/incomeChart";
import { ChevronDown, ChevronUp } from "lucide-react-native";
import { useAITheme } from "./useAITheme";
import { createPlanningStyles } from "../../styles/PlanningStyles";
import type { FinancialPlan } from "../../types/plans";
import { formatAED, formatPercent } from "../../utils/dashboard";
import { formatPlanningDate } from "../../utils/planningDate";
import { percentOf, planScenario } from "../../utils/planVisuals";

type Props = { plan: FinancialPlan; onSave?: () => void; onEdit?: () => void; onDelete?: () => void; busy?: boolean };

export default function FinancialPlanCard({ plan, onSave, onEdit, onDelete, busy = false }: Props) {
  const { palette, chartColors } = useAITheme();
  const s = createPlanningStyles(palette);
  const [details, setDetails] = useState(false);
  const [proposed, setProposed] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const scenario = planScenario(plan, proposed);
  const rows = plan.allocations.map((row, i) => ({ ...row, color: chartColors[i % chartColors.length], amount: proposed ? row.target : row.baseline }));
  const chart = incomeChart(rows.map(row => ({ label: row.category, amount: row.amount, color: row.color })), plan.income);
  const focus = rows.find(row => row.category === selected);
  const barMax = Math.max(1, ...rows.map(row => Math.max(row.baseline, row.target)));
  const cutTotal = plan.spendingCuts.reduce((sum, cut) => sum + cut.monthlyAmount, 0);
  const goalPercent = percentOf(plan.savedAmount, plan.targetAmount);
  const spendingGoal = plan.kind === "spending";
  const select = (category: string) => setSelected(current => current === category ? null : category);

  return <View style={s.card}>
    <View style={s.planHeading}>
      <Text style={s.planEyebrow}>{plan.id ? "SAVED PLAN" : "DRAFT PLAN"}</Text>
      <Text localize={false} style={s.title}>{plan.title}</Text>
      {plan.profile.household_size != null && <Text style={s.text}>{plan.profile.household_size} {plan.profile.household_size === 1 ? "person" : "people"} supported{plan.deadline ? ` · Target ${formatPlanningDate(plan.deadline)}` : ""}</Text>}
      {plan.budgetGoalSource && plan.profile.household_size == null && plan.deadline && <Text style={s.text}>Target {formatPlanningDate(plan.deadline)}</Text>}
    </View>

    <View style={s.scenarioSwitch} accessibilityRole="tablist">
      {[false, true].map(value => <Pressable key={String(value)} accessibilityRole="tab" accessibilityState={{ selected: proposed === value }}
        onPress={() => setProposed(value)} style={[s.scenarioOption, proposed === value && s.scenarioActive]}>
        <Text style={[s.scenarioLabel, proposed === value && s.scenarioLabelActive]}>{value ? "Proposed plan" : "Current estimates"}</Text>
      </Pressable>)}
    </View>

    <View style={s.metricGrid}>
      <View style={s.metric}><Text style={s.metricLabel}>Monthly income</Text><Text style={s.metricValue}>{formatAED(plan.income)}</Text></View>
      <View style={s.metric}><Text style={s.metricLabel}>Monthly costs</Text><Text style={s.metricValue}>{formatAED(scenario.spending)}</Text></View>
      <View style={s.metric}><Text style={s.metricLabel}>{scenario.available < 0 ? "Expense deficit" : "Available after costs"}</Text><Text style={[s.metricValue, scenario.available < 0 ? s.dangerText : s.accentText]}>{formatAED(Math.abs(scenario.available))}</Text></View>
      <View style={s.metric}><Text style={s.metricLabel}>{proposed ? "Proposed monthly cuts" : "Before proposed cuts"}</Text><Text style={s.metricValue}>{proposed ? formatAED(cutTotal) : "Your baseline"}</Text></View>
    </View>

    <View style={s.visualSection}>
      <View style={s.sectionHeading}><Text style={s.sectionTitle}>{spendingGoal ? "Spending ceiling" : "Monthly goal funding"}</Text><Text style={[s.sectionStat, scenario.shortfall > .005 ? s.dangerText : s.accentText]}>{scenario.shortfall > .005 ? "Needs adjustment" : "Fits this scenario"}</Text></View>
      <Text style={s.fundingValue}>{formatAED(spendingGoal ? scenario.spending : scenario.contribution)}<Text style={s.text}> / month</Text></Text>
      <Text style={s.text}>{spendingGoal ? `Monthly spending ceiling: ${formatAED(plan.targetAmount)}` : `Needed: ${formatAED(plan.requiredMonthly)} / month`}</Text>
      {spendingGoal && plan.targetAmount > 0 && <>
        <View accessibilityRole="progressbar" accessibilityLabel="Spending ceiling used" accessibilityValue={{ min: 0, max: 100, now: Math.round(percentOf(scenario.spending, plan.targetAmount)) }} style={s.progressTrack}>
          <View style={[s.progressFill, scenario.spending > plan.targetAmount && s.ceilingExceeded, { width: `${percentOf(scenario.spending, plan.targetAmount)}%` }]} />
        </View>
        <Text style={s.text}>{scenario.spending > plan.targetAmount ? `${formatAED(scenario.spending - plan.targetAmount)} above your spending ceiling.` : `${formatAED(plan.targetAmount - scenario.spending)} below your spending ceiling.`}</Text>
      </>}
      {!spendingGoal && plan.requiredMonthly > 0 && <>
        <View accessibilityRole="progressbar" accessibilityLabel="Monthly goal funding" accessibilityValue={{ min: 0, max: 100, now: Math.round(scenario.fundedPercent) }} style={s.progressTrack}>
          <View style={[s.progressFill, { width: `${scenario.fundedPercent}%` }]} />
        </View>
        <Text style={s.text}>{formatPercent(scenario.fundedPercent)} of the required monthly allocation is covered.</Text>
      </>}
      {scenario.shortfall > .005 && <Text style={s.shortfall}>{formatAED(scenario.shortfall)} more needed per month{proposed ? " after proposed cuts" : " before cuts"}.</Text>}
      {scenario.expenseDeficit > .005 && <Text style={s.error}>Costs exceed income by {formatAED(scenario.expenseDeficit)}. This deficit must be covered before funding the goal.</Text>}
      {!spendingGoal && plan.requiredMonthly === 0 && <Text style={s.text}>The entered progress already meets the target.</Text>}
      <Text style={s.caption}>This is a calculated scenario based on your estimates, not recorded savings.</Text>
    </View>

    {onSave && <Pressable style={[s.button, busy && s.muted]} disabled={busy} onPress={onSave}><Text style={s.buttonText}>{busy ? "Saving…" : "Save Plan"}</Text></Pressable>}
    {onEdit && <Pressable style={[s.button, s.secondary, busy && s.muted]} disabled={busy} onPress={onEdit}><Text style={s.secondaryText}>Adjust My Plan</Text></Pressable>}

    <View style={s.visualSection}>
      <Text style={s.sectionTitle}>Where your monthly money goes</Text>
      <Text style={s.caption}>{proposed ? "Proposed category costs" : "Baseline category estimates"} as a share of household income · Tap a slice or category</Text>
      <View style={s.planChart}>
        <IncomeDonut chart={chart} size={200} grey={palette.textMuted} danger={palette.danger} selected={selected} onSelect={select} />
        <View pointerEvents="none" style={s.planChartCenter}>
          <Text style={s.chartLabel}>{focus ? focus.category : chart.validIncome ? "Household income" : "Income needed"}</Text>
          <Text style={s.chartCurrency}>AED</Text>
          <Text style={s.chartValue} adjustsFontSizeToFit numberOfLines={1}>{focus ? formatDisplayAmount(focus.amount) : chart.validIncome ? formatDisplayAmount(plan.income) : "—"}</Text>
          {focus && chart.validIncome && <Text style={s.caption}>{formatPercent(focus.amount / plan.income * 100)} of income</Text>}
        </View>
      </View>
      {scenario.spending === 0 && <Text style={s.text}>No monthly costs entered in this scenario.</Text>}
      {!chart.validIncome && <Text style={s.text}>A positive household income is needed to show category percentages. Costs are listed below.</Text>}
      {chart.overBy > 0 && <Text style={s.error}>Costs exceed income by {formatAED(chart.overBy)}. The full red ring means all income has been used; percentages below show the actual overage.</Text>}
      <View style={s.chartLegend}>
        {rows.map(row => <Pressable key={row.category} accessibilityRole="button" accessibilityState={{ selected: selected === row.category }}
          accessibilityLabel={`${row.category}, ${formatAED(row.amount)}${chart.validIncome ? `, ${formatPercent(row.amount / plan.income * 100)} of income` : ""}`}
          onPress={() => select(row.category)} style={[s.chartLegendRow, selected === row.category && s.legendSelected]}>
          <View style={[s.chartDot, { backgroundColor: row.color }]} /><Text style={s.legendCategory}>{row.category}</Text>
          <View style={s.legendNumbers}><Text style={s.legendAmount}>{formatAED(row.amount)}</Text><Text style={s.caption}>{chart.validIncome ? formatPercent(row.amount / plan.income * 100) : "—"}</Text></View>
        </Pressable>)}
        {chart.validIncome && <View style={s.chartLegendRow}>
          <View style={[s.chartDot, { backgroundColor: palette.textMuted }]} /><Text style={s.legendCategory}>Income left after costs</Text>
          <View style={s.legendNumbers}><Text style={s.legendAmount}>{formatAED(chart.remaining!)}</Text><Text style={s.caption}>{formatPercent(chart.remainingPercent!)}</Text></View>
        </View>}
      </View>
      {chart.validIncome && <Text style={s.caption}>The whole circle is {formatAED(plan.income)} of household income. Grey is the amount left after costs, before allocating money to your goal.</Text>}
      {focus && <View style={s.categoryFocus}>
        <Text style={s.label}>{focus.category}</Text><Text style={s.text}>Baseline {formatAED(focus.baseline)} → proposed {formatAED(focus.target)}</Text>
        <Text style={s.text}>{focus.baseline > focus.target ? `Proposed reduction: ${formatAED(focus.baseline - focus.target)} / month.` : "No reduction proposed."} {focus.source}.</Text>
      </View>}
    </View>

    <View style={s.visualSection}>
      <Text style={s.sectionTitle}>Category comparison</Text>
      <Text style={s.caption}>Current is your monthly estimate. Proposed is the suggested amount for your plan.</Text>
      <Text style={s.caption}>Every full bar represents {formatAED(barMax)} per month.</Text>
      <View style={s.comparisonScale}>
        <View style={s.scaleStart}><Text style={s.scaleLabel} numberOfLines={1} adjustsFontSizeToFit>{formatAED(0)}</Text></View>
        <View style={s.scaleMiddle}><Text style={s.scaleLabel} numberOfLines={1} adjustsFontSizeToFit>{formatAED(barMax / 2)}</Text></View>
        <View style={s.scaleEnd}><Text style={s.scaleLabel} numberOfLines={1} adjustsFontSizeToFit>{formatAED(barMax)}</Text></View>
      </View>
      {rows.map(row => <Pressable key={row.category} accessibilityRole="button" accessibilityState={{ selected: selected === row.category }} onPress={() => select(row.category)}
        accessibilityLabel={`${row.category}: current ${formatAED(row.baseline)}, proposed ${formatAED(row.target)}`} style={[s.comparisonRow, selected === row.category && s.legendSelected]}>
        <Text style={s.comparisonCategory}>{row.category}</Text>
        <View style={s.comparisonPair}>
          <View style={s.comparisonBarHeading}><Text style={s.comparisonLabel}>Current</Text><Text style={s.comparisonAmount} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={.8}>{formatAED(row.baseline)}</Text></View>
          <View style={s.comparisonTrack}><View style={[s.comparisonFill, s.baselineFill, { width: `${percentOf(row.baseline, barMax)}%` }]} /></View>
        </View>
        <View style={s.comparisonPair}>
          <View style={s.comparisonBarHeading}><Text style={[s.comparisonLabel, s.accentText]}>Proposed</Text><Text style={s.comparisonAmount} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={.8}>{formatAED(row.target)}</Text></View>
          <View style={s.comparisonTrack}><View style={[s.comparisonFill, s.targetFill, { width: `${percentOf(row.target, barMax)}%` }]} /></View>
        </View>
        <Text style={row.baseline - row.target > .005 ? s.reductionLabel : s.caption}>{Math.abs(row.baseline - row.target) <= .005 ? "No change proposed" : row.baseline > row.target ? `Suggested reduction: ${formatAED(row.baseline - row.target)} / month` : `Proposed increase: ${formatAED(row.target - row.baseline)} / month`}</Text>
      </Pressable>)}
      <Text style={s.caption}>Amounts in AED per month. Proposed targets are estimates, not recorded spending.</Text>
    </View>

    {!spendingGoal && <View style={s.visualSection}>
      <View style={s.sectionHeading}><Text style={s.sectionTitle}>{plan.kind === "debt" ? "Debt goal progress" : "Savings goal progress"}</Text><Text style={s.sectionStat}>{formatPercent(goalPercent)}</Text></View>
      <View style={s.progressTrack} accessibilityRole="progressbar" accessibilityLabel="Entered goal progress" accessibilityValue={{ min: 0, max: 100, now: Math.round(goalPercent) }}><View style={[s.progressFill, { width: `${goalPercent}%` }]} /></View>
      <Text style={s.text}>{formatAED(plan.savedAmount)} entered toward {formatAED(plan.targetAmount)}</Text>
      <Text style={s.caption}>Based on progress you entered. Saving this plan does not add money to this total.</Text>
    </View>}

    <Pressable style={[s.button, s.secondary]} onPress={() => setDetails(!details)} accessibilityRole="button" accessibilityState={{ expanded: details }}>
      <View style={s.datePickerLabel}><Text style={s.secondaryText}>{details ? "Hide advice and assumptions" : `Advice and assumptions${plan.warnings.length ? ` · ${plan.warnings.length} notes` : ""}`}</Text>{details ? <ChevronUp color={palette.text} size={18} /> : <ChevronDown color={palette.text} size={18} />}</View>
    </Pressable>
    {details && <View style={s.detailSection}>
      {plan.spendingCuts.map(cut => <Text key={cut.category} style={s.text}>{cut.category}: proposed reduction of {formatAED(cut.monthlyAmount)} / month. {cut.reason}</Text>)}
      {plan.historyAdvice?.map((advice, i) => <Text key={`advice-${i}`} style={s.text}>{advice}</Text>)}
      {plan.warnings.map((warning, i) => <Text key={`warning-${i}`} style={s.error}>{warning}</Text>)}
      {plan.historyComparisons.map(row => <Text key={row.category} style={s.text}>{row.category}: historical average {formatAED(row.historicalMonthly)}; estimate {formatAED(row.plannedMonthly)}.</Text>)}
      {plan.assumptions.map((note, i) => <Text key={`note-${i}`} style={s.caption}>{note}</Text>)}
    </View>}
    {onDelete && <Pressable style={s.deleteAction} disabled={busy} onPress={onDelete}><Text style={s.error}>Delete Plan</Text></Pressable>}
  </View>;
}
