
import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  StatusBar,
  Switch,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import AmbientBackground from "../components/AmbientBackground";
import MetallicGlassCard from "../components/MetallicGlassCard";
import MetallicGlassButton from "../components/MetallicGlassButton";
import { useAppTheme } from "../theme/ThemeContext";
import { createAddTransactionStyles } from "../styles/AddTransactionStyles";
import { apiFetch, SessionExpiredError } from "../services/apiClient";

type Props = {
  onBack: () => void;
  onSaved: () => void;
  apiBaseUrl: string;
};

// Largest amount the backend accepts for one transaction
const MAX_AMOUNT = 1_000_000_000;

const categories = [
  "Rent",
  "Entertainment",
  "Food",
  "Transport",
  "Shopping",
  "Subscriptions",
  "Bills",
  "Other",
];

export default function AddTransactionScreen({
  onBack,
  onSaved,
  apiBaseUrl,
}: Props) {
  const { colors, mode } = useAppTheme();
  const styles = createAddTransactionStyles(colors);

  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("Food");
  const [customCategory, setCustomCategory] = useState("");
  const [description, setDescription] = useState("");
  const [monthly, setMonthly] = useState(false);
  const [paymentDay, setPaymentDay] = useState(String(new Date().getDate()));
  const [requestKey] = useState(() => "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => { const n = Math.floor(Math.random() * 16); return (c === "x" ? n : (n & 3) | 8).toString(16); }));
  const [saving, setSaving] = useState(false);

  const saveTransaction = async () => {
    const numericAmount = Number(amount);

    if (
      !amount.trim() ||
      !Number.isFinite(numericAmount) ||
      numericAmount <= 0
    ) {
      Alert.alert(
        "Invalid amount",
        "Please enter an amount greater than zero."
      );
      return;
    }

    if (numericAmount > MAX_AMOUNT) {
      Alert.alert(
        "Invalid amount",
        "Please enter an amount of up to AED 1,000,000,000."
      );
      return;
    }

    if (category === "Other" && !customCategory.trim()) {
      Alert.alert(
        "Category required",
        "Please enter a name for your custom category."
      );
      return;
    }

    if (monthly && (!/^\d{1,2}$/.test(paymentDay) || Number(paymentDay) < 1 || Number(paymentDay) > 31)) { Alert.alert("Payment day", "Choose a day from 1 to 31."); return; }
    setSaving(true);

    try {
      const today = new Date();

      const localDate = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0"),
      ].join("-");

      // Sent with the login token; the backend links it to this user
      const response = await apiFetch(apiBaseUrl, monthly ? "/recurring/" : "/transactions/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          amount: numericAmount,
          category:
            category === "Other"
              ? customCategory.trim()
              : category,
          description: description.trim() || null,
          ...(monthly ? { day: Number(paymentDay), request_key: requestKey } : { date: localDate }),
        }),
      });

      if (!response.ok) {
        Alert.alert(
          "Error",
          "Could not save the transaction. Please check the details and try again."
        );
        return;
      }

      Alert.alert("Success", "Expense saved successfully!");
      onSaved();
    } catch (error) {
      // An expired session is handled by App, which returns to sign-in
      if (error instanceof SessionExpiredError) return;

      Alert.alert(
        "Connection error",
        "Could not save the transaction. Check that FastAPI is running."
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top", "left", "right"]}>
      <StatusBar
        barStyle={mode === "dark" ? "light-content" : "dark-content"}
      />

      <AmbientBackground />

      <KeyboardFormScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >

        <Text style={styles.title}>Add Transaction</Text>
        <Text style={styles.subtitle}>
          Record a new expense
        </Text>

        <MetallicGlassCard>
          <Text style={styles.label}>Amount (AED)</Text>

          <TextInput
            style={styles.input}
            placeholder="e.g. 45.50"
            placeholderTextColor={colors.textMuted}
            keyboardType="decimal-pad"
            value={amount}
            onChangeText={setAmount}
          />

          <Text style={styles.label}>Category</Text>

          <View style={styles.categories}>
            {categories.map((item) => {
              const selected = category === item;

              return (
                <TouchableOpacity
                  key={item}
                  activeOpacity={0.8}
                  style={[
                    styles.categoryButton,
                    selected && styles.selectedCategory,
                  ]}
                  onPress={() => setCategory(item)}
                >
                  <Text
                    style={[
                      styles.categoryText,
                      selected && styles.selectedCategoryText,
                    ]}
                  >
                    {item}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {category === "Other" && (
            <>
              <Text style={styles.label}>
                What is the category?
              </Text>

              <TextInput
                style={styles.input}
                placeholder="e.g. Entertainment"
                placeholderTextColor={colors.textMuted}
                value={customCategory}
                onChangeText={setCustomCategory}
                autoCapitalize="words"
                maxLength={40}
              />
            </>
          )}

          <Text style={styles.label}>
            Description (optional)
          </Text>

          <TextInput
            style={styles.input}
            placeholder="What did you spend on?"
            placeholderTextColor={colors.textMuted}
            value={description}
            onChangeText={setDescription}
          />
          <Text style={styles.label}>Repeat monthly</Text>
          <Switch accessibilityLabel="Repeat expense monthly" value={monthly} onValueChange={setMonthly} trackColor={{ false: colors.border, true: colors.primary }} thumbColor={colors.surface} />
          {monthly && <>
            <Text style={styles.label}>Monthly payment day (1–31)</Text>
            <TextInput style={styles.input} accessibilityLabel="Monthly payment day" value={paymentDay} onChangeText={setPaymentDay} keyboardType="number-pad" maxLength={2} />
            <Text style={styles.label}>Today's expense is saved now. Monthly repeats start next month and automatically count as spent. Shorter months use their last day.</Text>
          </>}
        </MetallicGlassCard>

        <MetallicGlassButton
          title={saving ? "Saving..." : "Save Transaction"}
          onPress={saveTransaction}
          disabled={saving}
        />
      </KeyboardFormScrollView>
    </SafeAreaView>
  );
}
