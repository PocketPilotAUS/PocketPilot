import React, { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { useAITheme } from "./useAITheme";
import { createPlanningStyles } from "../../styles/PlanningStyles";
import type { FinancialPlan } from "../../types/plans";
import { formatAED } from "../../utils/dashboard";

export default function FinancialPlanCard({ plan, onSave, onEdit, onDelete, busy = false }: { plan: FinancialPlan; onSave?: () => void; onEdit?: () => void; onDelete?: () => void; busy?: boolean }) {
  const { palette } = useAITheme(); const s = createPlanningStyles(palette);
  const [details, setDetails] = useState(false);
  return <View style={s.card}>
    <Text style={s.title}>{plan.title}</Text>
    <Text style={s.text}>{plan.id ? "Saved plan" : "Draft · review before saving"} · {plan.profile.household_size} people supported</Text>
    <Text style={s.label}>{plan.feasible ? "Goal fits this scenario" : "Goal needs adjustment"}</Text>
    <Text style={s.text}>Income {formatAED(plan.income)} · Expenses {formatAED(plan.baselineSpending)}</Text>
    <Text style={s.text}>Available now: {formatAED(plan.availableBefore)} / month</Text>
    <Text style={s.text}>Required for goal: {formatAED(plan.requiredMonthly)} / month{plan.deadline ? ` through ${plan.deadline}` : ""}</Text>
    <Text style={s.text}>Affordable allocation after proposed cuts: {formatAED(plan.monthlyContribution)} / month</Text>
    {plan.spendingCuts.map(cut => <Text key={cut.category} style={s.text}>Consider reducing {cut.category} by {formatAED(cut.monthlyAmount)} / month. {cut.reason}</Text>)}
    {plan.historyAdvice?.map((advice, index) => <Text key={`advice-${index}`} style={s.text}>{advice}</Text>)}
    {plan.warnings.map((warning, index) => <Text key={index} style={s.error}>{warning}</Text>)}
    <Pressable style={[s.button, s.secondary]} onPress={() => setDetails(!details)}><Text style={s.secondaryText}>{details ? "Hide details" : "View category targets and history"}</Text></Pressable>
    {details && <>
      {plan.allocations.map(row => <View key={row.category}><Text style={s.label}>{row.category}: {formatAED(row.target)} / month</Text><Text style={s.text}>Baseline {formatAED(row.baseline)} · {row.source}</Text></View>)}
      {plan.historyComparisons.map(row => <Text key={row.category} style={s.text}>{row.category}: past monthly average {formatAED(row.historicalMonthly)}; current estimate {formatAED(row.plannedMonthly)}.</Text>)}
      {plan.assumptions.map((note, index) => <Text key={index} style={s.text}>{note}</Text>)}
      <Text style={s.text}>Already saved/paid toward goal: {formatAED(plan.savedAmount)}. Planned contributions do not increase recorded progress.</Text>
    </>}
    {onSave && <Pressable style={[s.button, busy && s.muted]} disabled={busy} onPress={onSave}><Text style={s.buttonText}>{busy ? "Saving…" : "Save Plan"}</Text></Pressable>}
    {onEdit && <Pressable style={[s.button, s.secondary]} disabled={busy} onPress={onEdit}><Text style={s.secondaryText}>Edit Plan</Text></Pressable>}
    {onDelete && <Pressable disabled={busy} onPress={onDelete}><Text style={s.error}>Delete Plan</Text></Pressable>}
  </View>;
}
