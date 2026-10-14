import React, { useRef, useState } from "react";
import { Pressable } from "react-native";
import { Text, TextInput, View } from "../../preferences/LocalizedNative";
import { useDashboardTheme } from "../dashboard/useDashboardTheme";
import { amountDraft, toAED, currencyCode } from "../../preferences/currency";
import { apiFetch } from "../../services/apiClient";
import type { FinancialPlan } from "../../types/plans";

type Props = { plan: FinancialPlan; apiBaseUrl: string; onPreview: (plan: FinancialPlan) => void; onCancel: () => void; onBusyChange: (busy: boolean) => void };
export default function BudgetPlanEditor({ plan, apiBaseUrl, onPreview, onCancel, onBusyChange }: Props) {
  const { styles: s, palette } = useDashboardTheme();
  const [goal, setGoal] = useState(plan.title);
  const [target, setTarget] = useState(amountDraft(plan.targetAmount));
  const [progress, setProgress] = useState(amountDraft(plan.savedAmount));
  const [monthly, setMonthly] = useState(amountDraft(plan.monthlyContribution));
  const [deadline, setDeadline] = useState(plan.deadline ?? "");
  const [byDeadline, setByDeadline] = useState(plan.profile.monthly_contribution == null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const locked = useRef(false);
  const preview = async () => {
    if (locked.current) return;
    const validMoney = (value: string) => /^\d+(?:\.\d{1,2})?$/.test(value);
    if (!goal.trim() || !validMoney(target) || !validMoney(progress) || (!byDeadline && !validMoney(monthly))) { setError("Enter a goal and valid amounts."); return; }
    const profile = { ...plan.profile, goal: goal.trim(), target_amount: toAED(target, plan.targetAmount), current_amount: toAED(progress, plan.savedAmount), monthly_contribution: byDeadline ? null : toAED(monthly, plan.monthlyContribution), deadline: byDeadline ? deadline : plan.deadline };
    locked.current = true; setBusy(true); onBusyChange(true); setError("");
    try {
      const response = await apiFetch(apiBaseUrl, "/planning/budget-plans/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile, choices: plan.budgetChoices ?? {}, budget_fingerprint: plan.budgetFingerprint, request_key: plan.confirmationKey }) });
      const value = await response.json();
      if (!response.ok) throw new Error(typeof value.detail === "string" ? value.detail : "Check your goal amounts and date.");
      onPreview(value);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not review plan."); }
    finally { locked.current = false; setBusy(false); onBusyChange(false); }
  };
  const field = (label: string, value: string, change: (value: string) => void, money = true) => <View style={s.editor}><Text style={s.editorLabel}>{label}</Text><View style={s.inputRow}>{money && <Text style={s.inputPrefix}>{currencyCode()}</Text>}<TextInput editable={!busy} accessibilityLabel={label} style={s.input} value={value} onChangeText={change} keyboardType={money ? "decimal-pad" : "default"} placeholderTextColor={palette.textMuted} maxLength={money ? 18 : 200} /></View></View>;
  return <View style={s.card}>
    {field("Goal", goal, setGoal, false)}
    {field("Target amount", target, setTarget)}
    {field("Already saved for this goal", progress, setProgress)}
    <Pressable disabled={busy} onPress={() => setByDeadline(value => !value)} style={s.secondaryButton}><Text style={s.secondaryButtonText}>{byDeadline ? "Choose a monthly saving amount" : "Choose a target deadline"}</Text></Pressable>
    {byDeadline ? field("Target date (YYYY-MM-DD)", deadline, setDeadline, false) : field("Monthly saving amount", monthly, setMonthly)}
    {!!error && <Text style={s.formError} accessibilityRole="alert">{error}</Text>}
    <View style={s.buttonRow}><Pressable disabled={busy} onPress={onCancel} style={s.secondaryButton}><Text style={s.secondaryButtonText}>Cancel</Text></Pressable><Pressable disabled={busy} onPress={() => { void preview(); }} style={[s.primaryButton, busy && s.buttonDisabled]}><Text style={s.primaryButtonText}>{busy ? "Reviewing…" : "Review plan"}</Text></Pressable></View>
  </View>;
}
