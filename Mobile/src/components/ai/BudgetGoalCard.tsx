import React, { useState } from "react";
import { Pressable } from "react-native";
import { Text, TextInput, View } from "../../preferences/LocalizedNative";
import { useDashboardTheme } from "../dashboard/useDashboardTheme";
import type { BudgetGoal, BudgetChoice } from "../../types/chat";
import { formatAED } from "../../utils/dashboard";
import { amountDraft, currencyCode, toAED } from "../../preferences/currency";

type Props = { assessment: BudgetGoal; disabled: boolean; onChoice: (choice: BudgetChoice) => void };
export default function BudgetGoalCard({ assessment: a, disabled, onChoice }: Props) {
  const { styles: s } = useDashboardTheme();
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  if (!a.ready || (a.feasible && !a.suggestions.length)) return null;
  return <View>
    {a.suggestions.map(row => <View key={row.category} style={s.editor}>
      <Text localize={false} style={s.editorLabel}>{row.category}</Text>
      <Text style={s.mutedText}>{row.essential ? "Could you realistically manage this essential cost on a lower amount?" : "Would this nonessential reduction work for you?"}</Text>
      <Text style={s.mutedText}>{formatAED(row.baseline)} → {formatAED(row.target)} / month</Text>
      <Text style={s.mutedText}>Frees up: {formatAED(row.monthlyAmount)} / month</Text>
      <Text style={[s.editorLabel, s.heroHint]}>Or enter an amount you can manage</Text>
      <View style={s.inputRow}><Text style={s.inputPrefix}>{currencyCode()}</Text><TextInput
        accessibilityLabel={`Scenario amount for ${row.category}`} keyboardType="decimal-pad" maxLength={18}
        editable={!disabled} style={s.input} value={drafts[row.category] ?? amountDraft(row.target)}
        onChangeText={value => setDrafts(previous => ({ ...previous, [row.category]: value }))}
      /></View>
      <View style={s.buttonRow}>
        <Pressable disabled={disabled} accessibilityRole="button" onPress={() => {
          const raw = drafts[row.category] ?? amountDraft(row.target);
          const value = toAED(raw, row.target);
          if (!/^\d+(?:\.\d{1,2})?$/.test(raw) || !Number.isFinite(value) || value < 0 || value > row.baseline) {
            setError("Enter a valid amount no higher than the current category budget."); return;
          }
          setError(""); onChoice({ category: row.category, target: value, fingerprint: a.budget_fingerprint });
        }} style={[s.primaryButton, disabled && s.buttonDisabled]}><Text style={s.primaryButtonText}>Try this amount</Text></Pressable>
        <Pressable disabled={disabled} accessibilityRole="button" onPress={() => onChoice({ category: row.category, target: null, fingerprint: a.budget_fingerprint })} style={[s.secondaryButton, disabled && s.buttonDisabled]}><Text style={s.secondaryButtonText}>Cannot reduce</Text></Pressable>
      </View>
    </View>)}
    {!!error && <Text style={s.formError} accessibilityRole="alert">{error}</Text>}
    {!a.feasible && <Pressable disabled={disabled} accessibilityRole="button" onPress={() => onChoice({ category: "*", target: a.protected.includes("*") ? 0 : null, fingerprint: a.budget_fingerprint })} style={[s.secondaryButton, s.budgetSetupAction, disabled && s.buttonDisabled]}><Text style={s.secondaryButtonText}>{a.protected.includes("*") ? "Explore possible cuts" : "Keep my budget unchanged"}</Text></Pressable>}
  </View>;
}
