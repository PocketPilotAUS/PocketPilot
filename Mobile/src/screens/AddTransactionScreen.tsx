import { toAED } from "../preferences/currency";
import React, { useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StatusBar, Switch } from "react-native";
import { Alert, Text, TextInput, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { CalendarDays, Check, Minus, NotebookPen, Plus, Repeat, Tag, X } from "lucide-react-native";

import CategoryIcon from "../components/transactions/CategoryIcon";
import { useDashboardTheme } from "../components/dashboard/useDashboardTheme";
import { apiFetch, SessionExpiredError } from "../services/apiClient";
import { createAddExpenseStyles } from "../styles/AddExpenseStyles";
import {
  CATEGORY_MAX_LENGTH,
  DESCRIPTION_MAX_LENGTH,
  EXPENSE_CATEGORIES,
  buildExpenseRequest,
  newRequestKey,
  sanitizeAmount,
  sanitizeDay,
  stepDay,
  validateExpense,
} from "../utils/addExpense";
import { formatShortDate, toISODate } from "../utils/transactions";

type Props = {
  onBack: () => void;
  onSaved: () => void;
  apiBaseUrl: string;
  budgetCategories?: string[];
  onBusyChange?: (busy: boolean) => void;
};

export default function AddTransactionScreen({ onBack, onSaved, apiBaseUrl, budgetCategories = [], onBusyChange }: Props) {
  const { styles, palette, mode } = useDashboardTheme();
  const add = createAddExpenseStyles(palette);
  const expenseCategories = [...new Map([...budgetCategories, ...EXPENSE_CATEGORIES].map(name => [name.toLowerCase(), name])).values()];

  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("Food");
  const [customCategory, setCustomCategory] = useState("");
  const [description, setDescription] = useState("");
  const [monthly, setMonthly] = useState(false);
  const [paymentDay, setPaymentDay] = useState(String(new Date().getDate()));
  // One key per visit, so retrying a monthly save never creates a duplicate
  const [requestKey] = useState(newRequestKey);
  const [saving, setSaving] = useState(false);

  const scroll = useRef<ScrollView>(null);
  const content = useRef<View>(null);

  // Scrolls a focused field into view above the keyboard and Save button
  const reveal = (input: TextInput | null) => {
    setTimeout(() => {
      if (!input || !content.current) return;
      input.measureLayout(content.current, (_x, y) => {
        scroll.current?.scrollTo({ y: Math.max(0, y - 100), animated: true });
      });
    }, 250);
  };

  const saveTransaction = async () => {
    if (saving) return;

    const form = { amount: String(toAED(amount)), category, customCategory, description, monthly, paymentDay };
    const problem = validateExpense(form);

    if (problem) {
      Alert.alert(problem.title, problem.message);
      return;
    }

    setSaving(true);
    onBusyChange?.(true);

    try {
      const { path, body } = buildExpenseRequest(form, new Date(), requestKey);

      // Sent with the login token; the backend links it to this user
      const response = await apiFetch(apiBaseUrl, path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        Alert.alert("Error", "Could not save the transaction. Please check the details and try again.");
        return;
      }

      Alert.alert("Success", "Expense saved successfully!");
      onSaved();
    } catch (error) {
      // An expired session is handled by App, which returns to sign-in
      if (error instanceof SessionExpiredError) return;

      Alert.alert("Connection error", "Could not save the transaction. Check that FastAPI is running.");
    } finally {
      setSaving(false);
      onBusyChange?.(false);
    }
  };

  const today = new Date();
  const todayLabel = formatShortDate(toISODate(today), today);

  // The amount field grows with its text (and the font shrinks for long
  // amounts), so "AED" stays next to the number and nothing is clipped
  const shown = amount || "0.00";
  const amountFontSize = shown.length > 10 ? 30 : shown.length > 7 ? 38 : 46;
  const amountWidth = Math.ceil(shown.length * amountFontSize * 0.62) + 12;

  return (
    <SafeAreaView style={styles.screen} edges={["top", "bottom", "left", "right"]}>
      <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />

      <KeyboardAvoidingView style={add.flex} behavior={Platform.OS === "ios" ? "padding" : "height"}>
        <ScrollView
          ref={scroll}
          style={add.flex}
          contentContainerStyle={add.content}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"}
        >
          <View ref={content}>
            <View style={styles.header}>
              <View style={styles.headerText}>
                <Text style={styles.eyebrow}>New expense</Text>
                <Text style={styles.title}>Add expense</Text>
              </View>

              <Pressable onPress={onBack} disabled={saving} style={styles.iconButton} accessibilityRole="button" accessibilityLabel="Cancel adding transaction" accessibilityState={{ disabled: saving }}>
                <X size={21} color={palette.text} />
              </Pressable>
            </View>

            {/* Expenses are always recorded with today's date */}
            <View style={add.dateRow}>
              <View style={add.dateChip} accessible accessibilityLabel={`Date: today, ${todayLabel}`}>
                <CalendarDays size={14} color={palette.textSecondary} strokeWidth={2.2} />
                <Text style={add.dateChipText}>Today · {todayLabel}</Text>
              </View>
            </View>

            {/* Amount */}
            <View style={[styles.card, add.amountCard]}>
              <Text style={styles.cardLabel}>Amount</Text>
              <View style={add.amountRow}>
                <Text style={add.currency}>AED</Text>
                <TextInput
                  value={amount}
                  onChangeText={(value) => setAmount(sanitizeAmount(value))}
                  placeholder="0.00"
                  placeholderTextColor={palette.textMuted}
                  keyboardType="decimal-pad"
                  style={[add.amountInput, { fontSize: amountFontSize, width: amountWidth }]}
                  maxLength={13}
                  editable={!saving}
                  accessibilityLabel="Amount in AED"
                />
              </View>
              <Text style={add.amountHint}>Up to AED 1,000,000,000</Text>
            </View>

            {/* Category */}
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Text style={styles.cardLabel}>Category</Text>
              </View>

              <View style={add.grid} accessibilityRole="radiogroup">
                {expenseCategories.map((item) => {
                  const selected = category === item;

                  return (
                    <Pressable
                      key={item}
                      onPress={() => { setCategory(item); if (item === "Other" && budgetCategories.includes("Other")) setCustomCategory("Other"); }}
                      disabled={saving}
                      style={({ pressed }) => [add.tile, selected && add.tileSelected, pressed && styles.buttonDisabled]}
                      accessibilityRole="radio"
                      accessibilityState={{ selected }}
                      accessibilityLabel={item}
                    >
                      <CategoryIcon category={item} />
                      <Text
                        style={[add.tileLabel, selected && add.tileLabelSelected]}
                        numberOfLines={1}
                        adjustsFontSizeToFit
                        minimumFontScale={0.7}
                      >
                        {item}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>

              {category === "Other" && (
                <View style={add.customField}>
                  <Text style={styles.editorLabel}>Category name</Text>
                  <View style={styles.inputRow}>
                    <Tag size={16} color={palette.textMuted} strokeWidth={2.2} />
                    <TextInput
                      value={customCategory}
                      onChangeText={setCustomCategory}
                      placeholder="e.g. Gym"
                      placeholderTextColor={palette.textMuted}
                      autoCapitalize="words"
                      maxLength={CATEGORY_MAX_LENGTH}
                      editable={!saving}
                      style={add.fieldInput}
                      onFocus={(event) => reveal(event.currentTarget as unknown as TextInput)}
                      accessibilityLabel="Custom category name"
                    />
                  </View>
                </View>
              )}
            </View>

            {/* Description */}
            <View style={add.fieldRow}>
              <NotebookPen size={17} color={palette.textMuted} strokeWidth={2.2} />
              <TextInput
                value={description}
                onChangeText={setDescription}
                placeholder="Description (optional)"
                placeholderTextColor={palette.textMuted}
                maxLength={DESCRIPTION_MAX_LENGTH}
                editable={!saving}
                style={add.fieldInput}
                onFocus={(event) => reveal(event.currentTarget as unknown as TextInput)}
                returnKeyType="done"
                accessibilityLabel="Description"
              />
            </View>

            {/* Repeat monthly (Karim's recurring expenses) */}
            <View style={styles.card}>
              <View style={add.repeatRow}>
                <View style={add.repeatIcon}>
                  <Repeat size={18} color={palette.accent} strokeWidth={2.2} />
                </View>
                <View style={add.repeatText}>
                  <Text style={add.repeatTitle}>Repeat monthly</Text>
                  <Text style={add.repeatSubtitle}>Record this expense every month</Text>
                </View>
                <Switch
                  value={monthly}
                  onValueChange={setMonthly}
                  disabled={saving}
                  trackColor={{ false: palette.track, true: palette.accent }}
                  thumbColor="#FFFFFF"
                  ios_backgroundColor={palette.track}
                  accessibilityLabel="Repeat expense monthly"
                />
              </View>

              {monthly && (
                <View style={add.repeatDetails}>
                  <View style={add.dayRow}>
                    <Text style={add.dayLabel}>Payment day each month</Text>
                    <View style={add.stepper}>
                      <Pressable
                        onPress={() => setPaymentDay((day) => stepDay(day, -1))}
                        disabled={saving}
                        style={add.stepButton}
                        accessibilityRole="button"
                        accessibilityLabel="Earlier payment day"
                      >
                        <Minus size={16} color={palette.text} strokeWidth={2.4} />
                      </Pressable>
                      <TextInput
                        value={paymentDay}
                        onChangeText={(value) => setPaymentDay(sanitizeDay(value))}
                        keyboardType="number-pad"
                        maxLength={2}
                        editable={!saving}
                        style={add.dayInput}
                        onFocus={(event) => reveal(event.currentTarget as unknown as TextInput)}
                        accessibilityLabel="Monthly payment day"
                      />
                      <Pressable
                        onPress={() => setPaymentDay((day) => stepDay(day, 1))}
                        disabled={saving}
                        style={add.stepButton}
                        accessibilityRole="button"
                        accessibilityLabel="Later payment day"
                      >
                        <Plus size={16} color={palette.text} strokeWidth={2.4} />
                      </Pressable>
                    </View>
                  </View>

                  <Text style={add.repeatNote}>
                    Today’s expense is saved now. Monthly repeats start next month and automatically
                    count as spent. Shorter months use their last day.
                  </Text>
                </View>
              )}
            </View>
          </View>
        </ScrollView>

        {/* Always visible: above the keyboard while typing, above the tab bar otherwise */}
        <View style={add.footer}>
          <Pressable
            onPress={() => { void saveTransaction(); }}
            disabled={saving}
            style={({ pressed }) => [add.saveButton, (pressed || saving) && styles.buttonDisabled]}
            accessibilityRole="button"
            accessibilityLabel={monthly ? "Save monthly expense" : "Save transaction"}
          >
            {saving ? (
              <ActivityIndicator color={palette.onAccent} />
            ) : (
              <Check size={19} color={palette.onAccent} strokeWidth={2.6} />
            )}
            <Text style={add.saveText}>{saving ? "Saving…" : "Save Transaction"}</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
