import React, { useEffect, useRef, useState } from "react";
import { Pressable } from "react-native";
import { Alert, Text, TextInput, View } from "../preferences/LocalizedNative";
import { useDashboardTheme } from "./dashboard/useDashboardTheme";
import { createDebtStyles } from "../styles/DebtStyles";
import { Debt, DebtPayment, loadDebtPayments, recordDebtPayment, removeDebtPayment } from "../services/debtService";
import { currencyCode, toAED } from "../preferences/currency";
import { formatAED } from "../utils/dashboard";
import { newRequestKey } from "../utils/addExpense";

const today = () => new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString().slice(0, 10);
type Props = { apiBaseUrl: string; debts: Debt[]; busy: boolean; onBusyChange: (value: boolean) => void; onChanged: () => void };
export default function DebtPaymentsPanel({ apiBaseUrl, debts, busy, onBusyChange, onChanged }: Props) {
  const { styles: d, palette } = useDashboardTheme();
  const s = createDebtStyles(palette);
  const [payments, setPayments] = useState<DebtPayment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Debt | null>(null);
  const [amount, setAmount] = useState("");
  const [paidOn, setPaidOn] = useState(today);
  const [revision, setRevision] = useState(0);
  const key = useRef("");
  const locked = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    let active = true; setLoading(true);
    loadDebtPayments(apiBaseUrl).then(rows => { if (active) { setPayments(rows); setError(""); } })
      .catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiBaseUrl, revision]);
  const start = (debt: Debt) => { if (busy || locked.current) return; setSelected(debt); setAmount(""); setPaidOn(today()); key.current = newRequestKey(); setError(""); };
  const save = async () => {
    if (!selected || busy || locked.current) return;
    const value = toAED(amount);
    const parsed = new Date(paidOn + "T00:00:00Z");
    if (!/^\d+(?:\.\d{1,2})?$/.test(amount) || !Number.isFinite(value) || value <= 0 || value > 1_000_000_000 || !/^\d{4}-\d{2}-\d{2}$/.test(paidOn) || !Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== paidOn || paidOn > today()) {
      setError("Enter a positive payment amount and a valid date on or before today (YYYY-MM-DD)."); return;
    }
    locked.current = true; onBusyChange(true); setError("");
    try {
      const row = await recordDebtPayment(apiBaseUrl, selected.id, { amount: value, paid_on: paidOn, request_key: key.current });
      if (mounted.current) { setPayments(rows => [row, ...rows.filter(item => item.id !== row.id)].sort((a, b) => b.paid_on.localeCompare(a.paid_on) || b.id - a.id)); setSelected(null); onChanged(); }
    } catch (e) { if (mounted.current) setError(e instanceof Error ? e.message : "Could not record payment."); }
    finally { locked.current = false; if (mounted.current) onBusyChange(false); }
  };
  const remove = (row: DebtPayment) => Alert.alert("Remove payment?", "Remove this payment from the debt payment history?", [
    { text: "Cancel", style: "cancel" }, { text: "Remove", style: "destructive", onPress: async () => {
      if (busy || locked.current) return;
      locked.current = true; onBusyChange(true);
      try { await removeDebtPayment(apiBaseUrl, row.id); if (mounted.current) { setPayments(rows => rows.filter(item => item.id !== row.id)); onChanged(); } }
      catch (e) { if (mounted.current) setError(e instanceof Error ? e.message : "Could not remove payment."); }
      finally { locked.current = false; if (mounted.current) onBusyChange(false); }
    } },
  ]);
  return <View style={d.card}>
    <Text style={s.formTitle}>Debt payments</Text>
    <Text style={d.cardSubtitle}>Record payments you have actually made. Savings uses their payment month.</Text>
    {!!error && <Text style={d.formError} accessibilityRole="alert">{error}</Text>}
    {selected ? <>
      <Text localize={false} style={[s.debtName, s.field]}>{selected.name}</Text>
      <Text style={d.editorLabel}>Amount paid</Text>
      <View style={d.inputRow}><Text style={d.inputPrefix}>{currencyCode()}</Text><TextInput value={amount} onChangeText={setAmount} editable={!busy} keyboardType="decimal-pad" maxLength={18} style={d.input} placeholder="0.00" placeholderTextColor={palette.textMuted} accessibilityLabel="Amount paid" /></View>
      <View style={s.field}><Text style={d.editorLabel}>Payment date (YYYY-MM-DD)</Text><TextInput value={paidOn} onChangeText={setPaidOn} editable={!busy} maxLength={10} style={s.fieldInput} placeholder="YYYY-MM-DD" placeholderTextColor={palette.textMuted} accessibilityLabel="Payment date" /></View>
      <Text style={s.hint}>The full payment reduces this loan's total left to pay.</Text>
      <View style={d.buttonRow}><Pressable disabled={busy} onPress={() => { setSelected(null); setError(""); }} style={[d.secondaryButton, busy && d.buttonDisabled]} accessibilityRole="button"><Text style={d.secondaryButtonText}>Cancel</Text></Pressable><Pressable disabled={busy} onPress={() => { void save(); }} style={[d.primaryButton, busy && d.buttonDisabled]} accessibilityRole="button"><Text style={d.primaryButtonText}>{busy ? "Saving…" : "Save payment"}</Text></Pressable></View>
    </> : debts.map(debt => <View key={debt.id} style={s.paymentRow}><Text localize={false} style={s.paymentName}>{debt.name}</Text><Pressable disabled={busy || loading} onPress={() => start(debt)} style={[d.compactAddButton, (busy || loading) && d.buttonDisabled]} accessibilityRole="button" accessibilityLabel="Record payment"><Text style={d.compactAddButtonText}>Record payment</Text></Pressable></View>)}
    {!loading && !payments.length && <Text style={[d.mutedText, s.field]}>No debt payments recorded yet.</Text>}
    {payments.map(row => <View key={row.id} style={s.paymentRow}><View style={s.paymentBody}><Text localize={false} style={s.debtName}>{row.debt_name}</Text><Text style={d.mutedText}>{row.paid_on}{row.automatic ? " - Automatically recorded" : ""}</Text><Text style={d.statValue}>{formatAED(row.amount)}</Text></View><Pressable disabled={busy} onPress={() => remove(row)} style={[s.editButton, busy && d.buttonDisabled]} accessibilityRole="button" accessibilityLabel="Remove payment"><Text style={s.editText}>Remove</Text></Pressable></View>)}
    {!!error && !selected && <Pressable disabled={busy} onPress={() => setRevision(value => value + 1)} style={d.secondaryButton} accessibilityRole="button"><Text style={d.secondaryButtonText}>Refresh payments</Text></Pressable>}
  </View>;
}
