import React, { useEffect, useState } from "react";
import { Alert, Text, TextInput, View } from "react-native";
import MetallicGlassCard from "./MetallicGlassCard";
import MetallicGlassButton from "./MetallicGlassButton";
import { apiFetch, SessionExpiredError } from "../services/apiClient";
import { useAppTheme } from "../theme/ThemeContext";
import { createRecurringStyles } from "../styles/RecurringStyles";

type Schedule = { id: number; amount: number; category: string; description: string | null; day: number; next_date: string; active: boolean };
export default function RecurringExpenses({ apiBaseUrl, onChanged }: { apiBaseUrl: string; onChanged: () => void }) {
  const { colors } = useAppTheme();
  const styles = createRecurringStyles(colors);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<number | null>(null);
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("");
  const [day, setDay] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    const load = async () => {
      try { const response = await apiFetch(apiBaseUrl, "/recurring/"); if (!response.ok) throw new Error(); const data = await response.json(); if (active) { setSchedules(data); setError(""); } }
      catch (err) { if (active && !(err instanceof SessionExpiredError)) setError("Could not load recurring expenses."); }
      finally { if (active) setLoading(false); }
    };
    void load(); return () => { active = false; };
  }, [apiBaseUrl, refresh]);
  const update = async (schedule: Schedule, stop = false) => {
    if (busy) return;
    if (!stop && (!/^\d+(\.\d{1,2})?$/.test(amount) || Number(amount) <= 0 || Number(amount) > 1000000000 || !category.trim() || !/^\d{1,2}$/.test(day) || Number(day) < 1 || Number(day) > 31)) { setError("Enter a valid amount, category and payment day (1–31)."); return; }
    setBusy(true); setError("");
    try {
      const response = await apiFetch(apiBaseUrl, `/recurring/${schedule.id}${stop ? "/stop" : ""}`, stop ? { method: "POST" } : { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ amount, category: category.trim(), description: schedule.description, day: Number(day) }) });
      if (!response.ok) throw new Error();
      const saved: Schedule = await response.json();
      setSchedules(current => current.map(item => item.id === saved.id ? saved : item)); setEditing(null); onChanged();
    } catch (err) { if (!(err instanceof SessionExpiredError)) setError("Could not update this recurring expense. Please retry."); }
    finally { setBusy(false); }
  };
  return <View>
    <Text style={styles.title}>Recurring Expenses</Text>
    {loading && <Text style={styles.body}>Loading schedules…</Text>}
    {!!error && <><Text style={styles.error}>{error}</Text><MetallicGlassButton title="Retry" onPress={() => setRefresh(value => value + 1)} /></>}
    {!loading && schedules.length === 0 && !error && <Text style={styles.body}>Turn on Repeat monthly when adding an expense.</Text>}
    {schedules.map(schedule => <MetallicGlassCard key={schedule.id}>
      <Text style={styles.heading}>{schedule.category} · AED {schedule.amount.toFixed(2)}</Text>
      <Text style={styles.body}>{schedule.active ? `Monthly on day ${schedule.day} · Next: ${schedule.next_date}` : "Stopped"}</Text>
      {editing === schedule.id ? <>
        <TextInput accessibilityLabel="Recurring amount in AED" style={styles.input} value={amount} onChangeText={setAmount} keyboardType="decimal-pad" editable={!busy} />
        <TextInput accessibilityLabel="Recurring category" style={styles.input} value={category} onChangeText={setCategory} maxLength={40} editable={!busy} />
        <TextInput accessibilityLabel="Recurring payment day" style={styles.input} value={day} onChangeText={setDay} keyboardType="number-pad" maxLength={2} editable={!busy} />
        <Text style={styles.body}>Changes apply to upcoming payments. Past expenses stay unchanged.</Text>
        <MetallicGlassButton title={busy ? "Saving…" : "Save Changes"} onPress={() => { void update(schedule); }} disabled={busy} />
        <MetallicGlassButton title="Cancel" variant="secondary" onPress={() => setEditing(null)} disabled={busy} />
      </> : schedule.active && <>
        <MetallicGlassButton title="Edit Schedule" variant="secondary" onPress={() => { setEditing(schedule.id); setAmount(String(schedule.amount)); setCategory(schedule.category); setDay(String(schedule.day)); }} disabled={busy} />
        <MetallicGlassButton title="Stop Repeating" variant="danger" onPress={() => Alert.alert("Stop repeating?", "Future payments will stop. Previously recorded expenses remain.", [{ text: "Cancel", style: "cancel" }, { text: "Stop", style: "destructive", onPress: () => { void update(schedule, true); } }])} disabled={busy} />
      </>}
    </MetallicGlassCard>)}
  </View>;
}
