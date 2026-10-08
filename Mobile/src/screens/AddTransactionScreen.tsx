
import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  StatusBar,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import AmbientBackground from "../components/AmbientBackground";
import MetallicGlassCard from "../components/MetallicGlassCard";
import MetallicGlassButton from "../components/MetallicGlassButton";
import { useAppTheme } from "../theme/ThemeContext";
import { createAddTransactionStyles } from "../styles/AddTransactionStyles";

type Props = {
  onBack: () => void;
  onSaved: () => void;
  apiBaseUrl: string;
};

const categories = [
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

    if (category === "Other" && !customCategory.trim()) {
      Alert.alert(
        "Category required",
        "Please enter a name for your custom category."
      );
      return;
    }

    setSaving(true);

    try {
      const today = new Date();

      const localDate = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0"),
      ].join("-");

      const response = await fetch(`${apiBaseUrl}/transactions/`, {
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
          date: localDate,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to save transaction");
      }

      Alert.alert("Success", "Transaction saved successfully!");
      onSaved();
    } catch {
      Alert.alert(
        "Connection error",
        "Could not save the transaction. Check that FastAPI is running."
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar
        barStyle={mode === "dark" ? "light-content" : "dark-content"}
      />

      <AmbientBackground />

      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <MetallicGlassButton
          title="← Back"
          variant="secondary"
          onPress={onBack}
          style={styles.backButton}
        />

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
        </MetallicGlassCard>

        <MetallicGlassButton
          title={saving ? "Saving..." : "Save Transaction"}
          onPress={saveTransaction}
          disabled={saving}
        />
      </ScrollView>
    </SafeAreaView>
  );
}
