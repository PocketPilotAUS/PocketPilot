import React, { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StatusBar } from "react-native";
import { Text, View, TextInput, Alert } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { ChevronLeft, ChevronRight, PiggyBank, TriangleAlert } from "lucide-react-native";
import BackButton from "../components/BackButton";
import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import CurrencyNotice from "../components/CurrencyNotice";
import ManualSavingsPanel from "../components/ManualSavingsPanel";
import { useDashboardTheme } from "../components/dashboard/useDashboardTheme";
import { navigationStyles } from "../styles/NavigationStyles";
import { createSavingsStyles } from "../styles/SavingsStyles";
import { SavingsOverview, loadSavings, confirmSavings } from "../services/savingsService";
import { amountDraft, currencyCode, toAED } from "../preferences/currency";
import { formatAED, monthName } from "../utils/dashboard";

export default function SavingsScreen({ apiBaseUrl, onBack }: { apiBaseUrl: string; onBack: () => void }) {
  const { styles: d, palette, mode } = useDashboardTheme();
  const s = createSavingsStyles(palette);
  const [month, setMonth] = useState(() => { const now = new Date(); return new Date(now.getFullYear(), now.getMonth(), 1); });
  const [data, setData] = useState<SavingsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [extraDebt, setExtraDebt] = useState("0");
  const [revision, setRevision] = useState(0);
  const year = month.getFullYear(), monthNumber = month.getMonth() + 1;
  useEffect(() => {
    let active = true; setLoading(true); setError(""); setData(null);
    loadSavings(apiBaseUrl, year, monthNumber).then(value => {
      if (!active) return; setData(value);
      const saved = value.history.find(row => row.year === year && row.month === monthNumber);
      setExtraDebt(saved ? amountDraft(saved.extra_debt_payments) : "0");
    }).catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiBaseUrl, year, monthNumber, revision]);
  const confirmed = data?.history.find(row => row.year === year && row.month === monthNumber);
  const valid = /^\d+(?:\.\d{1,2})?$/.test(extraDebt) && toAED(extraDebt) <= 1_000_000_000;
  const debtAmount = valid ? toAED(extraDebt, confirmed?.extra_debt_payments) : null;
  const leftover = data?.income != null && debtAmount != null ? Math.round((data.income - data.spent - debtAmount) * 100) / 100 : null;
  const save = async () => {
    if (busy || !data || data.income == null || !data.can_confirm || debtAmount == null) return;
    setBusy(true); setError("");
    try {
      const row = await confirmSavings(apiBaseUrl, { year, month: monthNumber, extra_debt_payments: debtAmount, expected_income: data.income, expected_spent: data.spent });
      setData(previous => previous ? { ...previous, total_saved: Math.round((previous.total_saved - (confirmed?.saved ?? 0) + row.saved) * 100) / 100, history: [...previous.history.filter(item => item.year !== year || item.month !== monthNumber), row].sort((a, b) => b.year - a.year || b.month - a.month) } : previous);
      Alert.alert("Savings confirmed", "The completed month's savings are now included in your total.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not confirm savings."); }
    finally { setBusy(false); }
  };
  const confirm = () => Alert.alert("Confirm month's savings?", "Confirm that the leftover was actually saved and all spending and debt payments for this month have been entered.", [{ text: "Cancel", style: "cancel" }, { text: "Confirm", onPress: () => { void save(); } }]);
  const now = new Date();
  const nextEnabled = year < now.getFullYear() || month.getMonth() < now.getMonth();
  const change = (offset: number) => { if (!busy && !loading) setMonth(new Date(year, month.getMonth() + offset, 1)); };
  return <SafeAreaView style={d.screen} edges={["top", "left", "right"]}>
    <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />
    <KeyboardFormScrollView contentContainerStyle={d.content}>
      <View style={[d.header, navigationStyles.header]}><BackButton onPress={onBack} disabled={busy} label="Back to Home" /><View style={d.cardTitleBlock}><Text style={d.eyebrow}>Your finances</Text><Text style={d.title}>Savings</Text></View></View>
      {!!error && <View style={d.errorBanner} accessibilityRole="alert"><TriangleAlert size={16} color={palette.danger} /><Text style={d.errorBannerText}>{error}</Text></View>}
      {loading ? <View style={[d.card, d.loader]}><ActivityIndicator color={palette.accent} /></View> : data && <>
        <View style={d.card}><View style={d.cardHeader}><Text style={d.cardLabel}>Total savings</Text><View style={s.icon}><PiggyBank size={22} color={palette.accent} /></View></View><Text style={[d.heroAmount, d.heroAmountAccent]} adjustsFontSizeToFit numberOfLines={1}>{formatAED(data.total_saved)}</Text><Text style={d.heroHint}>Manual savings plus confirmed completed months.</Text><View style={d.statRow}><View style={d.statTile}><Text style={d.statLabel}>Added manually</Text><Text style={d.statValue} adjustsFontSizeToFit numberOfLines={1}>{formatAED(data.manual_total)}</Text></View><View style={d.statTile}><Text style={d.statLabel}>Confirmed monthly savings</Text><Text style={d.statValue} adjustsFontSizeToFit numberOfLines={1}>{formatAED(data.history.reduce((sum, row) => sum + row.saved, 0))}</Text></View></View></View>
        <CurrencyNotice />
        <ManualSavingsPanel apiBaseUrl={apiBaseUrl} entries={data.manual_entries} disabled={busy} onBusyChange={setBusy} onChanged={entries => setData(previous => {
          if (!previous) return previous;
          const manualTotal = Math.round(entries.reduce((sum, entry) => sum + entry.amount, 0) * 100) / 100;
          const monthlyTotal = previous.history.reduce((sum, row) => sum + row.saved, 0);
          return { ...previous, manual_entries: entries, manual_total: manualTotal, total_saved: Math.round((manualTotal + monthlyTotal) * 100) / 100 };
        })} />
        <View style={d.card}>
          <View style={s.selector}><Pressable disabled={busy || year <= 1 && monthNumber <= 1} onPress={() => change(-1)} accessibilityRole="button" accessibilityLabel="Previous month" style={[s.monthButton, busy && d.buttonDisabled]}><ChevronLeft size={20} color={palette.text} /></Pressable><Text style={s.month}>{monthName(monthNumber)} {year}</Text><Pressable disabled={busy || !nextEnabled} onPress={() => change(1)} accessibilityRole="button" accessibilityLabel="Next month" style={[s.monthButton, (busy || !nextEnabled) && d.buttonDisabled]}><ChevronRight size={20} color={palette.text} /></Pressable></View>
          <Text style={d.heroLabel}>{leftover != null && leftover < 0 ? "Monthly shortfall" : "Estimated savings for this month"}</Text><Text style={[d.heroAmount, leftover != null && leftover < 0 ? d.heroAmountDanger : d.heroAmountAccent]} adjustsFontSizeToFit numberOfLines={1}>{leftover == null ? "Not set" : formatAED(Math.abs(leftover))}</Text>
          <View style={d.statRow}><View style={d.statTile}><Text style={d.statLabel}>Monthly income</Text><Text style={d.statValue} adjustsFontSizeToFit numberOfLines={1}>{data.income == null ? "Not set" : formatAED(data.income)}</Text></View><View style={d.statTile}><Text style={d.statLabel}>Recorded spending</Text><Text style={d.statValue} adjustsFontSizeToFit numberOfLines={1}>{formatAED(data.spent)}</Text></View></View>
          <View style={s.field}><Text style={d.editorLabel}>Debt payments not recorded in spending</Text><View style={d.inputRow}><Text style={d.inputPrefix}>{currencyCode()}</Text><TextInput editable={!busy} value={extraDebt} onChangeText={setExtraDebt} keyboardType="decimal-pad" maxLength={18} style={d.input} accessibilityLabel="Debt payments not recorded in spending" placeholder="0.00" placeholderTextColor={palette.textMuted} /></View><Text style={[d.mutedText, s.note]}>Enter actual payments for this month only. Leave 0 if already recorded in spending. Loan estimates are not deducted automatically.</Text></View>
          {!valid && <Text style={d.formError}>Enter a valid debt payment amount with up to two decimal places.</Text>}
          {data.income == null && <Text style={d.heroHint}>Set income for this month in Spending before confirming savings.</Text>}
          {leftover != null && leftover < 0 && <Text style={d.heroHint}>A shortfall adds no savings to your total.</Text>}
          {!data.can_confirm && <Text style={d.heroHint}>This month is still ongoing. Confirm savings after it ends.</Text>}
          {confirmed && <Text style={d.heroHint}>Previously confirmed: {formatAED(confirmed.saved)}</Text>}
          <Pressable disabled={busy || !data.can_confirm || data.income == null || !valid} onPress={confirm} accessibilityRole="button" style={[d.primaryButton, s.action, (busy || !data.can_confirm || data.income == null || !valid) && d.buttonDisabled]}><Text style={d.primaryButtonText}>{busy ? "Saving…" : confirmed ? "Update confirmed savings" : "Confirm month's savings"}</Text></Pressable>
        </View>
        <View style={d.card}><Text style={s.historyTitle}>Monthly savings history</Text>{!data.history.length && <Text style={d.mutedText}>No confirmed savings yet.</Text>}{data.history.map(row => <Pressable key={row.year + "-" + row.month} disabled={busy} onPress={() => setMonth(new Date(row.year, row.month - 1, 1))} accessibilityRole="button" style={s.historyRow}><View style={s.historyHeading}><Text style={s.rowTitle}>{monthName(row.month)} {row.year}</Text><Text style={s.rowValue}>{formatAED(row.saved)}</Text></View><Text style={d.mutedText}>Confirmed savings</Text>{row.leftover < 0 && <Text style={d.formError}>Monthly shortfall: {formatAED(-row.leftover)}</Text>}</Pressable>)}</View>
        <Text style={d.mutedText}>This tracks manual savings and confirmed months, not a live bank balance. Later transaction edits do not automatically change confirmed months.</Text>
      </>}
      {!!error && <Pressable disabled={busy || loading} onPress={() => setRevision(value => value + 1)} style={[d.secondaryButton, s.action]}><Text style={d.secondaryButtonText}>Refresh</Text></Pressable>}
    </KeyboardFormScrollView>
  </SafeAreaView>;
}
