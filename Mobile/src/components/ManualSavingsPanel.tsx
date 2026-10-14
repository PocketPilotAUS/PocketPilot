import React, { useRef, useState } from "react";
import { Pressable } from "react-native";
import { Pencil, Plus, Trash2 } from "lucide-react-native";
import { Alert, Text, TextInput, View } from "../preferences/LocalizedNative";
import { useDashboardTheme } from "./dashboard/useDashboardTheme";
import { createSavingsStyles } from "../styles/SavingsStyles";
import { ManualSavings, saveManualSavings, deleteManualSavings } from "../services/savingsService";
import { amountDraft, currencyCode, toAED } from "../preferences/currency";
import { formatAED } from "../utils/dashboard";
import { newRequestKey } from "../utils/addExpense";

type Props = { apiBaseUrl: string; entries: ManualSavings[]; disabled: boolean; onBusyChange: (busy: boolean) => void; onChanged: (entries: ManualSavings[]) => void };
export default function ManualSavingsPanel({ apiBaseUrl, entries, disabled, onBusyChange, onChanged }: Props) {
  const { styles: d, palette } = useDashboardTheme();
  const s = createSavingsStyles(palette);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ManualSavings | null>(null);
  const [label, setLabel] = useState("");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");
  const locked = useRef(false);
  const key = useRef("");
  const start = (entry?: ManualSavings) => {
    if (disabled) return;
    setEditing(entry ?? null); setLabel(entry?.label ?? ""); setAmount(entry ? amountDraft(entry.amount) : ""); setError(""); key.current = newRequestKey(); setOpen(true);
  };
  const save = async () => {
    if (locked.current || disabled) return;
    const baseAmount = toAED(amount, editing?.amount);
    if (!/^\d+(?:\.\d{1,2})?$/.test(amount) || !Number.isFinite(baseAmount) || baseAmount <= 0 || baseAmount > 1_000_000_000 || label.trim().length > 80) {
      setError("Enter a positive savings amount with up to two decimal places."); return;
    }
    locked.current = true; onBusyChange(true); setError("");
    try {
      const body = { label: label.trim() || "Previous savings", amount: baseAmount, ...(editing ? {} : { request_key: key.current }) };
      const row = await saveManualSavings(apiBaseUrl, body, editing?.id);
      onChanged([row, ...entries.filter(item => item.id !== row.id)]); setOpen(false); setEditing(null);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save savings entry."); }
    finally { locked.current = false; onBusyChange(false); }
  };
  const remove = (entry: ManualSavings) => Alert.alert("Remove savings entry?", "This removes only this manual entry. Confirmed monthly savings stay unchanged.", [{ text: "Cancel", style: "cancel" }, { text: "Delete", style: "destructive", onPress: async () => {
    if (locked.current || disabled) return;
    locked.current = true; onBusyChange(true); setError("");
    try { await deleteManualSavings(apiBaseUrl, entry.id); onChanged(entries.filter(row => row.id !== entry.id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not remove savings entry."); }
    finally { locked.current = false; onBusyChange(false); }
  } }]);
  return <View>
    {!open && <Pressable disabled={disabled} onPress={() => start()} accessibilityRole="button" accessibilityLabel="Add savings" accessibilityState={{ disabled }} style={({ pressed }) => [d.compactAddButton, s.manualAddButton, disabled && d.buttonDisabled, pressed && d.buttonDisabled]}><Plus size={16} color={palette.onAccent} strokeWidth={2.6} /><Text style={d.compactAddButtonText}>Add savings</Text></Pressable>}
    {(open || entries.length > 0 || !!error) && <View style={d.card}>
    {!!error && <Text style={d.formError} accessibilityRole="alert">{error}</Text>}
    {open && <>
      <Text style={d.editorLabel}>{editing ? "Edit savings entry" : "Add savings"}</Text>
      <View style={d.inputRow}><Text style={d.inputPrefix}>{currencyCode()}</Text><TextInput value={amount} onChangeText={setAmount} editable={!disabled} keyboardType="decimal-pad" maxLength={18} style={d.input} placeholder="0.00" placeholderTextColor={palette.textMuted} accessibilityLabel="Savings amount" /></View>
      <View style={s.field}><Text style={d.editorLabel}>Label (optional)</Text><View style={d.inputRow}><TextInput value={label} onChangeText={setLabel} editable={!disabled} maxLength={80} style={d.input} placeholder="Previous savings" placeholderTextColor={palette.textMuted} accessibilityLabel="Savings label" /></View></View>
      <Text style={[d.mutedText, s.note]}>Do not add money that is already included in confirmed monthly savings.</Text>
      <View style={d.buttonRow}><Pressable disabled={disabled} onPress={() => { setOpen(false); setError(""); }} style={[d.secondaryButton, disabled && d.buttonDisabled]}><Text style={d.secondaryButtonText}>Cancel</Text></Pressable><Pressable disabled={disabled} onPress={() => { void save(); }} style={[d.primaryButton, disabled && d.buttonDisabled]}><Text style={d.primaryButtonText}>{disabled ? "Saving…" : "Save savings"}</Text></Pressable></View>
    </>}
    {entries.map(entry => <View key={entry.id} style={s.manualRow}>
      <View style={s.manualBody}><Text localize={entry.label === "Previous savings"} style={s.rowTitle}>{entry.label}</Text><Text style={s.rowValue}>{formatAED(entry.amount)}</Text></View>
      <Pressable disabled={disabled} onPress={() => start(entry)} accessibilityRole="button" accessibilityLabel="Edit savings entry" style={s.manualAction}><Pencil size={17} color={palette.textSecondary} /></Pressable>
      <Pressable disabled={disabled} onPress={() => remove(entry)} accessibilityRole="button" accessibilityLabel="Remove savings entry" style={s.manualAction}><Trash2 size={17} color={palette.danger} /></Pressable>
    </View>)}
    </View>}
  </View>;
}
