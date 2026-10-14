import React, { useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView } from "react-native";
import { Alert, Text, TextInput, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import * as DocumentPicker from "expo-document-picker";
import { File, Paths } from "expo-file-system";
import { Check, FileUp, X } from "lucide-react-native";
import { useDashboardTheme } from "../components/dashboard/useDashboardTheme";
import { createStatementImportStyles } from "../styles/StatementImportStyles";
import { formatAED } from "../utils/dashboard";
import { formatPlanningDate } from "../utils/planningDate";
import { Currency, ExchangeRate, getCurrencyPreference } from "../preferences/currency";
import CurrencyNotice from "../components/CurrencyNotice";
import { loadYuanRate } from "../services/currencyService";
import { confirmStatement, previewStatement, StatementPreview, StatementRow } from "../services/statementService";
import { SessionExpiredError } from "../services/apiClient";

type ReviewedRow = StatementRow & { selected: boolean };
type Props = { apiBaseUrl: string; budgetCategories?: string[]; onClose: () => void; onBusyChange: (busy: boolean) => void; onImported: () => void };

export default function StatementImportScreen({ apiBaseUrl, budgetCategories = [], onClose, onBusyChange, onImported }: Props) {
  const { styles, palette } = useDashboardTheme();
  const s = createStatementImportStyles(palette);
  const [currency, setCurrency] = useState<Currency | null>(null);
  const [dateOrder, setDateOrder] = useState<"DMY" | "MDY">("DMY");
  const [amountStyle, setAmountStyle] = useState<"negative_debits" | "positive_debits">("negative_debits");
  const [preview, setPreview] = useState<StatementPreview | null>(null);
  const [rows, setRows] = useState<ReviewedRow[]>([]);
  const [filename, setFilename] = useState("");
  const [statementRate, setStatementRate] = useState<ExchangeRate | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);
  const setWorking = (value: boolean) => { lock.current = value; setBusy(value); onBusyChange(value); };
  const chosen = rows.filter(row => row.selected && row.kind === "expense" && row.direction === "debit");
  const total = chosen.reduce((sum, row) => sum + Number(row.amount_aed), 0);
  const update = (id: number, patch: Partial<ReviewedRow>) => setRows(current => current.map(row => row.row_id === id ? { ...row, ...patch } : row));

  const pick = async () => {
    if (lock.current || !currency) return;
    setWorking(true); setError("");
    let cacheFile: File | undefined;
    try {
      const result = await DocumentPicker.getDocumentAsync({ type: "*/*", copyToCacheDirectory: true, multiple: false });
      if (result.canceled) return;
      const asset = result.assets[0];
      if (Platform.OS !== "web") cacheFile = new File(asset.uri);
      if (!asset.name.toLowerCase().endsWith(".csv")) throw new Error("Choose a CSV statement. PDF and photos are not supported yet.");
      if ((asset.size ?? cacheFile?.size ?? 0) > 128 * 1024) throw new Error("Choose a CSV smaller than 128 KB.");
      const csvText = asset.file ? await asset.file.text() : await cacheFile!.text();
      const cached = getCurrencyPreference().rate;
      const rate = currency === "CNY" ? cached ?? await loadYuanRate(null) : null;
      const data = await previewStatement(apiBaseUrl, { csv_text: csvText, currency, date_order: dateOrder, amount_style: amountStyle, ...(rate ? { aed_to_cny: rate.aedToCny } : {}), categories: budgetCategories });
      setFilename(asset.name); setPreview(data); setStatementRate(rate);
      setRows(data.rows.map(row => ({ ...row, selected: row.kind === "expense" && row.direction === "debit" && !row.possible_duplicate })));
    } catch (err) {
      if (!(err instanceof SessionExpiredError)) setError(err instanceof Error && err.name !== "AbortError" ? err.message : "Reading the statement took too long. Try again; nothing was saved.");
    } finally {
      // Delete only the copied picker cache, never the user's original statement.
      if (cacheFile?.uri.startsWith(Paths.cache.uri)) { try { cacheFile.delete(); } catch {} }
      setWorking(false);
    }
  };
  const save = async () => {
    if (lock.current || !preview || !chosen.length) return;
    if (chosen.some(row => !row.category.trim())) { setError("Choose a category for every selected expense."); return; }
    setWorking(true); setError("");
    try {
      const result = await confirmStatement(apiBaseUrl, preview.preview_token, chosen.map(row => ({ row_id: row.row_id, category: row.category.trim(), include_possible_duplicate: row.possible_duplicate })));
      Alert.alert("Import complete", `${result.added} expenses added. ${result.skipped_duplicates} exact duplicates skipped.`);
      onImported();
    } catch (err) {
      if (!(err instanceof SessionExpiredError)) setError(err instanceof Error && err.name !== "AbortError" ? err.message : "Could not confirm the import. Retry to check the result; exact duplicates will be skipped.");
    } finally { setWorking(false); }
  };
  return <SafeAreaView style={styles.screen} edges={["top", "bottom", "left", "right"]}>
    <View style={[styles.header, s.header]}>
      <View style={styles.headerText}><Text style={styles.eyebrow}>Transactions</Text><Text style={styles.title}>Import statement</Text></View>
      <Pressable disabled={busy} onPress={onClose} style={styles.iconButton} accessibilityRole="button" accessibilityLabel="Close statement import"><X size={22} color={palette.text} /></Pressable>
    </View>
    <KeyboardAvoidingView style={s.flex} behavior={Platform.OS === "ios" ? "padding" : "height"}>
      <ScrollView style={s.flex} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
        {!!error && <Text style={s.warning} accessibilityRole="alert">{error}</Text>}
        {!preview ? <View style={s.card}>
          <Text style={s.title}>Start with a CSV statement</Text>
          <Text style={s.text}>Up to 50 rows and 128 KB. Use Date, Description and Amount columns, or separate Debit and Credit columns. Headers must be on the first row.</Text>
          <Text style={s.title}>Statement currency</Text>
          <Text style={s.text}>Choose the currency actually used by your bank statement.</Text>
          <View style={s.options}>{(["AED", "CNY"] as const).map(code => <Pressable key={code} disabled={busy} onPress={() => setCurrency(code)} accessibilityRole="radio" accessibilityState={{ checked: currency === code }} style={[s.option, currency === code && s.selected]}><Text localize={false} style={s.title}>{code}</Text></Pressable>)}</View>
          <Text style={s.title}>Date format</Text>
          <View style={s.options}>{(["DMY", "MDY"] as const).map(order => <Pressable key={order} disabled={busy} onPress={() => setDateOrder(order)} accessibilityRole="radio" accessibilityState={{ checked: dateOrder === order }} style={[s.option, dateOrder === order && s.selected]}><Text style={s.text}>{order === "DMY" ? "DD/MM/YYYY" : "MM/DD/YYYY"}</Text></Pressable>)}</View>
          <Text style={s.title}>Amount column</Text>
          <View style={s.options}>{(["negative_debits", "positive_debits"] as const).map(style => <Pressable key={style} disabled={busy} onPress={() => setAmountStyle(style)} accessibilityRole="radio" accessibilityState={{ checked: amountStyle === style }} style={[s.option, amountStyle === style && s.selected]}><Text style={s.text}>{style === "negative_debits" ? "Spending is negative" : "Spending is positive"}</Text></Pressable>)}</View>
          <Text style={s.text}>Separate Debit and Credit columns ignore this sign choice. ISO dates such as 2026-10-13 also work.</Text>
          <Text style={s.text}>Your PocketPilot server reads the CSV and asks its configured Ollama model for suggestions. Nothing is saved until you confirm.</Text>
          <Pressable disabled={busy || !currency} onPress={() => { void pick(); }} style={[s.button, (busy || !currency) && s.muted]} accessibilityRole="button" accessibilityLabel="Choose CSV statement"><FileUp size={20} color={palette.onAccent} /><Text style={s.buttonText}>{busy ? "Reading statement…" : "Choose CSV statement"}</Text></Pressable>
        </View> : <>
          <View style={s.card}>
            <Text localize={false} style={s.title}>{filename}</Text>
            <Text style={s.text}>Review every row before importing. This version adds expenses only. Income, credits and transfers are not imported.</Text>
            <Text style={s.text}>Exact matches on date, amount and description are skipped when saving, including repeated imports.</Text>
            {!!statementRate && <CurrencyNotice always rateOverride={statementRate} />}
            {!preview.ai_available && <Text style={s.warning}>AI suggestions are unavailable. Label debit rows manually; nothing has been saved.</Text>}
            {!!preview.errors.length && <Text style={s.warning}>{preview.errors.length} invalid rows were skipped.</Text>}
            {preview.errors.map(item => <Text key={item.row_id} style={s.text}>Row {item.row_id}: {item.message}</Text>)}
            <Pressable disabled={busy} onPress={() => { setPreview(null); setRows([]); setError(""); }} accessibilityRole="button"><Text style={s.title}>Choose another statement</Text></Pressable>
          </View>
          {rows.map(row => <View key={row.row_id} style={s.card}>
            <Text localize={false} style={s.title}>{row.description}</Text>
            <Text style={s.text}>{formatPlanningDate(row.date)} · {formatAED(Number(row.amount_aed))}</Text>
            <Text localize={false} style={s.text}>{`${row.source_currency} ${row.source_amount} · ${row.direction === "debit" ? "Money out" : "Money in"}`}</Text>
            {row.possible_duplicate && <Text style={s.warning}>Possible duplicate. Include only if this is a separate expense.</Text>}
            <Text style={s.text}>{row.kind === "expense" ? "Expense" : row.kind === "income" ? "Income or credit · not imported" : row.kind === "transfer" ? "Transfer · not imported" : "Needs your review"}</Text>
            {row.direction === "debit" && <>
              <View style={s.options}>{(["expense", "transfer", "review"] as const).map(kind => <Pressable key={kind} disabled={busy} accessibilityRole="radio" accessibilityState={{ checked: row.kind === kind }} onPress={() => update(row.row_id, { kind, selected: kind === "expense" && !row.possible_duplicate })} style={[s.option, row.kind === kind && s.selected]}><Text style={s.text}>{kind === "expense" ? "Expense" : kind === "transfer" ? "Transfer" : "Skip"}</Text></Pressable>)}</View>
              {row.kind === "expense" && <>
                <Text style={s.title}>Category</Text>
                <TextInput style={s.input} value={row.category} onChangeText={category => update(row.row_id, { category })} maxLength={40} editable={!busy} accessibilityLabel={`Category for row ${row.row_id}`} />
                <Pressable disabled={busy} accessibilityRole="checkbox" accessibilityState={{ checked: row.selected }} onPress={() => update(row.row_id, { selected: !row.selected })} style={[s.option, row.selected && s.selected]}><Text style={s.title}>{row.selected ? "✓ Selected for import" : "Include this expense"}</Text></Pressable>
              </>}
            </>}
          </View>)}
        </>}
      </ScrollView>
      {preview && <View style={s.footer}>
        <Text style={s.title}>{chosen.length} selected · {formatAED(total)}</Text>
        <Pressable disabled={busy || !chosen.length} onPress={() => { void save(); }} style={[s.button, (busy || !chosen.length) && s.muted]} accessibilityRole="button" accessibilityLabel="Confirm selected expenses">{busy ? <ActivityIndicator color={palette.onAccent} /> : <Check size={20} color={palette.onAccent} />}<Text style={s.buttonText}>{busy ? "Importing…" : "Confirm selected expenses"}</Text></Pressable>
      </View>}
    </KeyboardAvoidingView>
  </SafeAreaView>;
}
