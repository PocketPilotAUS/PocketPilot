import React, { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StatusBar, Switch } from "react-native";
import { Text, View, TextInput, Alert } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { CreditCard, Minus, Pencil, Plus, Repeat, Trash2, TriangleAlert } from "lucide-react-native";
import DebtPaymentsPanel from "../components/DebtPaymentsPanel";
import BackButton from "../components/BackButton";
import { navigationStyles } from "../styles/NavigationStyles";
import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import CurrencyNotice from "../components/CurrencyNotice";
import { useDashboardTheme } from "../components/dashboard/useDashboardTheme";
import { createAddExpenseStyles } from "../styles/AddExpenseStyles";
import { sanitizeDay, stepDay } from "../utils/addExpense";
import { createDebtStyles } from "../styles/DebtStyles";
import { amountDraft, currencyCode, toAED } from "../preferences/currency";
import { Debt, loadDebts, removeDebt, saveDebt } from "../services/debtService";
import { formatPlanningDate } from "../utils/planningDate";

const blank = { name: "", balance: "", rate: "", years: "", months: "", original: "", autoDay: "", nextDue: "" };
const money = (n: number) => `AED ${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
export default function DebtScreen({ apiBaseUrl, onBack }: { apiBaseUrl: string; onBack: () => void }) {
  const { styles, palette, mode } = useDashboardTheme();
  const s = createDebtStyles(palette);
  const add = createAddExpenseStyles(palette);
  const [historyDebt, setHistoryDebt] = useState<Pick<Debt, "id" | "name"> | null>(null);
  const [debts, setDebts] = useState<Debt[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<Debt | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [draft, setDraft] = useState(blank);
  const refresh = async () => { setLoading(true); setError(""); try { setDebts(await loadDebts(apiBaseUrl)); setLoadFailed(false); } catch (e) { setLoadFailed(true); setError(e instanceof Error ? e.message : "Could not load debts."); } finally { setLoading(false); } };
  useEffect(() => { let active = true; loadDebts(apiBaseUrl).then(rows => { if (active) { setDebts(rows); setLoadFailed(false); } }).catch(e => { if (active) { setLoadFailed(true); setError(e.message); } }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, [apiBaseUrl]);
  const open = (debt?: Debt) => {
    setEditing(debt || null); setError(""); setFormOpen(true);
    setDraft(debt ? { name: debt.name, balance: amountDraft(debt.balance), rate: String(debt.annual_rate), years: String(Math.floor(debt.remaining_months / 12)), months: String(debt.remaining_months % 12), original: debt.original_principal == null ? "" : amountDraft(debt.original_principal), autoDay: debt.automatic_day == null ? "" : String(debt.automatic_day), nextDue: debt.next_due ?? "" } : blank);
  };
  const save = async () => {
    const decimal = /^\d+(?:\.\d{1,2})?$/;
    const months = Number(draft.years || 0) * 12 + Number(draft.months || 0);
    if (!draft.name.trim() || !decimal.test(draft.balance) || !/^\d+(?:\.\d{1,4})?$/.test(draft.rate) || Number(draft.rate) > 100 || !/^\d*$/.test(draft.years) || !/^\d*$/.test(draft.months) || Number(draft.months || 0) > 11 || months < 1 || months > 600 || (draft.original !== "" && (!decimal.test(draft.original) || Number(draft.original) <= 0))) {
      setError("Enter a debt name, valid amounts, a rate from 0 to 100%, and 1 to 600 remaining months. Extra months must be 0 to 11."); return;
    }
    if (draft.autoDay && (!/^\d{1,2}$/.test(draft.autoDay) || Number(draft.autoDay) < 1 || Number(draft.autoDay) > 31)) {
      setError("Enter a payment day from 1 to 31."); return;
    }
    const day = Number(draft.autoDay);
    const now = new Date(Date.now() + 4 * 60 * 60 * 1000);
    const year = now.getUTCFullYear();
    const month = now.getUTCMonth();
    const nextDate = new Date(Date.UTC(year, month + 1, Math.min(day, new Date(Date.UTC(year, month + 2, 0)).getUTCDate()))).toISOString().slice(0, 10);
    const nextDue = editing?.automatic_day === day && editing.next_due ? editing.next_due : nextDate;
    setBusy(true); setError("");
    try {
      const row = await saveDebt(apiBaseUrl, { name: draft.name.trim(), balance: toAED(draft.balance, editing?.balance), automatic_day: draft.autoDay ? Number(draft.autoDay) : null, next_due: draft.autoDay ? nextDue : null, annual_rate: Number(draft.rate), remaining_months: months, original_principal: draft.original === "" ? null : toAED(draft.original, editing?.original_principal) }, editing?.id);
      setDebts(rows => editing ? rows.map(item => item.id === row.id ? row : item) : [...rows, row]); setFormOpen(false); setEditing(null);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save debt."); } finally { setBusy(false); }
  };
  const deleteDebt = (debt: Debt) => Alert.alert("Delete debt?", "This removes the saved debt, not any recorded transactions.", [{ text: "Cancel", style: "cancel" }, { text: "Delete", style: "destructive", onPress: async () => { setBusy(true); setError(""); try { await removeDebt(apiBaseUrl, debt.id); setDebts(rows => rows.filter(row => row.id !== debt.id)); } catch (e) { setError(e instanceof Error ? e.message : "Could not delete debt."); } finally { setBusy(false); } } }]);
  const inputField = (key: keyof typeof blank, label: string, options: { money?: boolean; suffix?: string; hint?: string; text?: boolean } = {}) => <View style={s.field}>
    <Text style={[styles.editorLabel, (key === "years" || key === "months") && s.termLabel]}>{label}</Text>
    {options.text ? <TextInput value={draft[key]} editable={!busy} maxLength={80} accessibilityLabel={label} style={s.fieldInput} placeholder="Debt name" placeholderTextColor={palette.textMuted} onChangeText={value => setDraft(previous => ({ ...previous, [key]: value }))} /> : <View style={styles.inputRow}>
      {options.money && <Text style={styles.inputPrefix}>{currencyCode()}</Text>}
      <TextInput value={draft[key]} editable={!busy} maxLength={18} keyboardType="decimal-pad" accessibilityLabel={label} style={styles.input} placeholder={options.money ? "0.00" : "0"} placeholderTextColor={palette.textMuted} onChangeText={value => setDraft(previous => ({ ...previous, [key]: value }))} />
      {options.suffix && <Text style={styles.inputPrefix}>{options.suffix}</Text>}
    </View>}
    {options.hint && <Text style={s.hint}>{options.hint}</Text>}
  </View>;
  return <SafeAreaView style={styles.screen} edges={["top", "left", "right"]}>
    <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />
    <KeyboardFormScrollView key={historyDebt?.id ?? "debts"} contentContainerStyle={styles.content}>
      <View style={[styles.header, navigationStyles.header]}><BackButton disabled={busy} onPress={() => historyDebt ? setHistoryDebt(null) : onBack()} label={historyDebt ? "Back to Debt" : "Back to Home"} /><View style={styles.headerText}><Text style={styles.eyebrow}>Your finances</Text><Text style={styles.title}>{historyDebt ? "Debt payments" : "Debt"}</Text></View></View>
      <DebtPaymentsPanel apiBaseUrl={apiBaseUrl} debts={debts} busy={busy} onBusyChange={setBusy} onChanged={() => { void refresh(); }} historyDebt={historyDebt} onHistory={setHistoryDebt} renderDebts={renderPaymentActions => <>
      {!!error && !formOpen && <View style={styles.errorBanner} accessibilityRole="alert"><TriangleAlert size={16} color={palette.danger} /><Text style={styles.errorBannerText}>{error}</Text></View>}
      {loading ? <View style={[styles.card, styles.loader]}><ActivityIndicator color={palette.accent} /></View> : !loadFailed && <>
        <View style={styles.card}>
          <View style={styles.cardHeader}><View style={styles.cardTitleBlock}><Text style={styles.cardLabel}>Debt overview</Text><Text style={styles.cardSubtitle}>Your outstanding balances</Text></View><View style={s.icon}><CreditCard size={21} color={palette.accent} /></View></View>
          <Text style={styles.heroLabel}>Estimated total left to pay</Text>
          <Text style={styles.heroAmount} adjustsFontSizeToFit numberOfLines={1}>{money(debts.reduce((total, d) => total + d.total_left_to_pay, 0))}</Text>
          <View style={styles.statRow}>
            <View style={styles.statTile}><Text style={styles.statLabel}>{debts.some(d => d.repayment_plan) ? "Monthly repayment targets" : "Estimated monthly payments"}</Text><Text style={styles.statValue} adjustsFontSizeToFit numberOfLines={1}>{money(debts.reduce((total, d) => total + (d.repayment_plan?.monthly_payment ?? d.estimated_monthly_payment), 0))}</Text></View>
            <View style={{ flex: 1 }} />
          </View>
        </View>
        <CurrencyNotice />
        <View style={s.sectionHeader}><Text style={s.sectionTitle}>Your debts</Text>{!formOpen && <Pressable disabled={busy} onPress={() => open()} accessibilityRole="button" accessibilityLabel="Add debt" style={({ pressed }) => [styles.compactAddButton, busy && styles.buttonDisabled, pressed && styles.buttonDisabled]}><Plus size={16} color={palette.onAccent} strokeWidth={2.6} /><Text style={styles.compactAddButtonText}>Add debt</Text></Pressable>}</View>
        {formOpen && <View style={styles.card}>
          <Text style={s.formTitle}>{editing ? "Edit debt" : "Add debt"}</Text><Text style={styles.cardSubtitle}>Enter the principal still owed, excluding future interest.</Text>
          {inputField("name", "Debt name", { text: true })}
          {inputField("balance", "Current outstanding principal", { money: true })}
          {inputField("rate", "Annual interest rate (%)", { suffix: "%" })}
          <View style={s.termRow}><View style={s.termField}>{inputField("years", "Years remaining")}</View><View style={s.termField}>{inputField("months", "Extra months remaining (0–11)")}</View></View>
          {inputField("original", "Original amount borrowed (optional)", { money: true })}
          <View style={[styles.card, s.field]}>
            <View style={add.repeatRow}>
              <View style={add.repeatIcon}><Repeat size={18} color={palette.accent} strokeWidth={2.2} /></View>
              <View style={add.repeatText}><Text style={add.repeatTitle}>Repeat monthly</Text><Text style={add.repeatSubtitle}>Record this debt payment every month</Text></View>
              <Switch value={!!draft.autoDay} onValueChange={enabled => setDraft(previous => ({ ...previous, autoDay: enabled ? String(new Date(Date.now() + 4 * 60 * 60 * 1000).getUTCDate()) : "" }))} disabled={busy} trackColor={{ false: palette.track, true: palette.accent }} thumbColor="#FFFFFF" ios_backgroundColor={palette.track} accessibilityLabel="Repeat debt payment monthly" />
            </View>
            {!!draft.autoDay && <View style={add.repeatDetails}>
              <View style={add.dayRow}>
                <Text style={add.dayLabel}>Payment day each month</Text>
                <View style={add.stepper}>
                  <Pressable onPress={() => setDraft(previous => ({ ...previous, autoDay: stepDay(previous.autoDay, -1) }))} disabled={busy} style={add.stepButton} accessibilityRole="button" accessibilityLabel="Earlier payment day"><Minus size={16} color={palette.text} strokeWidth={2.4} /></Pressable>
                  <TextInput value={draft.autoDay} onChangeText={value => setDraft(previous => ({ ...previous, autoDay: sanitizeDay(value) }))} keyboardType="number-pad" maxLength={2} editable={!busy} style={add.dayInput} accessibilityLabel="Monthly debt payment day" />
                  <Pressable onPress={() => setDraft(previous => ({ ...previous, autoDay: stepDay(previous.autoDay, 1) }))} disabled={busy} style={add.stepButton} accessibilityRole="button" accessibilityLabel="Later payment day"><Plus size={16} color={palette.text} strokeWidth={2.4} /></Pressable>
                </View>
              </View>
              <Text style={add.repeatNote}>{editing?.automatic_day === Number(draft.autoDay) && editing.next_due ? `Next payment: ${editing.next_due}.` : "Monthly payments start next month."} Payments automatically count as spent and reduce this debt. Shorter months use their last day. No bank transfer is made.</Text>
            </View>}
          </View>
          <Text style={s.hint}>Changing the loan amount, interest rate or remaining term resets the estimated total to those new figures. Existing payment history is kept.</Text>
          {!!error && <Text style={styles.formError} accessibilityRole="alert">{error}</Text>}
          <View style={styles.buttonRow}>
            <Pressable disabled={busy} onPress={() => { setFormOpen(false); setError(""); }} accessibilityRole="button" style={[styles.secondaryButton, busy && styles.buttonDisabled]}><Text style={styles.secondaryButtonText}>Cancel</Text></Pressable>
            <Pressable disabled={busy} onPress={() => { void save(); }} accessibilityRole="button" style={[styles.primaryButton, busy && styles.buttonDisabled]}><Text style={styles.primaryButtonText}>{busy ? "Saving…" : "Save debt"}</Text></Pressable>
          </View>
        </View>}
        {!debts.length && !formOpen && <View style={styles.card}><View style={s.empty}><View style={s.icon}><CreditCard size={22} color={palette.accent} /></View><Text style={s.emptyText}>No debts yet. Add a debt to see your total and payment estimates.</Text></View></View>}
        {debts.filter(debt => !formOpen || debt.id !== editing?.id).map(debt => <View key={debt.id} style={styles.card}>
          <View style={styles.cardHeader}><View style={s.titleRow}><View style={s.icon}><CreditCard size={20} color={palette.accent} /></View><View style={styles.cardTitleBlock}><Text localize={false} style={s.debtName}>{debt.name}</Text><Text style={styles.cardSubtitle}>{`${debt.annual_rate}% · ${Math.floor(debt.remaining_months / 12)} years · ${debt.remaining_months % 12} months`}</Text></View></View></View>
          <Text style={styles.heroLabel}>Estimated total left to pay</Text><Text style={styles.heroAmount} adjustsFontSizeToFit numberOfLines={1}>{money(debt.total_left_to_pay)}</Text>
          <View style={styles.statRow}><View style={styles.statTile}><Text style={styles.statLabel}>Estimated monthly payment</Text><Text style={styles.statValue} adjustsFontSizeToFit numberOfLines={1}>{money(debt.estimated_monthly_payment)}</Text></View><View style={{ flex: 1 }} /></View>
          {debt.repayment_plan && <View style={s.field}>
            <Text style={styles.statLabel}>Monthly repayment target</Text>
            <Text style={styles.statValue}>{money(debt.repayment_plan.monthly_payment)}</Text>
            <Text style={styles.mutedText}>{money(debt.estimated_monthly_payment)} regular + {money(debt.repayment_plan.extra_payment)} planned extra</Text>
            <Text style={styles.mutedText}>Target payoff: {formatPlanningDate(debt.repayment_plan.deadline)}</Text>
          </View>}
          {!formOpen && renderPaymentActions(debt)}
          <View style={s.actions}>
            <Pressable disabled={busy} onPress={() => open(debt)} accessibilityRole="button" accessibilityLabel="Edit debt" style={({ pressed }) => [s.editButton, busy && styles.buttonDisabled, pressed && s.pressed]}><Pencil size={15} color={palette.textSecondary} /><Text style={s.editText}>Edit debt</Text></Pressable>
            <Pressable disabled={busy} onPress={() => deleteDebt(debt)} accessibilityRole="button" accessibilityLabel="Delete debt" style={({ pressed }) => [s.deleteButton, busy && styles.buttonDisabled, pressed && s.pressed]}><Trash2 size={17} color={palette.danger} /></Pressable>
          </View>
        </View>)}
        <Text style={[styles.mutedText, s.note]}>Estimates assume fixed interest and equal monthly payments. Fees are excluded. Update balances manually from your lender statement.</Text>
      </>}
      {loadFailed && !busy && <Pressable onPress={() => { void refresh(); }} accessibilityRole="button" style={[styles.primaryButton, s.retry]}><Text style={styles.primaryButtonText}>Retry</Text></Pressable>}
      </>} />
    </KeyboardFormScrollView>
  </SafeAreaView>;
}
