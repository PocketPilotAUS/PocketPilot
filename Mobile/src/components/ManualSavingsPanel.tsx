import React, { useRef, useState } from "react";
import { Pressable } from "react-native";
import { Pencil, Trash2 } from "lucide-react-native";
import { Alert, Text, View } from "../preferences/LocalizedNative";
import { useDashboardTheme } from "./dashboard/useDashboardTheme";
import { createSavingsStyles } from "../styles/SavingsStyles";
import { ManualSavings, SavingsGoal, deleteManualSavings } from "../services/savingsService";
import { formatAED } from "../utils/dashboard";

// Saved entries, grouped so goal savings and general savings are never confused.
type Props = { apiBaseUrl: string; entries: ManualSavings[]; goals: SavingsGoal[]; disabled: boolean; onBusyChange: (busy: boolean) => void; onEdit: (entry: ManualSavings) => void; onChanged: (entries: ManualSavings[]) => void };
export default function ManualSavingsPanel({ apiBaseUrl, entries, goals, disabled, onBusyChange, onEdit, onChanged }: Props) {
  const { styles: d, palette } = useDashboardTheme();
  const s = createSavingsStyles(palette);
  const [error, setError] = useState("");
  const locked = useRef(false);
  if (!entries.length) return null;
  const remove = (entry: ManualSavings) => Alert.alert("Remove savings entry?", "This removes only this entry. Confirmed monthly savings stay unchanged.", [{ text: "Cancel", style: "cancel" }, { text: "Delete", style: "destructive", onPress: async () => {
    if (locked.current || disabled) return;
    locked.current = true; onBusyChange(true); setError("");
    try { await deleteManualSavings(apiBaseUrl, entry.id); onChanged(entries.filter(row => row.id !== entry.id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not remove savings entry."); }
    finally { locked.current = false; onBusyChange(false); }
  } }]);
  const row = (entry: ManualSavings) => <View key={entry.id} style={s.manualRow}>
    <View style={s.manualBody}>
      <Text localize={entry.label === "Previous savings" || entry.label === "Extra savings"} style={s.rowTitle}>{entry.label}</Text>
      <Text style={s.rowValue}>{formatAED(entry.amount)}</Text>
      {entry.goal_id && <Text localize={false} style={s.goalTag}>{goals.find(goal => goal.id === entry.goal_id)?.title ?? ""}</Text>}
    </View>
    <Pressable disabled={disabled} onPress={() => onEdit(entry)} accessibilityRole="button" accessibilityLabel="Edit savings entry" style={s.manualAction}><Pencil size={17} color={palette.textSecondary} /></Pressable>
    <Pressable disabled={disabled} onPress={() => remove(entry)} accessibilityRole="button" accessibilityLabel="Remove savings entry" style={s.manualAction}><Trash2 size={17} color={palette.danger} /></Pressable>
  </View>;
  const goalEntries = entries.filter(entry => entry.goal_id);
  const generalEntries = entries.filter(entry => !entry.goal_id);
  return <View style={d.card}>
    <Text style={s.historyTitle}>Savings entries</Text>
    {!!error && <Text style={d.formError} accessibilityRole="alert">{error}</Text>}
    {goalEntries.length > 0 && <><Text style={s.groupTitle}>Goal savings</Text>{goalEntries.map(row)}</>}
    {generalEntries.length > 0 && <><Text style={s.groupTitle}>Extra savings</Text>{generalEntries.map(row)}</>}
  </View>;
}
