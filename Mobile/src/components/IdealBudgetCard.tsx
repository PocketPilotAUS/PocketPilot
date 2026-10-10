import React, { useState } from "react";
import { Text, TextInput, View } from "react-native";
import MetallicGlassCard from "./MetallicGlassCard";
import MetallicGlassButton from "./MetallicGlassButton";
import type { MonthlyBudget } from "./MonthlyIncomeCard";
import { useAppTheme } from "../theme/ThemeContext";
import { createIncomeStyles } from "../styles/IncomeStyles";
import { apiFetch, SessionExpiredError } from "../services/apiClient";

type Props = { budget: MonthlyBudget | null; apiBaseUrl: string; onSaved: (budget: MonthlyBudget) => void };
export default function IdealBudgetCard({ budget, apiBaseUrl, onSaved }: Props) {
  const { colors } = useAppTheme();
  const styles = createIncomeStyles(colors);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const allocations = budget?.ideal_budget?.allocations;
  if (!budget || !allocations) return null;
  const total = Object.values(draft).reduce((sum, value) => sum + Number(value), 0);
  const save = async () => {
    if (Object.values(draft).some(value => !/^\d{1,3}$/.test(value) || Number(value) > 100) || total !== 100) {
      setError("Use whole percentages from 0 to 100. The total must be 100%."); return;
    }
    setSaving(true); setError("");
    try {
      const response = await apiFetch(apiBaseUrl, `/budget/plan?year=${budget.year}&month=${budget.month}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ percentages: Object.fromEntries(Object.entries(draft).map(([key, value]) => [key, Number(value)])) }),
      });
      if (!response.ok) throw new Error("save");
      onSaved(await response.json()); setEditing(false);
    } catch (err) { if (!(err instanceof SessionExpiredError)) setError("Could not save your budget. Please try again."); }
    finally { setSaving(false); }
  };
  return <MetallicGlassCard>
    <Text style={styles.label}>IDEAL MONTHLY BUDGET</Text>
    <Text style={styles.hint}>{budget.ideal_budget?.customized ? "Your custom allocation for this month." : "A starting split based on 50% needs, 30% wants and 20% savings / debt. Category percentages are examples—adjust them for your bills and goals."}</Text>
    {budget.income == null && <Text style={styles.hint}>Add your monthly income above to see suggested AED amounts.</Text>}
    {allocations.map(item => {
      const savings = item.category === "Savings / debt";
      const over = item.target !== null && item.spent > item.target;
      return <View key={item.category}>
        <View style={styles.row}>
          <Text style={styles.value}>{item.category}</Text>
          <Text style={styles.value}>{item.target == null ? `${item.percentage}%` : `AED ${item.target.toFixed(2)} · ${item.percentage}%`}</Text>
        </View>
        {editing ? <TextInput accessibilityLabel={`${item.category} budget percentage`} style={styles.input} keyboardType="number-pad" value={draft[item.category]} onChangeText={value => setDraft(current => ({ ...current, [item.category]: value }))} editable={!saving} maxLength={3} /> : !savings && <>
          <Text style={[styles.hint, over && styles.error]}>Spent AED {item.spent.toFixed(2)}{over ? ` · AED ${(item.spent - item.target!).toFixed(2)} over budget` : ""}</Text>
          {item.target !== null && <View style={styles.track} accessibilityRole="progressbar" accessibilityLabel={`${item.category} budget spent`} accessibilityValue={{ min: 0, max: 100, now: item.target > 0 ? Math.min(100, item.spent / item.target * 100) : item.spent > 0 ? 100 : 0 }}><View style={[styles.fill, { width: `${item.target > 0 ? Math.min(100, item.spent / item.target * 100) : item.spent > 0 ? 100 : 0}%`, backgroundColor: over ? colors.error : colors.primary }]} /></View>}
        </>}
        {savings && <Text style={styles.hint}>Planned allocation; this does not record a saving or debt payment.</Text>}
      </View>;
    })}
    <Text style={styles.hint}>Unmatched expense categories count toward Other. Essential bills and minimum debt payments should take priority.</Text>
    {editing ? <>
      <Text style={[styles.hint, total !== 100 && styles.error]}>Allocated: {total}% of income</Text>
      <MetallicGlassButton title={saving ? "Saving…" : "Save Budget"} onPress={() => { void save(); }} disabled={saving} />
      <MetallicGlassButton title="Cancel" variant="secondary" onPress={() => { setEditing(false); setError(""); }} disabled={saving} />
    </> : <MetallicGlassButton title="Edit Budget Split" variant="secondary" style={styles.button} onPress={() => { setDraft(Object.fromEntries(allocations.map(item => [item.category, String(item.percentage)]))); setEditing(true); }} />}
    {!!error && <Text style={styles.error}>{error}</Text>}
  </MetallicGlassCard>;
}
