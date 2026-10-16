import React, { useRef, useState } from "react";
import { Pressable } from "react-native";
import { Text, TextInput, View } from "../preferences/LocalizedNative";
import { useDashboardTheme } from "./dashboard/useDashboardTheme";
import { createSavingsStyles } from "../styles/SavingsStyles";
import { ManualSavings, SavingsGoal, saveManualSavings } from "../services/savingsService";
import { amountDraft, currencyCode, toAED } from "../preferences/currency";
import { newRequestKey } from "../utils/addExpense";

// general: extra savings (money saved outside monthly income and spending),
// counted in total savings only. goal: total savings and one goal's progress.
// edit: correct an entry, including moving it between general and a goal.
export type SavingsFormKind = "general" | "goal" | "edit";

type Props = {
  apiBaseUrl: string;
  kind: SavingsFormKind;
  goals: SavingsGoal[];
  entry?: ManualSavings;
  goalId?: string | null;
  disabled: boolean;
  onBusyChange: (busy: boolean) => void;
  onCancel: () => void;
  onSaved: (entry: ManualSavings, created: boolean) => void;
};

export default function SavingsEntryForm({ apiBaseUrl, kind, goals, entry, goalId: initialGoal, disabled, onBusyChange, onCancel, onSaved }: Props) {
  const { styles: d, palette } = useDashboardTheme();
  const s = createSavingsStyles(palette);
  const [amount, setAmount] = useState(entry ? amountDraft(entry.amount) : "");
  const [label, setLabel] = useState(entry?.label ?? "");
  const [goalId, setGoalId] = useState<string | null>(
    kind === "edit" ? entry?.goal_id ?? null
      : kind === "goal" ? initialGoal ?? (goals.length === 1 ? goals[0].id : null)
        : null);
  const [error, setError] = useState("");
  const locked = useRef(false);
  const key = useRef(newRequestKey());
  const choices = kind === "edit" ? [{ id: null, title: "Extra savings" }, ...goals] : kind === "goal" ? goals : [];

  const save = async () => {
    if (locked.current || disabled) return;
    const baseAmount = toAED(amount, entry?.amount);
    if (!/^\d+(?:\.\d{1,2})?$/.test(amount) || !Number.isFinite(baseAmount) || baseAmount <= 0 || baseAmount > 1_000_000_000) {
      setError("Enter a positive savings amount with up to two decimal places."); return;
    }
    if (kind === "goal" && !goalId) { setError("Choose the goal this money is for."); return; }
    locked.current = true; onBusyChange(true); setError("");
    try {
      const fallback = kind === "goal" ? goals.find(goal => goal.id === goalId)?.title ?? "Goal savings" : "Extra savings";
      const body = { label: label.trim() || entry?.label || fallback, amount: baseAmount, goal_id: goalId, ...(entry ? {} : { request_key: key.current }) };
      onSaved(await saveManualSavings(apiBaseUrl, body, entry?.id), !entry);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save savings entry."); }
    finally { locked.current = false; onBusyChange(false); }
  };

  return <View style={d.card}>
    <Text style={d.cardLabel}>{kind === "general" ? "Add extra savings" : kind === "goal" ? "Add to a savings goal" : "Edit savings entry"}</Text>
    <Text style={[d.mutedText, s.formHint]}>{kind === "general"
      ? "Record money you've set aside that isn't already included in your monthly savings."
      : kind === "goal" ? "Counts toward your total savings and the goal you choose."
        : "Change the amount, label or where this money counts."}</Text>
    {!!error && <Text style={d.formError} accessibilityRole="alert">{error}</Text>}
    {choices.length > 0 && <View style={s.goalChoices} accessibilityRole="radiogroup">
      {choices.map(goal => {
        const selected = goalId === goal.id;
        return <Pressable key={goal.id ?? "general"} disabled={disabled} onPress={() => setGoalId(goal.id)} accessibilityRole="radio" accessibilityState={{ selected, disabled }} style={[s.goalChoice, selected && s.goalChoiceActive]}>
          <Text localize={goal.id === null} style={[s.goalChoiceText, selected && s.goalChoiceTextActive]}>{goal.title}</Text>
        </Pressable>;
      })}
    </View>}
    <View style={[d.inputRow, s.formField]}><Text style={d.inputPrefix}>{currencyCode()}</Text><TextInput value={amount} onChangeText={setAmount} editable={!disabled} keyboardType="decimal-pad" maxLength={18} style={d.input} placeholder="0.00" placeholderTextColor={palette.textMuted} accessibilityLabel="Savings amount" autoFocus={!entry} /></View>
    <View style={[d.inputRow, s.formField]}><TextInput value={label} onChangeText={setLabel} editable={!disabled} maxLength={80} style={d.input} placeholder="Description (optional)" placeholderTextColor={palette.textMuted} accessibilityLabel="Savings description" /></View>
    <Text style={[d.mutedText, s.note]}>Don't record money already included in confirmed monthly savings or another savings entry.</Text>
    <View style={d.buttonRow}>
      <Pressable disabled={disabled} onPress={onCancel} style={[d.secondaryButton, disabled && d.buttonDisabled]} accessibilityRole="button"><Text style={d.secondaryButtonText}>Cancel</Text></Pressable>
      <Pressable disabled={disabled} onPress={() => { void save(); }} style={[d.primaryButton, disabled && d.buttonDisabled]} accessibilityRole="button"><Text style={d.primaryButtonText}>{disabled ? "Saving…" : "Save savings"}</Text></Pressable>
    </View>
  </View>;
}
