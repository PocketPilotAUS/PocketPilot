
import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  Alert,
  ActivityIndicator,
  StatusBar,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import AmbientBackground from "../components/AmbientBackground";
import MetallicGlassCard from "../components/MetallicGlassCard";
import MetallicGlassButton from "../components/MetallicGlassButton";
import { useAppTheme } from "../theme/ThemeContext";
import { createTransactionHistoryStyles } from "../styles/TransactionHistoryStyles";

type Transaction = {
  id: number;
  amount: number;
  category: string;
  description: string | null;
  date: string;
};

type Props = {
  apiBaseUrl: string;
  onBack: () => void;
};

export default function TransactionHistoryScreen({
  apiBaseUrl,
  onBack,
}: Props) {
  const { colors, mode } = useAppTheme();
  const styles = createTransactionHistoryStyles(colors);

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/transactions/`);

        if (!response.ok) {
          throw new Error("Failed to fetch transactions");
        }

        const data: Transaction[] = await response.json();

        // Display newest transactions first
        const sorted = [...data].sort(
          (a, b) => b.date.localeCompare(a.date) || b.id - a.id
        );

        setTransactions(sorted);
      } catch {
        setError("Could not load transactions. Check your connection.");
      } finally {
        setLoading(false);
      }
    };

    fetchTransactions();
  }, [apiBaseUrl]);

  const deleteTransaction = (id: number) => {
    Alert.alert(
      "Delete Transaction",
      "Are you sure you want to delete this transaction? This action cannot be undone.",
      [
        {
          text: "Cancel",
          style: "cancel",
        },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            setDeletingId(id);

            try {
              const response = await fetch(
                `${apiBaseUrl}/transactions/${id}`,
                {
                  method: "DELETE",
                }
              );

              if (!response.ok) {
                throw new Error("Failed to delete transaction");
              }

              setTransactions((current) =>
                current.filter((transaction) => transaction.id !== id)
              );
            } catch {
              Alert.alert(
                "Error",
                "Could not delete the transaction. Please try again."
              );
            } finally {
              setDeletingId(null);
            }
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar
        barStyle={mode === "dark" ? "light-content" : "dark-content"}
      />

      <AmbientBackground />

      <ScrollView contentContainerStyle={styles.content}>
        <MetallicGlassButton
          title="← Back to Dashboard"
          variant="secondary"
          onPress={onBack}
          style={styles.backButton}
        />

        <Text style={styles.title}>Transaction History</Text>

        <Text style={styles.subtitle}>
          View your recorded expenses
        </Text>

        {loading ? (
          <ActivityIndicator
            size="large"
            color={colors.primary}
          />
        ) : error ? (
          <MetallicGlassCard>
            <Text style={styles.error}>{error}</Text>
          </MetallicGlassCard>
        ) : transactions.length === 0 ? (
          <MetallicGlassCard>
            <Text style={styles.empty}>
              No transactions yet. Add your first expense!
            </Text>
          </MetallicGlassCard>
        ) : (
          transactions.map((transaction) => (
            <MetallicGlassCard key={transaction.id}>
              <View style={styles.row}>
                <View style={styles.details}>
                  <Text style={styles.category}>
                    {transaction.category}
                  </Text>

                  <Text style={styles.description}>
                    {transaction.description || "No description"}
                  </Text>

                  <Text style={styles.date}>
                    {transaction.date}
                  </Text>
                </View>

                <Text style={styles.amount}>
                  AED {transaction.amount.toFixed(2)}
                </Text>
              </View>

              <View style={styles.deleteButtonContainer}>
                <MetallicGlassButton
                  title={
                    deletingId === transaction.id
                      ? "Deleting..."
                      : "Delete Transaction"
                  }
                  variant="danger"
                  onPress={() => deleteTransaction(transaction.id)}
                  disabled={deletingId !== null}
                  style={styles.deleteButton}
                />
              </View>
            </MetallicGlassCard>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
