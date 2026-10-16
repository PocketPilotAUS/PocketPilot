import React, { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StatusBar } from "react-native";
import { Alert, Text, TextInput, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { ChevronLeft, ChevronRight, CircleCheck, PiggyBank, Plus, Target, TriangleAlert } from "lucide-react-native";
import BackButton from "../components/BackButton";
import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import CurrencyNotice from "../components/CurrencyNotice";
import ManualSavingsPanel from "../components/ManualSavingsPanel";
import SavingsEntryForm, { SavingsFormKind } from "../components/SavingsEntryForm";
import { useDashboardTheme } from "../components/dashboard/useDashboardTheme";
import { navigationStyles } from "../styles/NavigationStyles";
import { createSavingsStyles } from "../styles/SavingsStyles";
import { ManualSavings, SavingsOverview, loadSavings, confirmSavings } from "../services/savingsService";
import { formatAED, formatPercent, monthName } from "../utils/dashboard";
import { amountDraft, currencyCode, toAED } from "../preferences/currency";

type SavingsForm = { kind: SavingsFormKind; entry?: ManualSavings; goalId?: string; key: number };

// Entries changed locally; totals stay consistent with the server's rules
function withEntries(previous: SavingsOverview, entries: ManualSavings[]): SavingsOverview {
  const manualTotal = Math.round(entries.reduce((sum, entry) => sum + entry.amount, 0) * 100) / 100;
  const monthlyTotal = previous.history.reduce((sum, row) => sum + row.saved, 0);
  return { ...previous, manual_entries: entries, manual_total: manualTotal, total_saved: Math.round((manualTotal + monthlyTotal) * 100) / 100 };
}

export default function SavingsScreen({ apiBaseUrl, onBack, onOpenPlan }: { apiBaseUrl: string; onBack: () => void; onOpenPlan?: (planId?: string) => void }) {
  const { styles: d, palette, mode } = useDashboardTheme();
  const s = createSavingsStyles(palette);
  const [month, setMonth] = useState(() => { const now = new Date(); return new Date(now.getFullYear(), now.getMonth(), 1); });
  const [data, setData] = useState<SavingsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const year = month.getFullYear(), monthNumber = month.getMonth() + 1;
  useEffect(() => {
    let active = true; setLoading(true); setError(""); setData(null);
    loadSavings(apiBaseUrl, year, monthNumber).then(value => {
      if (!active) return; setData(value);
    }).catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiBaseUrl, year, monthNumber, revision]);
  // Goal progress is calculated by the server from assigned entries
  const refreshGoals = () => {
    loadSavings(apiBaseUrl, year, monthNumber).then(value => setData(previous => previous ? { ...previous, goals: value.goals } : previous)).catch(() => undefined);
  };
  const [form, setForm] = useState<SavingsForm | null>(null);
  const openForm = (next: Omit<SavingsForm, "key">) => { if (!busy) setForm({ ...next, key: Date.now() }); };
  // Each entry is counted once: confirmed months, extra savings, or one goal
  const entries = data?.manual_entries ?? [];
  const goalTotal = Math.round(entries.reduce((sum, entry) => sum + (entry.goal_id ? entry.amount : 0), 0) * 100) / 100;
  const extraTotal = Math.round(entries.reduce((sum, entry) => sum + (entry.goal_id ? 0 : entry.amount), 0) * 100) / 100;
  const monthlyTotal = Math.round((data?.history ?? []).reduce((sum, row) => sum + row.saved, 0) * 100) / 100;
  const saved = (entry: ManualSavings, created: boolean) => {
    setForm(null);
    setData(previous => previous && withEntries(previous, [entry, ...previous.manual_entries.filter(item => item.id !== entry.id)]));
    refreshGoals();
    const goal = data?.goals.find(item => item.id === entry.goal_id);
    if (created) Alert.alert("Savings added", goal ? `${formatAED(entry.amount)} added to ${goal.title}.` : `${formatAED(entry.amount)} added to your extra savings.`);
  };
  const confirmed = data?.history.find(row => row.year === year && row.month === monthNumber);
  const debtAmount = data?.debt_payments ?? 0;
  const leftover = data?.income != null && debtAmount != null ? Math.round((data.income - data.spent - debtAmount) * 100) / 100 : null;
  // Calculated savings for the month; the user confirms what they actually saved, up to this
  const calculated = Math.max(0, leftover ?? 0);
  const [review, setReview] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState("");
  const startReview = () => { if (!busy) { setReview(amountDraft(confirmed ? confirmed.saved : calculated)); setReviewError(""); } };
  const save = async (actual: number) => {
    if (busy || !data || data.income == null || !data.can_confirm || debtAmount == null) return;
    setBusy(true); setError("");
    try {
      const row = await confirmSavings(apiBaseUrl, { year, month: monthNumber, expected_debt_payments: debtAmount, expected_income: data.income, expected_spent: data.spent, actual_saved: actual });
      setReview(null);
      setData(previous => previous ? { ...previous, total_saved: Math.round((previous.total_saved - (confirmed?.saved ?? 0) + row.saved) * 100) / 100, history: [...previous.history.filter(item => item.year !== year || item.month !== monthNumber), row].sort((a, b) => b.year - a.year || b.month - a.month) } : previous);
      Alert.alert("Savings confirmed", "The completed month's savings are now included in your total.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not confirm savings."); }
    finally { setBusy(false); }
  };
  const confirm = () => {
    if (review == null) return;
    const actual = toAED(review, confirmed ? confirmed.saved : calculated);
    if (!/^\d+(?:\.\d{1,2})?$/.test(review) || !Number.isFinite(actual) || actual < 0) { setReviewError("Enter the amount you actually saved, with up to two decimal places."); return; }
    if (actual > calculated + 0.005) { setReviewError(`You can confirm up to ${formatAED(calculated)}. Record other money as extra savings.`); return; }
    setReviewError("");
    Alert.alert("Confirm month's savings?", `Add ${formatAED(actual)} to your total savings for ${monthName(monthNumber)} ${year}? Make sure all spending and debt payments for this month are entered.`,
      [{ text: "Cancel", style: "cancel" }, { text: "Confirm", onPress: () => { void save(actual); } }]);
  };
  const now = new Date();
  const nextEnabled = year < now.getFullYear() || month.getMonth() < now.getMonth();
  const currentMonth = year === now.getFullYear() && month.getMonth() === now.getMonth();
  const change = (offset: number) => { if (!busy && !loading) { setReview(null); setMonth(new Date(year, month.getMonth() + offset, 1)); } };
  return <SafeAreaView style={d.screen} edges={["top", "left", "right"]}>
    <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />
    <KeyboardFormScrollView contentContainerStyle={d.content}>
      <View style={[d.header, navigationStyles.header]}><BackButton onPress={onBack} disabled={busy} label="Back to Home" /><View style={d.cardTitleBlock}><Text style={d.eyebrow}>Your finances</Text><Text style={d.title}>Savings</Text></View></View>
      {!!error && <View style={d.errorBanner} accessibilityRole="alert"><TriangleAlert size={16} color={palette.danger} /><Text style={d.errorBannerText}>{error}</Text></View>}
      {loading ? <View style={[d.card, d.loader]}><ActivityIndicator color={palette.accent} /></View> : data && <>
        <View style={d.card}>
          <View style={d.cardHeader}><Text style={d.cardLabel}>Total savings</Text><View style={s.icon}><PiggyBank size={22} color={palette.accent} /></View></View>
          <Text style={[d.heroAmount, d.heroAmountAccent]} adjustsFontSizeToFit numberOfLines={1}>{formatAED(data.total_saved)}</Text>
          <View style={s.breakdown}>
            <View style={s.breakdownRow}><Text style={d.mutedText}>Confirmed monthly savings</Text><Text style={s.breakdownValue}>{formatAED(monthlyTotal)}</Text></View>
            <View style={s.breakdownRow}><Text style={d.mutedText}>Extra savings</Text><Text style={s.breakdownValue}>{formatAED(extraTotal)}</Text></View>
            <View style={s.breakdownRow}><Text style={d.mutedText}>Goal savings</Text><Text style={s.breakdownValue}>{formatAED(goalTotal)}</Text></View>
          </View>
          <View style={s.addActions}>
            <Pressable disabled={busy} onPress={() => openForm({ kind: "general" })} accessibilityRole="button" style={[d.primaryButton, s.addAction, busy && d.buttonDisabled]}><Plus size={16} color={palette.onAccent} strokeWidth={2.6} /><Text style={d.primaryButtonText} numberOfLines={1} adjustsFontSizeToFit>Add extra savings</Text></Pressable>
            <Pressable disabled={busy} onPress={() => openForm({ kind: "goal" })} accessibilityRole="button" style={[d.secondaryButton, s.addAction, busy && d.buttonDisabled]}><Target size={16} color={palette.accent} strokeWidth={2.4} /><Text style={d.secondaryButtonText} numberOfLines={1} adjustsFontSizeToFit>Add to a goal</Text></Pressable>
          </View>
        </View>
        {form && (form.kind === "goal" && !data.goals.length
          ? <View style={[d.card, s.emptyGoals]}>
              <Text style={d.cardLabel}>No savings goals yet</Text>
              <Text style={d.mutedText}>Create a financial plan with a savings goal, then add money to it here.</Text>
              <View style={d.buttonRow}>
                <Pressable onPress={() => setForm(null)} style={d.secondaryButton} accessibilityRole="button"><Text style={d.secondaryButtonText}>Cancel</Text></Pressable>
                {onOpenPlan && <Pressable onPress={() => onOpenPlan()} style={d.primaryButton} accessibilityRole="button"><Text style={d.primaryButtonText}>My Financial Plans</Text></Pressable>}
              </View>
            </View>
          : <SavingsEntryForm key={form.key} apiBaseUrl={apiBaseUrl} kind={form.kind} goals={data.goals} entry={form.entry} goalId={form.goalId} disabled={busy}
              onBusyChange={setBusy} onCancel={() => setForm(null)} onSaved={saved} />)}
        <View style={d.card}>
          <View style={d.cardHeader}>
            <View style={d.cardTitleBlock}><Text style={d.cardLabel}>Potential savings</Text><Text style={d.cardSubtitle}>{currentMonth ? "This month" : "Completed month"}</Text></View>
            <View style={s.monthPicker}>
              <Pressable disabled={busy || year <= 1 && monthNumber <= 1} onPress={() => change(-1)} hitSlop={6} accessibilityRole="button" accessibilityLabel="Previous month" style={[s.monthStep, busy && d.buttonDisabled]}><ChevronLeft size={17} color={palette.text} /></Pressable>
              <Text style={s.monthPickerLabel}>{monthName(monthNumber).slice(0, 3)} {year}</Text>
              <Pressable disabled={busy || !nextEnabled} onPress={() => change(1)} hitSlop={6} accessibilityRole="button" accessibilityLabel="Next month" style={[s.monthStep, (busy || !nextEnabled) && d.buttonDisabled]}><ChevronRight size={17} color={palette.text} /></Pressable>
            </View>
          </View>
          <Text style={[d.heroAmount, leftover != null && leftover < 0 ? d.heroAmountDanger : d.heroAmountAccent]} adjustsFontSizeToFit numberOfLines={1}>{leftover == null ? "Not set" : formatAED(Math.abs(leftover))}</Text>
          {leftover != null && leftover < 0 && <Text style={d.heroHint}>Monthly shortfall</Text>}
          <View style={s.breakdown}>
            <View style={s.breakdownRow}><Text style={d.mutedText}>Monthly income</Text><Text style={s.breakdownValue}>{data.income == null ? "Not set" : formatAED(data.income)}</Text></View>
            <View style={s.breakdownRow}><Text style={d.mutedText}>Recorded spending</Text><Text style={s.breakdownValue}>− {formatAED(data.spent)}</Text></View>
            <View style={s.breakdownRow}><Text style={d.mutedText}>Debt payments</Text><Text style={s.breakdownValue}>− {formatAED(debtAmount)}</Text></View>
          </View>
          <Text style={d.heroHint}>An estimate from recorded income, spending and debt payments. It is not money already saved.</Text>
          <View style={s.confirmArea}>
            {confirmed && review == null && <View style={s.confirmedRow}>
              <CircleCheck size={18} color={palette.accent} />
              <Text style={[s.rowTitle, s.confirmedText]}>Confirmed · {formatAED(confirmed.saved)} added to your total savings</Text>
              <Pressable disabled={busy || !data.can_confirm} onPress={startReview} accessibilityRole="button" style={d.pill}><Text style={d.pillText}>Correct amount</Text></Pressable>
            </View>}
            {!confirmed && review == null && <>
              <Pressable disabled={busy || !data.can_confirm || data.income == null} onPress={startReview} accessibilityRole="button" accessibilityState={{ disabled: busy || !data.can_confirm || data.income == null }} style={[d.primaryButton, s.confirmButton, (busy || !data.can_confirm || data.income == null) && d.buttonDisabled]}><Text style={d.primaryButtonText}>Review & confirm month's savings</Text></Pressable>
              <Text style={[d.mutedText, s.confirmStatus]}>{!data.can_confirm ? "You can confirm this month's savings after the month ends."
                : data.income == null ? "Set income for this month in Spending before confirming savings."
                  : leftover != null && leftover < 0 ? "A shortfall adds no savings to your total."
                    : "Review the amount and confirm what you actually saved."}</Text>
            </>}
            {review != null && <View style={s.reviewBox}>
              <Text style={d.editorLabel}>Amount you actually saved</Text>
              <View style={d.inputRow}><Text style={d.inputPrefix}>{currencyCode()}</Text><TextInput value={review} onChangeText={setReview} editable={!busy} keyboardType="decimal-pad" maxLength={18} style={d.input} accessibilityLabel="Amount you actually saved" /></View>
              <Text style={d.mutedText}>Calculated: {formatAED(calculated)}. Lower it if you saved less.</Text>
              {!!reviewError && <Text style={d.formError} accessibilityRole="alert">{reviewError}</Text>}
              <View style={d.buttonRow}>
                <Pressable disabled={busy} onPress={() => { setReview(null); setReviewError(""); }} style={[d.secondaryButton, busy && d.buttonDisabled]} accessibilityRole="button"><Text style={d.secondaryButtonText}>Cancel</Text></Pressable>
                <Pressable disabled={busy} onPress={confirm} style={[d.primaryButton, busy && d.buttonDisabled]} accessibilityRole="button"><Text style={d.primaryButtonText}>{busy ? "Saving…" : "Confirm"}</Text></Pressable>
              </View>
            </View>}
          </View>
        </View>
        <CurrencyNotice />
        {data.goals.length > 0 && <View style={d.card}>
          <Text style={s.historyTitle}>Savings goals</Text>
          {data.goals.map(goal => {
            const percent = goal.target > 0 ? Math.min(100, goal.saved / goal.target * 100) : 0;
            return <Pressable key={goal.id} disabled={busy} onPress={() => openForm({ kind: "goal", goalId: goal.id })} accessibilityRole="button" accessibilityHint="Add savings to this goal" style={({ pressed }) => [s.goalRow, pressed && s.goalRowPressed]}>
              <View style={s.historyHeading}><Text localize={false} style={s.rowTitle}>{goal.title}</Text><Text style={s.rowValue}>{formatPercent(percent)}</Text></View>
              <View style={d.budgetTrack} accessibilityRole="progressbar" accessibilityLabel={`${goal.title} progress`} accessibilityValue={{ min: 0, max: 100, now: Math.round(percent) }}><View style={[d.budgetFill, { width: `${percent}%` }]} /></View>
              <Text style={d.mutedText}>{formatAED(goal.saved)} of {formatAED(goal.target)} · {formatAED(goal.remaining)} remaining</Text>
              <View style={s.goalActions}>
                <View style={d.pill}><Plus size={13} color={palette.accent} /><Text style={d.pillText}>Add savings</Text></View>
                {onOpenPlan && <Pressable disabled={busy} onPress={() => onOpenPlan(goal.id)} accessibilityRole="button" style={d.pill}><Text style={d.pillText}>View plan</Text></Pressable>}
              </View>
            </Pressable>;
          })}
        </View>}
        <ManualSavingsPanel apiBaseUrl={apiBaseUrl} entries={data.manual_entries} goals={data.goals} disabled={busy} onBusyChange={setBusy}
          onEdit={entry => openForm({ kind: "edit", entry })} onChanged={entries => { setData(previous => previous && withEntries(previous, entries)); refreshGoals(); }} />
        <View style={d.card}>
          <Text style={s.historyTitle}>Monthly savings history</Text>
          {!data.history.length && <Text style={d.mutedText}>No confirmed savings yet.</Text>}
          {data.history.map(row => <Pressable key={row.year + "-" + row.month} disabled={busy} onPress={() => { setReview(null); setMonth(new Date(row.year, row.month - 1, 1)); }} accessibilityRole="button" accessibilityHint="Shows this month in Potential savings" style={s.historyRow}><View style={s.historyHeading}><Text style={s.rowTitle}>{monthName(row.month)} {row.year}</Text><Text style={s.rowValue}>{formatAED(row.saved)}</Text></View><Text style={d.mutedText}>Confirmed savings</Text>{row.leftover < 0 && <Text style={d.formError}>Monthly shortfall: {formatAED(-row.leftover)}</Text>}</Pressable>)}
        </View>
        <Text style={d.mutedText}>This tracks manual savings and confirmed months, not a live bank balance. Later transaction edits do not automatically change confirmed months.</Text>
      </>}
      {!!error && <Pressable disabled={busy || loading} onPress={() => setRevision(value => value + 1)} style={[d.secondaryButton, s.action]}><Text style={d.secondaryButtonText}>Refresh</Text></Pressable>}
    </KeyboardFormScrollView>
  </SafeAreaView>;
}
