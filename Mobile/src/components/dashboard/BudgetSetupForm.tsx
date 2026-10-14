import { amountDraft, toAED, formatDraftMoney, baseMoneyDraft } from "../../preferences/currency";
import React, { useRef, useState } from "react";
import { Pressable } from "react-native";
import { Text, TextInput, View } from "../../preferences/LocalizedNative";
import { Check, Plus, Pencil, Trash2 } from "lucide-react-native";
import CategoryIcon from "../transactions/CategoryIcon";
import { useDashboardTheme } from "./useDashboardTheme";
import { createBudgetSetupStyles } from "../../styles/BudgetSetupStyles";
import { createAddExpenseStyles } from "../../styles/AddExpenseStyles";
import { saveBudgetSetup } from "../../services/budgetService";
import { SessionExpiredError } from "../../services/apiClient";
import { DashboardData, monthName } from "../../utils/dashboard";
import { BudgetCategoryDraft, validateBudgetSetup } from "../../utils/budgetSetup";
import { EXPENSE_CATEGORIES, sanitizeAmount } from "../../utils/addExpense";

type Props = { data: DashboardData; apiBaseUrl: string; onSaved: (data: DashboardData) => void; onCancel: () => void };
export default function BudgetSetupForm({ data, apiBaseUrl, onSaved, onCancel }: Props) {
  const { palette } = useDashboardTheme(); const s = createBudgetSetupStyles(palette);
  const add = createAddExpenseStyles(palette);
  const [income, setIncome] = useState(data.income == null ? "" : amountDraft(data.income));
  const [categories, setCategories] = useState<BudgetCategoryDraft[]>(() => data.ideal_budget?.allocations.map(row => ({ name: row.category, amount: row.target == null ? "" : amountDraft(row.target) })) ?? []);
  const [selected, setSelected] = useState<string | null>(null);
  const [customName, setCustomName] = useState("");
  const [categoryAmount, setCategoryAmount] = useState("");
  const [review, setReview] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const locked = useRef(false);
  const total = categories.reduce((sum, row) => sum + Number(row.amount || 0), 0);
  const left = Number(income || 0) - total;
  const categoryTiles = [...new Map([...EXPENSE_CATEGORIES, ...categories.map(row => row.name)].map(name => [name.toLowerCase(), name])).values()];
  const choose = (name: string) => {
    setError(""); setSelected(name); setCustomName("");
    setCategoryAmount(categories.find(row => row.name.toLowerCase() === name.toLowerCase())?.amount ?? "");
  };
  const chooseCustom = () => { setError(""); setSelected(""); setCustomName(""); setCategoryAmount(""); };
  const addCategory = () => {
    if (selected === null || busy) return;
    const name = selected === "" ? customName.trim() : selected;
    const row = { name, amount: categoryAmount.trim() };
    const problem = validateBudgetSetup("0", [{ ...row, amount: baseMoneyDraft(row.amount) }]);
    if (problem) { setError(problem); return; }
    const existing = categories.findIndex(item => item.name.toLowerCase() === name.toLowerCase());
    if (selected === "" && existing >= 0) { setError("This category is already in your budget. Tap its tile to edit the amount."); return; }
    if (existing < 0 && categories.length >= 50) { setError("Add between 1 and 50 budget categories."); return; }
    setCategories(rows => existing >= 0 ? rows.map((item, i) => i === existing ? { ...item, amount: row.amount } : item) : [...rows, row]);
    setSelected(null); setError("");
  };
  const save = async () => {
    if (locked.current) return;
    const problem = validateBudgetSetup(baseMoneyDraft(income), categories.map(row => ({ ...row, amount: baseMoneyDraft(row.amount) })));
    if (problem) { setError(problem); setReview(false); return; }
    locked.current = true; setBusy(true); setError("");
    try { onSaved(await saveBudgetSetup(apiBaseUrl, data.year, data.month, String(toAED(income, data.income)), categories.map(row => ({ name: row.name.trim(), amount: String(toAED(row.amount, data.ideal_budget?.allocations.find(old => old.category === row.name)?.target)) })))); }
    catch (err) { if (!(err instanceof SessionExpiredError)) setError(err instanceof Error ? err.message : "Could not save your budget. Please try again."); }
    finally { locked.current = false; setBusy(false); }
  };
  return <View style={s.card}>
    <Text style={s.title}>{review ? "Review your budget" : "Set up your budget"}</Text>
    <Text style={s.text}>{monthName(data.month)} {data.year} · AED</Text>
    {!review ? <>
      <Text style={s.text}>Tap a category, enter your usual monthly amount, and add it to your budget. You can also add your own categories.</Text>
      <View style={s.field}><Text style={s.label}>Monthly take-home income</Text><TextInput style={s.input} accessibilityLabel="Monthly take-home income" keyboardType="decimal-pad" value={income} onChangeText={value => setIncome(sanitizeAmount(value))} editable={!busy} placeholder="Enter amount or 0 if none" placeholderTextColor={palette.textMuted} /></View>
      <Text style={s.label}>Choose budget categories</Text>
      <View style={add.grid}>
        {categoryTiles.map(name => {
          const included = categories.some(row => row.name.toLowerCase() === name.toLowerCase());
          return <Pressable key={name} disabled={busy} onPress={() => choose(name)} accessibilityRole="button" accessibilityLabel={name}
            accessibilityState={{ selected: selected === name }} accessibilityHint={included ? "Edit this category amount" : "Set a monthly amount for this category"}
            style={[add.tile, selected === name && add.tileSelected]}>
            <CategoryIcon category={name} /><Text style={[add.tileLabel, selected === name && add.tileLabelSelected]} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={.7}>{name}</Text>
            {included && <View style={s.categoryAdded}><Check size={12} color={palette.accent} /></View>}
          </Pressable>;
        })}
      </View>
      <Pressable style={[s.button, s.secondary, categories.length >= 50 && s.disabled]} disabled={busy || categories.length >= 50} onPress={chooseCustom}><View style={s.customButtonLabel}><Plus size={17} color={palette.text} /><Text style={s.secondaryText}>Add my own category</Text></View></Pressable>
      {selected !== null && <View style={s.category}>
        <View style={s.row}><Text style={s.label}>{selected === "" ? "My custom category" : selected}</Text><Pressable style={s.remove} onPress={() => { setSelected(null); setError(""); }} accessibilityRole="button" accessibilityLabel="Cancel category edit"><Text style={s.text}>Cancel</Text></Pressable></View>
        {selected === "" && <TextInput style={s.input} accessibilityLabel="Category name" value={customName} onChangeText={setCustomName} maxLength={40} editable={!busy} placeholder="Category name" placeholderTextColor={palette.textMuted} />}
        <Text style={s.label}>Usual monthly amount</Text>
        <TextInput style={s.input} accessibilityLabel="Monthly category budget in AED" keyboardType="decimal-pad" value={categoryAmount} onChangeText={value => setCategoryAmount(sanitizeAmount(value))} editable={!busy} placeholder="Enter amount or 0 if none" placeholderTextColor={palette.textMuted} autoFocus />
        <Pressable style={s.button} onPress={addCategory} disabled={busy}><Text style={s.buttonText}>{categories.some(row => row.name.toLowerCase() === selected.toLowerCase()) ? "Update category amount" : "Add to budget"}</Text></Pressable>
      </View>}
      {!!categories.length && <View style={s.categoryList}>
        <Text style={s.label}>Your budget categories</Text>
        {categories.map((row, i) => <View key={row.name} style={s.selectedCategoryRow}>
          <CategoryIcon category={row.name} />
          <Pressable style={s.selectedCategoryDetails} accessibilityRole="button" accessibilityLabel={`Edit ${row.name}`} onPress={() => choose(row.name)}><Text style={s.label}>{row.name}</Text><Text style={s.text}>{formatDraftMoney(Number(row.amount || 0))} / month</Text></Pressable>
          <Pressable style={s.remove} accessibilityRole="button" accessibilityLabel={`Edit ${row.name}`} onPress={() => choose(row.name)}><Pencil size={17} color={palette.textSecondary} /></Pressable>
          <Pressable style={s.remove} accessibilityRole="button" accessibilityLabel={`Remove ${row.name}`} onPress={() => { setCategories(rows => rows.filter((_, index) => index !== i)); if (selected === row.name) setSelected(null); }}><Trash2 size={17} color={palette.danger} /></Pressable>
        </View>)}
      </View>}
      {!!error && <Text style={s.error} accessibilityRole="alert">{error}</Text>}
      <Pressable style={s.button} onPress={() => { if (selected !== null) { setError("Add or update the selected category before reviewing your budget."); return; } const problem = validateBudgetSetup(baseMoneyDraft(income), categories.map(row => ({ ...row, amount: baseMoneyDraft(row.amount) }))); setError(problem ?? ""); if (!problem) setReview(true); }}><Text style={s.buttonText}>Review my budget</Text></Pressable>
    </> : <>
      {categories.map((row, i) => <View key={i} style={s.row}><Text style={s.label}>{row.name}</Text><Text style={s.text}>{formatDraftMoney(Number(row.amount))}</Text></View>)}
      <Text style={s.text}>Monthly income: {formatDraftMoney(Number(income))}</Text>
      <Text style={s.text}>Planned monthly spending: {formatDraftMoney(total)}</Text>
      <Text style={left < 0 ? s.error : s.positive}>{left < 0 ? "Budget exceeds income by" : "Income left after your budget"}: {formatDraftMoney(Math.abs(left))}</Text>
      <Text style={s.text}>Saving creates your budget targets. It does not record paid expenses or money saved.</Text>
      {!!error && <Text style={s.error} accessibilityRole="alert">{error}</Text>}
      <Pressable style={[s.button, busy && s.disabled]} disabled={busy} onPress={() => { void save(); }}><Text style={s.buttonText}>{busy ? "Saving…" : "Save my budget"}</Text></Pressable>
      <Pressable style={[s.button, s.secondary]} disabled={busy} onPress={() => setReview(false)}><Text style={s.secondaryText}>Adjust Details</Text></Pressable>
    </>}
    <Pressable disabled={busy} style={[s.button, s.secondary]} onPress={onCancel}><Text style={s.secondaryText}>Cancel</Text></Pressable>
  </View>;
}
