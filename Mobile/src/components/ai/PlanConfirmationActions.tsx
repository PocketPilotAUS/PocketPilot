import React from "react";
import { Pressable } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import { useDashboardTheme } from "../dashboard/useDashboardTheme";
import { useAITheme } from "./useAITheme";
import { createPlanningStyles } from "../../styles/PlanningStyles";
import { formatAED } from "../../utils/dashboard";
import { formatPlanningDate } from "../../utils/planningDate";
import type { FinancialPlan } from "../../types/plans";

// Server-verified figures only; nothing here is calculated on the phone.
function PlanSummary({ plan }: { plan: FinancialPlan }) {
  const { palette } = useAITheme();
  const p = createPlanningStyles(palette);
  const metric = (label: string, value: string) => <View style={p.metric}><Text style={p.metricLabel}>{label}</Text><Text style={p.metricValue}>{value}</Text></View>;
  return <View style={{ marginTop: 12 }}>
    <Text style={p.planEyebrow}>{plan.id ? "SAVED PLAN" : "DRAFT PLAN"}</Text>
    <Text localize={false} style={p.title}>{plan.title}</Text>
    <View style={p.metricGrid}>
      {metric(plan.debtGoalSource ? "Estimated total repayment" : "Goal amount", formatAED(plan.targetAmount))}
      {metric(plan.debtGoalSource ? "Monthly debt payment" : "Monthly saving", formatAED(plan.monthlyContribution))}
      {plan.debtGoalSource && metric("Extra above regular payment", formatAED(plan.extraMonthly ?? 0))}
      {plan.debtGoalSource && plan.estimatedInterest != null && metric("Estimated remaining interest", formatAED(plan.estimatedInterest))}
      {plan.debtGoalSource && plan.estimatedInterestSaved != null && metric("Estimated interest saved", formatAED(plan.estimatedInterestSaved))}
      {plan.months != null && metric("Months", String(plan.months))}
      {plan.deadline && metric("Target date", formatPlanningDate(plan.deadline))}
      {metric("Left after goal", formatAED(plan.debtGoalSource ? plan.leftAfterGoal ?? 0 : plan.availableAfter))}
    </View>
    {plan.debtGoalSource && plan.estimatedInterestSaved != null && <Text style={p.caption}>Fixed-rate estimate; fees and lender-specific adjustments are excluded.</Text>}
  </View>;
}

type Props = { plan: FinancialPlan; dismissed: boolean; busy: boolean; saving?: boolean; onConfirm: () => void; onEdit: () => void; onDecline: () => void };
export default function PlanConfirmationActions({ plan, dismissed, busy, saving = false, onConfirm, onEdit, onDecline }: Props) {
  const { styles: s } = useDashboardTheme();
  if (!plan.ready) return null;
  const summary = plan.budgetGoalSource ? <PlanSummary plan={plan} /> : null;
  if (plan.id) return <View>{summary}<Text style={s.heroHint}>Plan saved. Find it in My Financial Plans.</Text></View>;
  if (dismissed) return <View>{summary}<Text style={s.heroHint}>Plan rejected. Nothing was saved.</Text></View>;
  return <View>
    {summary}
    <Text style={s.heroHint}>Not saved yet. Accept to save it to My Financial Plans.</Text>
    <View style={s.buttonRow}>
      <Pressable accessibilityRole="button" disabled={busy} onPress={onConfirm} style={[s.primaryButton, busy && s.buttonDisabled]}><Text style={s.primaryButtonText}>{saving ? "Saving…" : "Accept plan"}</Text></Pressable>
      <Pressable accessibilityRole="button" disabled={busy} onPress={onEdit} style={[s.secondaryButton, busy && s.buttonDisabled]}><Text style={s.secondaryButtonText}>Adjust</Text></Pressable>
    </View>
    <Pressable accessibilityRole="button" disabled={busy} onPress={onDecline} style={[s.secondaryButton, s.budgetSetupAction, busy && s.buttonDisabled]}><Text style={s.secondaryButtonText}>Reject</Text></Pressable>
  </View>;
}
