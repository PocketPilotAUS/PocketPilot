import React from "react";
import { Pressable } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import { useAITheme } from "./useAITheme";
import { createPlanningStyles } from "../../styles/PlanningStyles";
import { formatAED } from "../../utils/dashboard";
import { formatPlanningDate } from "../../utils/planningDate";
import type { FinancialPlan } from "../../types/plans";

type Props = { plan: FinancialPlan; busy?: boolean; onSave?: () => void; onEdit?: () => void; onDelete?: () => void };
export default function DebtPlanDetails({ plan, busy, onSave, onEdit, onDelete }: Props) {
  const { palette } = useAITheme();
  const s = createPlanningStyles(palette);
  const metric = (label: string, value: string) => <View style={s.metric}><Text style={s.metricLabel}>{label}</Text><Text style={s.metricValue}>{value}</Text></View>;
  return <View style={s.card}>
    <Text style={s.planEyebrow}>{plan.id ? "SAVED PLAN" : "DRAFT PLAN"}</Text>
    <Text localize={false} style={s.title}>{plan.title}</Text>
    <View style={s.metricGrid}>
      {metric("Estimated total repayment", formatAED(plan.targetAmount))}
      {metric("Monthly debt payment", formatAED(plan.monthlyContribution))}
      {metric("Regular payment already budgeted", formatAED(plan.regularMonthly ?? 0))}
      {metric("Extra monthly payment", formatAED(plan.extraMonthly ?? 0))}
      {plan.estimatedInterest != null && metric("Estimated remaining interest", formatAED(plan.estimatedInterest))}
      {plan.estimatedInterestSaved != null && metric("Estimated interest saved", formatAED(plan.estimatedInterestSaved))}
      {plan.deadline && metric("Target date", formatPlanningDate(plan.deadline))}
      {plan.months != null && metric("Monthly payments", String(plan.months))}
      {metric("Left after extra repayment", formatAED(plan.leftAfterGoal ?? 0))}
    </View>
    <Text style={s.caption}>This is a saved-budget scenario, not a payment history or bank balance. Recording payments happens on the Debt page.</Text>
    {plan.assumptions.map((note, index) => <Text key={index} style={s.caption}>{note}</Text>)}
    {onSave && <Pressable accessibilityRole="button" disabled={busy} onPress={onSave} style={[s.button, busy && s.muted]}><Text style={s.buttonText}>Save plan</Text></Pressable>}
    {onEdit && <Pressable accessibilityRole="button" disabled={busy} onPress={onEdit} style={[s.button, s.secondary, busy && s.muted]}><Text style={s.secondaryText}>Adjust plan</Text></Pressable>}
    {onDelete && <Pressable accessibilityRole="button" disabled={busy} onPress={onDelete} style={[s.button, s.secondary, busy && s.muted]}><Text style={s.secondaryText}>Delete plan</Text></Pressable>}
  </View>;
}
