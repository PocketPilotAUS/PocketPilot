import React, { useEffect, useState } from "react";
import { Text, TextInput, View } from "../preferences/LocalizedNative";
import MetallicGlassCard from "./MetallicGlassCard";
import MetallicGlassButton from "./MetallicGlassButton";
import { useAppTheme } from "../theme/ThemeContext";
import { apiFetch, SessionExpiredError } from "../services/apiClient";
import { createIncomeStyles } from "../styles/IncomeStyles";

export type BudgetAllocation = { category: string; percentage: number; target: number | null; spent: number };
export type MonthlyBudget = { ideal_budget?: { customized: boolean; mode?: "amounts"; planned_total?: number; planned_remaining?: number | null; unbudgeted?: { category: string; spent: number }[]; allocations: BudgetAllocation[] } | null; year: number; month: number; income: number | null; spent: number; remaining: number | null; spent_percentage: number | null };
type Props = { budget: MonthlyBudget | null; loading: boolean; apiBaseUrl: string; onSaved: (budget: MonthlyBudget) => void };
export default function MonthlyIncomeCard({ budget, loading, apiBaseUrl, onSaved }: Props) {
  const { colors } = useAppTheme();
  const styles = createIncomeStyles(colors);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { setDraft(budget?.income == null ? "" : String(budget.income)); }, [budget]);
  const save = async () => {
    if (!/^\d+(\.\d{1,2})?$/.test(draft.trim()) || Number(draft) > 1000000000) { setError("Enter an income of 0 to 1,000,000,000 AED with up to two decimal places."); return; }
    if (!budget) return;
    setSaving(true); setError("");
    try {
      const response = await apiFetch(apiBaseUrl, `/budget/income?year=${budget.year}&month=${budget.month}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ amount: draft.trim() }) });
      if (!response.ok) throw new Error("save");
      onSaved(await response.json()); setEditing(false);
    } catch (err) { if (!(err instanceof SessionExpiredError)) setError("Could not save income. Please try again."); }
    finally { setSaving(false); }
  };
  const over = (budget?.remaining ?? 0) < 0;
  return <MetallicGlassCard>
    <Text style={styles.label}>MONTHLY BUDGET{budget ? ` · ${new Date(budget.year, budget.month - 1, 1).toLocaleDateString("en", { month: "long" }).toUpperCase()}` : ""}</Text>
    {loading || !budget ? <Text style={styles.amount}>{loading ? "Loading…" : "Budget unavailable"}</Text> : <>
      <Text style={styles.amount}>{budget.income == null ? "Set your monthly income" : `AED ${budget.income.toFixed(2)}`}</Text>
      <Text style={styles.hint}>Monthly income</Text>
      <View style={styles.row}><Text style={styles.body}>Spent this month</Text><Text style={styles.value}>AED {budget.spent.toFixed(2)}</Text></View>
      {budget.remaining !== null && <View style={styles.row}><Text style={styles.body}>{over ? "Over income" : "Remaining"}</Text><Text style={[styles.value, over && styles.error]}>AED {Math.abs(budget.remaining).toFixed(2)}</Text></View>}
      {budget.spent_percentage !== null ? <>
        <View style={styles.track} accessibilityRole="progressbar" accessibilityLabel="Monthly income spent" accessibilityValue={{ min: 0, max: 100, now: Math.min(100, budget.spent_percentage), text: `${budget.spent_percentage.toFixed(1)}% spent` }}><View style={[styles.fill, { width: `${Math.min(100, Math.max(0, budget.spent_percentage))}%`, backgroundColor: over ? colors.error : colors.primary }]} /></View>
        <Text style={styles.hint}>{budget.spent_percentage.toFixed(1)}% of income spent</Text>
      </> : <Text style={styles.hint}>{budget.income === 0 ? "No income this month; percentage unavailable." : "Add income to see how much your spending uses."}</Text>}
      {editing ? <>
        <TextInput accessibilityLabel="Monthly income in AED" style={styles.input} value={draft} onChangeText={setDraft} keyboardType="decimal-pad" placeholder="Monthly income in AED" placeholderTextColor={colors.textMuted} editable={!saving} />
        <MetallicGlassButton title={saving ? "Saving…" : "Save Income"} onPress={() => { void save(); }} disabled={saving} />
        <MetallicGlassButton title="Cancel" variant="secondary" onPress={() => { setEditing(false); setError(""); setDraft(budget.income == null ? "" : String(budget.income)); }} disabled={saving} />
      </> : <MetallicGlassButton title={budget.income == null ? "Add Monthly Income" : "Edit Income"} variant="secondary" onPress={() => setEditing(true)} style={styles.button} />}
      {!!error && <Text style={styles.error}>{error}</Text>}
    </>}
  </MetallicGlassCard>;
}
