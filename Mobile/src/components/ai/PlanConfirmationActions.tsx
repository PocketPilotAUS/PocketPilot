import React from "react";
import { Pressable } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import { useDashboardTheme } from "../dashboard/useDashboardTheme";
import type { FinancialPlan } from "../../types/plans";

type Props = { plan: FinancialPlan; dismissed: boolean; busy: boolean; onConfirm: () => void; onEdit: () => void; onDecline: () => void };
export default function PlanConfirmationActions({ plan, dismissed, busy, onConfirm, onEdit, onDecline }: Props) {
  const { styles: s } = useDashboardTheme();
  if (!plan.ready) return null;
  if (plan.id) return <Text style={s.heroHint}>Plan confirmed. Find it in Plans.</Text>;
  if (dismissed) return <Text style={s.heroHint}>Plan left unconfirmed.</Text>;
  return <View>
    <View style={s.buttonRow}>
      <Pressable accessibilityRole="button" disabled={busy} onPress={onConfirm} style={[s.primaryButton, busy && s.buttonDisabled]}><Text style={s.primaryButtonText}>{busy ? "Saving…" : "Confirm plan"}</Text></Pressable>
      <Pressable accessibilityRole="button" disabled={busy} onPress={onEdit} style={[s.secondaryButton, busy && s.buttonDisabled]}><Text style={s.secondaryButtonText}>Edit plan</Text></Pressable>
    </View>
    <Pressable accessibilityRole="button" disabled={busy} onPress={onDecline} style={[s.secondaryButton, s.budgetSetupAction, busy && s.buttonDisabled]}><Text style={s.secondaryButtonText}>Not now</Text></Pressable>
  </View>;
}
