import React, { useState } from "react";
import { Pressable } from "react-native";
import { Text, TextInput, View } from "../../preferences/LocalizedNative";
import KeyboardFormScrollView from "../KeyboardFormScrollView";
import { useAITheme } from "./useAITheme";
import { createPlanningStyles } from "../../styles/PlanningStyles";
import { PLAN_CATEGORIES, FinancialPlan, PlanningContext, PlanningProfile } from "../../types/plans";
import { planningRequest } from "../../services/planningService";
import { SessionExpiredError } from "../../services/apiClient";
import { formatAED } from "../../utils/dashboard";
import PlanningDateField from "./PlanningDateField";
import { formatPlanningDate, parsePlanningDate, planningDateError } from "../../utils/planningDate";

export const initialProfile = (context: PlanningContext): PlanningProfile => ({
  income: context.current_income, other_income: null, household_size: null, goal: null, goal_kind: null,
  target_amount: null, current_amount: null, deadline: null, expenses: {}, typical_months: [], protected_categories: [], ...context.profile,
});
export default function PlanningForm({ apiBaseUrl, context, initial, onPreview, onCancel }: { apiBaseUrl: string; context: PlanningContext; initial?: PlanningProfile; onPreview: (plan: FinancialPlan) => void; onCancel: () => void }) {
  const { palette } = useAITheme(); const s = createPlanningStyles(palette);
  const [profile, setProfile] = useState<PlanningProfile>(initial ?? initialProfile(context));
  const [deadlineText, setDeadlineText] = useState(() => formatPlanningDate((initial ?? initialProfile(context)).deadline));
  const [dateError, setDateError] = useState<string | null>(null);
  const updateDeadline = (text: string) => {
    setDeadlineText(text);
    setDateError(null);
    setProfile(current => ({ ...current, deadline: parsePlanningDate(text) }));
  };
  const [step, setStep] = useState(0); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const change = (key: keyof PlanningProfile, value: unknown) => setProfile(current => ({ ...current, [key]: value }));
  const field = (label: string, key: keyof PlanningProfile, numeric = true, hint?: string) => <View key={key} style={{ gap: 8 }}>
    <Text style={s.label}>{label}</Text>
    {hint && <Text style={s.text}>{hint}</Text>}
    <TextInput style={s.input} accessibilityLabel={label} placeholder={numeric ? "Enter amount or 0 if none" : "Enter here"} placeholderTextColor={palette.textMuted} keyboardType={numeric ? "decimal-pad" : "default"} value={profile[key] == null ? "" : String(profile[key])} editable={!busy} onChangeText={value => change(key, value === "" ? null : key === "household_size" ? Number(value) : value)} />
  </View>;
  const preview = async () => {
    const invalidDate = planningDateError(deadlineText);
    if (invalidDate) { setDateError(invalidDate); setStep(1); return; }
    setBusy(true); setError("");
    try {
      const result = await planningRequest<FinancialPlan & { missing?: string[] }>(apiBaseUrl, "/profile", "PUT", profile);
      if (!result.ready) { setError(`Still needed: ${result.missing?.join(", ")}. Use 0 only when a cost truly does not apply.`); return; }
      onPreview(result);
    } catch (err) { if (!(err instanceof SessionExpiredError)) setError((err as Error).message); }
    finally { setBusy(false); }
  };
  return <KeyboardFormScrollView contentContainerStyle={s.content}>
    <View style={s.card}>
      <Text style={s.title}>{["Your household", "Your main goal", "Monthly expenses"][step]}</Text>
      <Text style={s.text}>Step {step + 1} of 3 · AED · Details stay in your planning profile. They do not record paid expenses.</Text>
      {step === 0 && <>
        {field("Monthly take-home income", "income")}
        {field("Additional household income", "other_income", true, "Include only income available to this budget; do not count your income twice.")}
        {field("People supported by this budget", "household_size", true, "Include yourself and anyone whose costs this income supports.")}
      </>}
      {step === 1 && <>
        {field("What is your main financial goal?", "goal", false)}
        <View style={s.row}>{(["savings", "debt", "spending"] as const).map(kind => <Pressable key={kind} style={[s.chip, profile.goal_kind === kind && s.selected]} onPress={() => change("goal_kind", kind)}><Text style={s.text}>{kind === "spending" ? "Control spending" : kind === "debt" ? "Pay off debt" : "Save money"}</Text></Pressable>)}</View>
        {field(profile.goal_kind === "spending" ? "Monthly spending ceiling" : "Target amount", "target_amount")}
        {profile.goal_kind !== "spending" && field("Already saved or paid toward this goal", "current_amount")}
        {profile.goal_kind !== "spending" && <PlanningDateField value={deadlineText} onChange={updateDeadline} error={dateError} disabled={busy} />}
        <Text style={s.text}>Debt planning here allocates extra payments after minimums. Interest and an exact payoff schedule need a separate debt calculation.</Text>
      </>}
      {step === 2 && <>
        <Text style={s.label}>Use your previous spending as a reference</Text>
        <Text style={s.text}>Select only months that are fully recorded and typical. Blank category amounts then use those months’ averages. A zero in a confirmed complete month means no spending in that category.</Text>
        {Object.entries(context.past_months).map(([month, categories]) => <View key={month}>
          <Pressable style={[s.chip, profile.typical_months.includes(month) && s.selected]} onPress={() => change("typical_months", profile.typical_months.includes(month) ? profile.typical_months.filter(m => m !== month) : [...profile.typical_months, month])}><Text style={s.text}>{profile.typical_months.includes(month) ? "✓ " : ""}{month} · {formatAED(Object.values(categories).reduce((a, n) => a + n, 0))} · Confirm complete and typical</Text></Pressable>
          <Text style={s.text}>{Object.entries(categories).map(([key, amount]) => `${key} ${formatAED(amount)}`).join(" · ")}</Text>
        </View>)}
        {!Object.keys(context.past_months).length && <Text style={s.text}>No past recorded months yet. Enter monthly estimates below.</Text>}
        {!!Object.keys(context.recurring_obligations).length && <><Text style={s.text}>Active recurring commitments: {Object.entries(context.recurring_obligations).map(([key, amount]) => `${key} ${formatAED(amount)}`).join(" · ")}</Text><Pressable style={[s.button, s.secondary]} onPress={() => setProfile(current => ({ ...current, expenses: { ...context.recurring_obligations, ...current.expenses } }))}><Text style={s.secondaryText}>Use recurring amounts for blank categories</Text></Pressable></>}
        {PLAN_CATEGORIES.map(category => <View key={category} style={{ gap: 8 }}>
          <Text style={s.label}>{category === "Debt payments" ? "Required minimum debt payments" : category}</Text>
          <TextInput style={s.input} accessibilityLabel={`${category} monthly estimate`} placeholder={profile.typical_months.length ? "Use confirmed history average" : "Unknown · enter amount or 0 if none"} placeholderTextColor={palette.textMuted} keyboardType="decimal-pad" value={profile.expenses[category] == null ? "" : String(profile.expenses[category])} onChangeText={value => setProfile(current => ({ ...current, expenses: { ...current.expenses, [category]: value === "" ? null : value } }))} editable={!busy} />
          {["Entertainment", "Shopping", "Subscriptions"].includes(category) && <Pressable style={[s.chip, profile.protected_categories.includes(category) && s.selected]} onPress={() => change("protected_categories", profile.protected_categories.includes(category) ? profile.protected_categories.filter(key => key !== category) : [...profile.protected_categories, category])}><Text style={s.text}>{profile.protected_categories.includes(category) ? "✓ Essential for my household" : "Mark essential for my household"}</Text></Pressable>}
        </View>)}
      </>}
      {!!error && <Text accessibilityRole="alert" style={s.error}>{error}</Text>}
      {step < 2 ? <Pressable style={s.button} onPress={() => {
        if (step === 1 && profile.goal_kind !== "spending") {
          const invalidDate = planningDateError(deadlineText);
          if (invalidDate) { setDateError(invalidDate); return; }
        }
        setStep(step + 1); setError("");
      }}><Text style={s.buttonText}>Continue</Text></Pressable> : <Pressable style={[s.button, busy && s.muted]} disabled={busy} onPress={() => { if (profile.goal_kind === "spending") { void previewSpending(); } else { void preview(); } }}><Text style={s.buttonText}>{busy ? "Checking…" : "Review My Plan"}</Text></Pressable>}
      {step > 0 && <Pressable disabled={busy} style={[s.button, s.secondary]} onPress={() => setStep(step - 1)}><Text style={s.secondaryText}>Back</Text></Pressable>}
      <Pressable disabled={busy} onPress={onCancel}><Text style={s.text}>Cancel</Text></Pressable>
    </View>
  </KeyboardFormScrollView>;

  async function previewSpending() {
    setBusy(true); setError("");
    try {
      const result = await planningRequest<FinancialPlan & { missing?: string[] }>(apiBaseUrl, "/profile", "PUT", { ...profile, current_amount: 0, deadline: null });
      if (!result.ready) setError(`Still needed: ${result.missing?.join(", ")}`); else onPreview(result);
    } catch (err) { if (!(err instanceof SessionExpiredError)) setError((err as Error).message); }
    finally { setBusy(false); }
  }
}
