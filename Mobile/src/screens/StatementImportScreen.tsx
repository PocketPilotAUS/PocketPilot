import React, { useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView } from "react-native";
import { Alert, Text, TextInput, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import * as DocumentPicker from "expo-document-picker";
import { File, Paths } from "expo-file-system";
import { Check, FileUp, Pencil, TriangleAlert, X } from "lucide-react-native";
import { useTransactionsTheme } from "../components/transactions/useTransactionsTheme";
import CategoryIcon from "../components/transactions/CategoryIcon";
import { dayGroupLabel, formatShortDate } from "../utils/transactions";
import { groupStatementRows, includedStatementRows, needsStatementReview, prepareStatementRow, ReviewedStatementRow } from "../utils/statementReview";
import { createStatementImportStyles } from "../styles/StatementImportStyles";
import { formatAED } from "../utils/dashboard";
import { formatPlanningDate } from "../utils/planningDate";
import { Currency, ExchangeRate, getCurrencyPreference } from "../preferences/currency";
import CurrencyNotice from "../components/CurrencyNotice";
import { loadYuanRate } from "../services/currencyService";
import { confirmStatement, previewStatement, StatementPreview } from "../services/statementService";
import { SessionExpiredError } from "../services/apiClient";

type ReviewedRow = ReviewedStatementRow;
type Props = { apiBaseUrl: string; budgetCategories?: string[]; onClose: () => void; onBusyChange: (busy: boolean) => void; onImported: () => void };

export default function StatementImportScreen({ apiBaseUrl, budgetCategories = [], onClose, onBusyChange, onImported }: Props) {
  const { styles, palette, tx } = useTransactionsTheme();
  const s = createStatementImportStyles(palette);
  const [currency, setCurrency] = useState<Currency | null>(null);
  const [dateOrder, setDateOrder] = useState<"DMY" | "MDY">("DMY");
  const [amountStyle, setAmountStyle] = useState<"negative_debits" | "positive_debits">("negative_debits");
  const [preview, setPreview] = useState<StatementPreview | null>(null);
  const [rows, setRows] = useState<ReviewedRow[]>([]);
  const [editingRow, setEditingRow] = useState<number | null>(null);
  const [filename, setFilename] = useState("");
  const [statementRate, setStatementRate] = useState<ExchangeRate | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);
  const setWorking = (value: boolean) => { lock.current = value; setBusy(value); onBusyChange(value); };
  const chosen = includedStatementRows(rows);
  const reviewRows = rows.filter(needsStatementReview);
  const groups = groupStatementRows(rows.filter(row => !needsStatementReview(row)));
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
      setRows(data.rows.map(prepareStatementRow)); setEditingRow(null);
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
  const finishEdit = (row: ReviewedRow) => {
    if (row.direction === "debit" && row.kind === "expense" && row.selected && !row.category.trim()) { setError("Choose a category for this expense before finishing."); return; }
    update(row.row_id, { reviewed: true }); setEditingRow(null); setError("");
  };
  const renderRow = (row: ReviewedRow, index: number) => {
    const uncertain = needsStatementReview(row);
    const editing = editingRow === row.row_id;
    const included = chosen.some(item => item.row_id === row.row_id);
    return <View key={row.row_id} style={index > 0 ? tx.rowDivider : undefined}>
      <View style={tx.row}>
        <CategoryIcon category={row.kind === "expense" ? row.category || "Other" : "Other"} />
        <View style={tx.rowText}>
          <Text style={tx.rowTitle} numberOfLines={1}>{row.kind === "expense" ? row.category || "Uncategorized" : row.kind === "transfer" ? "Transfer" : row.direction === "credit" ? "Money in" : "Uncategorized"}</Text>
          <Text style={tx.rowSubtitle} numberOfLines={1}>{formatShortDate(row.date)}<Text localize={false}> - {row.description}</Text></Text>
          {uncertain ? <View style={s.reviewLabel}><TriangleAlert size={12} color={palette.danger} /><Text style={s.reviewText}>Needs review</Text></View> : !included && <Text style={tx.rowSubtitle}>Not imported</Text>}
        </View>
        <Text style={tx.rowAmount}>{formatAED(Number(row.amount_aed))}</Text>
        <Pressable disabled={busy} onPress={() => setEditingRow(editing ? null : row.row_id)} style={s.editButton} accessibilityRole="button" accessibilityLabel={`Edit ${row.description}`} accessibilityState={{ expanded: editing }}><Pencil size={15} color={palette.textSecondary} /></Pressable>
      </View>
      {uncertain && !editing && <Text style={s.reviewReason}>{row.issues.join(" ")}</Text>}
      {editing && <View style={s.editor}>
        <Text localize={false} style={s.title}>{row.description}</Text>
        <Text style={s.text}>{formatPlanningDate(row.date)} - {formatAED(Number(row.amount_aed))}</Text>
        <Text localize={false} style={s.text}>{row.source_currency} {row.source_amount} - {row.direction === "debit" ? "Money out" : "Money in"}</Text>
        {uncertain && <Text style={s.warning}>{row.issues.join(" ")}</Text>}
        {row.direction === "debit" ? <>
          <View style={s.options}>{(["expense", "transfer", "review"] as const).map(kind => <Pressable key={kind} disabled={busy} accessibilityRole="radio" accessibilityState={{ checked: row.kind === kind }} onPress={() => update(row.row_id, { kind, selected: kind === "expense" && !row.possible_duplicate })} style={[s.option, row.kind === kind && s.selected]}><Text style={s.text}>{kind === "expense" ? "Expense" : kind === "transfer" ? "Transfer" : "Skip"}</Text></Pressable>)}</View>
          {row.kind === "expense" && <>
            <Text style={s.title}>Category</Text>
            <TextInput style={s.input} value={row.category} onChangeText={category => update(row.row_id, { category })} maxLength={40} editable={!busy} accessibilityLabel={`Category for row ${row.row_id}`} />
            <Pressable disabled={busy} accessibilityRole="checkbox" accessibilityState={{ checked: row.selected }} onPress={() => update(row.row_id, { selected: !row.selected })} style={[s.option, row.selected && s.selected]}><Text style={s.title}>{row.selected ? "Selected for import" : "Include this expense"}</Text></Pressable>
          </>}
        </> : <Text style={s.text}>Incoming money is not imported as spending.</Text>}
        <Pressable disabled={busy} onPress={() => finishEdit(row)} style={s.button} accessibilityRole="button"><Text style={s.buttonText}>Done</Text></Pressable>
      </View>}
    </View>;
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
            <Text style={s.text}>Tap a pencil to edit an entry. Check flagged entries before including them. Nothing is saved until you import.</Text>
            <Text style={s.text}>Income and transfers are excluded. Exact duplicates are skipped when saving.</Text>
            {!!statementRate && <CurrencyNotice always rateOverride={statementRate} />}
            {!preview.ai_available && <Text style={s.warning}>AI suggestions are unavailable. Clear descriptions were categorized automatically; review the flagged entries. Nothing has been saved.</Text>}
            {!!preview.errors.length && <Text style={s.warning}>{preview.errors.length} invalid rows were skipped.</Text>}
            {preview.errors.map(item => <Text key={item.row_id} style={s.text}>Row {item.row_id}: {item.message}</Text>)}
            <Pressable disabled={busy} onPress={() => { setPreview(null); setRows([]); setEditingRow(null); setError(""); }} accessibilityRole="button"><Text style={s.title}>Choose another statement</Text></Pressable>
          </View>
          {!!reviewRows.length && <View>
            <View style={tx.groupHeader}><Text style={tx.groupTitle}>Needs review</Text></View>
            <View style={tx.groupCard}>{reviewRows.map(renderRow)}</View>
          </View>}
          {groups.map(group => <View key={group.date}>
            <View style={tx.groupHeader}><Text style={tx.groupTitle}>{dayGroupLabel(group.date, new Date())}</Text></View>
            <View style={tx.groupCard}>{group.rows.map(renderRow)}</View>
          </View>)}
        </>}
      </ScrollView>
      {preview && <View style={s.footer}>
        <Pressable disabled={busy || !chosen.length} onPress={() => { void save(); }} style={[s.button, (busy || !chosen.length) && s.muted]} accessibilityRole="button" accessibilityLabel={`Import ${chosen.length} transactions`}>{busy ? <ActivityIndicator color={palette.onAccent} /> : <Check size={20} color={palette.onAccent} />}<Text style={s.buttonText}>{busy ? "Importing…" : `Import ${chosen.length} ${chosen.length === 1 ? "transaction" : "transactions"}`}</Text></Pressable>
      </View>}
    </KeyboardAvoidingView>
  </SafeAreaView>;
}
