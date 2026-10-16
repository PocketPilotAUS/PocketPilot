import { amountDraft, currencyCode, toAED } from "../preferences/currency";
import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable } from "react-native";
import { Pencil, RefreshCw, Repeat } from "lucide-react-native";
import { Alert, Text, TextInput, View } from "../preferences/LocalizedNative";
import BottomSheet from "./transactions/BottomSheet";
import CategoryIcon from "./transactions/CategoryIcon";
import { useTransactionsTheme } from "./transactions/useTransactionsTheme";
import { apiFetch, SessionExpiredError } from "../services/apiClient";
import { Debt, loadDebts } from "../services/debtService";
import { formatAED } from "../utils/dashboard";
import { formatShortDate } from "../utils/transactions";

type Schedule = { id: number; amount: number; category: string; description: string | null; day: number; next_date: string; active: boolean };

// Compact rows matching the transaction list; editing and stopping happen in a sheet
export default function RecurringExpenses({ apiBaseUrl, onChanged, onOpenDebt }: { apiBaseUrl: string; onChanged: () => void; onOpenDebt?: () => void }) {
  const { styles, tx, palette } = useTransactionsTheme();
  const [debts, setDebts] = useState<Debt[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Schedule | null>(null);
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("");
  const [day, setDay] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  // A second tap while a request is running must never send it twice
  const locked = useRef(false);
  useEffect(() => {
    let active = true;
    setLoading(true);
    const load = async () => {
      try { const [response, debtRows] = await Promise.all([apiFetch(apiBaseUrl, "/recurring/"), loadDebts(apiBaseUrl)]); if (!response.ok) throw new Error(); const data = await response.json(); if (active) { setSchedules(data); setDebts(debtRows.filter(row => row.total_left_to_pay > 0)); setError(""); } }
      catch (err) { if (active && !(err instanceof SessionExpiredError)) setError("Could not load recurring expenses."); }
      finally { if (active) setLoading(false); }
    };
    void load(); return () => { active = false; };
  }, [apiBaseUrl, refresh]);
  const open = (schedule: Schedule) => {
    if (busy) return;
    setEditing(schedule); setAmount(amountDraft(schedule.amount)); setCategory(schedule.category); setDay(String(schedule.day)); setFormError("");
  };
  const close = () => { if (!busy) setEditing(null); };
  const update = async (schedule: Schedule, stop = false) => {
    if (locked.current) return;
    if (!stop && (!/^\d+(\.\d{1,2})?$/.test(amount) || toAED(amount) <= 0 || toAED(amount) > 1000000000 || !category.trim() || !/^\d{1,2}$/.test(day) || Number(day) < 1 || Number(day) > 31)) { setFormError("Enter a valid amount, category and payment day (1–31)."); return; }
    locked.current = true; setBusy(true); setFormError("");
    try {
      const response = await apiFetch(apiBaseUrl, `/recurring/${schedule.id}${stop ? "/stop" : ""}`, stop ? { method: "POST" } : { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ amount: String(toAED(amount, schedule.amount)), category: category.trim(), description: schedule.description, day: Number(day) }) });
      if (!response.ok) throw new Error();
      const saved: Schedule = await response.json();
      setSchedules(current => current.map(item => item.id === saved.id ? saved : item)); setEditing(null); onChanged();
    } catch (err) { if (!(err instanceof SessionExpiredError)) setFormError("Could not update this recurring expense. Please retry."); }
    finally { locked.current = false; setBusy(false); }
  };
  const stop = (schedule: Schedule) => Alert.alert("Stop repeating?", "Future payments will stop. Previously recorded expenses remain.", [{ text: "Cancel", style: "cancel" }, { text: "Stop", style: "destructive", onPress: () => { void update(schedule, true); } }]);
  const active = schedules.filter(schedule => schedule.active).length + debts.filter(debt => debt.automatic_day != null).length;

  return <View>
    <View style={tx.groupHeader}>
      <Text style={tx.groupTitle}>Recurring expenses</Text>
      {active > 0 && <Text style={tx.groupTotal}>{active} active</Text>}
    </View>
    {loading && <View style={[tx.groupCard, tx.recurringState]}><ActivityIndicator color={palette.accent} /></View>}
    {!loading && !!error && <View style={[tx.groupCard, tx.recurringState]}>
      <Text style={styles.mutedText}>{error}</Text>
      <Pressable onPress={() => setRefresh(value => value + 1)} style={styles.pill} accessibilityRole="button"><RefreshCw size={13} color={palette.accent} /><Text style={styles.pillText}>Retry</Text></Pressable>
    </View>}
    {!loading && !error && schedules.length === 0 && debts.length === 0 && <View style={[tx.groupCard, tx.recurringState]}>
      <Repeat size={18} color={palette.textMuted} />
      <Text style={styles.mutedText}>Turn on Repeat monthly when adding an expense.</Text>
    </View>}
    {!loading && !error && schedules.length > 0 && <View style={tx.groupCard}>
      {schedules.map((schedule, index) => {
        const description = schedule.description?.trim();
        return <View key={schedule.id} style={[tx.row, index > 0 && tx.rowDivider, !schedule.active && tx.recurringStopped]}>
          <CategoryIcon category={schedule.category} />
          <View style={tx.rowText}>
            <Text style={tx.rowTitle} numberOfLines={1}>{schedule.category}{description ? <Text localize={false} style={tx.rowSubtitle}> · {description}</Text> : null}</Text>
            <Text style={tx.rowSubtitle} numberOfLines={1}>{schedule.active ? `Monthly · Next ${formatShortDate(schedule.next_date)}` : "Stopped"}</Text>
          </View>
          <Text style={tx.rowAmount}>{formatAED(schedule.amount)}</Text>
          {schedule.active && <Pressable onPress={() => open(schedule)} disabled={busy} hitSlop={6} style={({ pressed }) => [tx.recurringEdit, pressed && tx.rowPressed]} accessibilityRole="button" accessibilityLabel={`Edit recurring ${schedule.category}`}>
            <Pencil size={15} color={palette.textSecondary} strokeWidth={2.2} />
          </Pressable>}
        </View>;
      })}
    </View>}

    {!loading && !error && debts.length > 0 && <View style={tx.groupCard}>
      {debts.map((debt, index) => <View key={`debt:${debt.id}`} style={[tx.row, index > 0 && tx.rowDivider]}>
        <CategoryIcon category="Debt" />
        <View style={tx.rowText}>
          <Text style={tx.rowTitle} numberOfLines={1}>Debt<Text localize={false} style={tx.rowSubtitle}> - {debt.name}</Text></Text>
          <Text style={tx.rowSubtitle} numberOfLines={1}>{debt.next_due ? `Monthly - Next ${formatShortDate(debt.next_due)}` : "Monthly - Automatic payments off"}</Text>
        </View>
        <Text style={tx.rowAmount}>{formatAED(debt.estimated_monthly_payment)}</Text>
        {onOpenDebt && <Pressable onPress={onOpenDebt} style={tx.recurringEdit} accessibilityRole="button" accessibilityLabel={`Manage recurring debt ${debt.name}`}><Pencil size={15} color={palette.textSecondary} strokeWidth={2.2} /></Pressable>}
      </View>)}
    </View>}

    <BottomSheet visible={editing !== null} title="Edit recurring expense" onClose={close}>
      {editing && <View style={tx.recurringForm}>
        {!!formError && <Text style={styles.formError} accessibilityRole="alert">{formError}</Text>}
        <Text style={styles.editorLabel}>Amount</Text>
        <View style={styles.inputRow}><Text style={styles.inputPrefix}>{currencyCode()}</Text><TextInput accessibilityLabel="Recurring amount" style={styles.input} value={amount} onChangeText={setAmount} keyboardType="decimal-pad" maxLength={18} editable={!busy} /></View>
        <Text style={styles.editorLabel}>Category</Text>
        <View style={styles.inputRow}><TextInput accessibilityLabel="Recurring category" style={styles.input} value={category} onChangeText={setCategory} maxLength={40} editable={!busy} /></View>
        <Text style={styles.editorLabel}>Payment day each month (1–31)</Text>
        <View style={styles.inputRow}><TextInput accessibilityLabel="Recurring payment day" style={styles.input} value={day} onChangeText={setDay} keyboardType="number-pad" maxLength={2} editable={!busy} /></View>
        <Text style={styles.mutedText}>Changes apply to upcoming payments. Past expenses stay unchanged.</Text>
        <Pressable onPress={() => { void update(editing); }} disabled={busy} style={[styles.primaryButton, tx.recurringSave, busy && styles.buttonDisabled]} accessibilityRole="button">
          <Text style={styles.primaryButtonText}>{busy ? "Saving…" : "Save changes"}</Text>
        </Pressable>
        <Pressable onPress={() => stop(editing)} disabled={busy} style={({ pressed }) => [tx.deleteButton, (pressed || busy) && tx.rowPressed]} accessibilityRole="button">
          <Repeat size={17} color={palette.danger} strokeWidth={2.2} /><Text style={tx.deleteText}>Stop repeating</Text>
        </Pressable>
      </View>}
    </BottomSheet>
  </View>;
}
