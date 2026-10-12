import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, RefreshControl, StatusBar } from "react-native";
import { Alert, Text, TextInput, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { Inbox, Plus, RefreshCw, Search, SearchX, TriangleAlert, X } from "lucide-react-native";

import RecurringExpenses from "../components/RecurringExpenses";
import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import TransactionDetail from "../components/transactions/TransactionDetail";
import TransactionFilters from "../components/transactions/TransactionFilters";
import TransactionRow from "../components/transactions/TransactionRow";
import { useTransactionsTheme } from "../components/transactions/useTransactionsTheme";
import { apiFetch, SessionExpiredError } from "../services/apiClient";
import { formatAED } from "../utils/dashboard";
import {
  DEFAULT_FILTERS,
  Filters,
  Transaction,
  activeFilterCount,
  applyFilters,
  categoriesOf,
  groupTransactions,
  summarize,
} from "../utils/transactions";

type Props = {
  apiBaseUrl: string;
  refreshKey?: number;
  onAddExpense?: () => void;
};

export default function TransactionHistoryScreen({ apiBaseUrl, onAddExpense, refreshKey = 0 }: Props) {
  const { styles, tx, palette, mode } = useTransactionsTheme();

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [selected, setSelected] = useState<Transaction | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    // Keep newly saved expenses visible even after a filtered search.
    setFilters(DEFAULT_FILTERS);
    setSelected(null);
  }, [refreshKey]);

  useEffect(() => {
    let active = true;

    const load = async () => {
      setError("");

      try {
        // Returns only the logged-in user's transactions
        const response = await apiFetch(apiBaseUrl, "/transactions/");

        if (!response.ok) throw new Error("Failed to fetch transactions");

        const data: Transaction[] = await response.json();

        if (active) {
          setTransactions(data);
          setLoaded(true);
        }
      } catch (err) {
        // An expired session is handled by App, which returns to sign-in
        if (!active || err instanceof SessionExpiredError) return;

        setError("Could not load your transactions. Check your connection and try again.");
      } finally {
        if (active) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    };

    void load();

    return () => {
      active = false;
    };
  }, [apiBaseUrl, reload, refreshKey]);

  const refresh = useCallback(() => {
    setRefreshing(true);
    setReload((value) => value + 1);
  }, []);

  const retry = () => {
    setLoading(true);
    setReload((value) => value + 1);
  };

  const today = new Date();

  // Search, filters, sorting, totals and groups all come from one list,
  // so they always agree with each other
  const filtered = useMemo(
    () => applyFilters(transactions, filters, new Date()),
    [transactions, filters]
  );
  const summary = summarize(filtered);
  const groups = groupTransactions(filtered, filters.sort, today);
  const categories = useMemo(() => categoriesOf(transactions), [transactions]);

  const deleteTransaction = async (transaction: Transaction) => {
    setDeletingId(transaction.id);

    try {
      const response = await apiFetch(apiBaseUrl, `/transactions/${transaction.id}`, {
        method: "DELETE",
      });

      // 404: already deleted (e.g. on another device), so it is
      // removed from the list like a successful delete
      if (!response.ok && response.status !== 404) {
        throw new Error("Failed to delete transaction");
      }

      setTransactions((current) => current.filter((item) => item.id !== transaction.id));
      setSelected(null);
    } catch (err) {
      if (err instanceof SessionExpiredError) return;

      Alert.alert("Error", "Could not delete the transaction. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  const summaryCaption = (() => {
    const parts = [];
    if (filters.search.trim()) parts.push(`matching “${filters.search.trim()}”`);
    if (activeFilterCount(filters) > 0) parts.push("with filters applied");
    return parts.length ? `Showing transactions ${parts.join(" ")}` : "All recorded transactions";
  })();

  const renderSkeleton = () => (
    <View style={tx.groupCard}>
      {[0, 1, 2, 3, 4].map((index) => (
        <View key={index} style={[tx.skeletonRow, index > 0 && tx.rowDivider]}>
          <View style={tx.skeletonIcon} />
          <View style={tx.skeletonLines}>
            <View style={[tx.skeletonLine, tx.skeletonLineShort]} />
            <View style={[tx.skeletonLine, tx.skeletonLineLong]} />
          </View>
          <View style={tx.skeletonAmount} />
        </View>
      ))}
    </View>
  );

  const renderState = (
    Icon: typeof Inbox,
    title: string,
    message: string,
    action?: { label: string; Icon: typeof Inbox; onPress: () => void; primary?: boolean },
    danger = false
  ) => (
    <View style={[styles.card, tx.stateCard]}>
      <View style={[tx.stateIcon, danger && tx.stateIconDanger]}>
        <Icon size={24} color={danger ? palette.danger : palette.accent} strokeWidth={2} />
      </View>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyText}>{message}</Text>
      {action && (
        <Pressable
          onPress={action.onPress}
          style={({ pressed }) => [action.primary ? styles.emptyButton : tx.secondaryPill, pressed && tx.rowPressed]}
          accessibilityRole="button"
        >
          <action.Icon
            size={15}
            color={action.primary ? palette.onAccent : palette.text}
            strokeWidth={2.4}
          />
          <Text style={action.primary ? styles.emptyButtonText : tx.secondaryPillText}>{action.label}</Text>
        </Pressable>
      )}
    </View>
  );

  const renderList = () => {
    if (loading && !loaded) return renderSkeleton();

    if (error && !loaded) {
      return renderState(TriangleAlert, "Couldn't load transactions", error, {
        label: "Try again",
        Icon: RefreshCw,
        onPress: retry,
      }, true);
    }

    if (transactions.length === 0) {
      return renderState(
        Inbox,
        "No transactions yet",
        "Expenses you record will appear here.",
        onAddExpense ? { label: "Add an expense", Icon: Plus, onPress: onAddExpense, primary: true } : undefined
      );
    }

    if (filtered.length === 0) {
      return renderState(SearchX, "No matching transactions", "Try a different search or adjust your filters.", {
        label: "Clear search and filters",
        Icon: X,
        onPress: () => setFilters(DEFAULT_FILTERS),
      });
    }

    return groups.map((group) => (
      <View key={group.key}>
        <View style={tx.groupHeader}>
          <Text style={tx.groupTitle}>{group.title}</Text>
          <Text style={tx.groupTotal}>{formatAED(group.total)}</Text>
        </View>
        <View style={tx.groupCard}>
          {group.items.map((transaction, index) => (
            <TransactionRow
              key={transaction.id}
              transaction={transaction}
              today={today}
              first={index === 0}
              onPress={setSelected}
            />
          ))}
        </View>
      </View>
    ));
  };

  return (
    <SafeAreaView style={styles.screen} edges={["top", "left", "right"]}>
      <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />

      <KeyboardFormScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={palette.accent} />
        }
      >
        <View style={styles.header}>
          <View style={styles.headerText}>
            <Text style={styles.eyebrow}>Your activity</Text>
            <Text style={styles.title}>Transactions</Text>
          </View>
        </View>

        {onAddExpense && <Pressable onPress={onAddExpense} style={tx.addButton} accessibilityRole="button" accessibilityLabel="Add transaction">
          <Plus size={19} color={palette.onAccent} strokeWidth={2.4} />
          <Text style={tx.addButtonText}>Add transaction</Text>
        </Pressable>}

        {/* Summary for the current search and filters */}
        <View style={styles.card}>
          <View style={tx.summaryRow}>
            <Text style={styles.cardLabel}>Total spending</Text>
            {loaded && (
              <View style={tx.countBadge}>
                <Text style={tx.countText}>
                  {summary.count} {summary.count === 1 ? "transaction" : "transactions"}
                </Text>
              </View>
            )}
          </View>
          <Text style={tx.summaryAmount} adjustsFontSizeToFit numberOfLines={1}>
            {loaded ? formatAED(summary.total) : "—"}
          </Text>
          <Text style={tx.summaryCaption} numberOfLines={2}>
            {loaded ? summaryCaption : loading ? "Loading your transactions…" : "Unavailable"}
          </Text>
        </View>

        <View style={tx.searchBar}>
          <Search size={17} color={palette.textMuted} strokeWidth={2.2} />
          <TextInput
            value={filters.search}
            onChangeText={(search) => setFilters((current) => ({ ...current, search }))}
            placeholder="Search description or category"
            placeholderTextColor={palette.textMuted}
            style={tx.searchInput}
            returnKeyType="search"
            autoCorrect={false}
            autoCapitalize="none"
            clearButtonMode="never"
            accessibilityLabel="Search transactions"
          />
          {filters.search !== "" && (
            <Pressable
              onPress={() => setFilters((current) => ({ ...current, search: "" }))}
              hitSlop={10}
              accessibilityRole="button"
              accessibilityLabel="Clear search"
            >
              <X size={17} color={palette.textMuted} strokeWidth={2.2} />
            </Pressable>
          )}
        </View>

        <TransactionFilters
          filters={filters}
          categories={categories}
          today={today}
          onChange={setFilters}
        />

        {error && loaded ? (
          <View style={styles.errorBanner}>
            <TriangleAlert size={16} color={palette.danger} strokeWidth={2.2} />
            <Text style={styles.errorBannerText}>Couldn’t refresh. Showing your last loaded transactions.</Text>
          </View>
        ) : null}

        {renderList()}

        {/* Recurring expense schedules (unchanged feature) */}
        <View style={tx.recurringSection}>
          <RecurringExpenses key={refreshKey} apiBaseUrl={apiBaseUrl} onChanged={() => setReload((value) => value + 1)} />
        </View>
      </KeyboardFormScrollView>

      <TransactionDetail
        transaction={selected}
        deleting={selected !== null && deletingId === selected.id}
        onClose={() => setSelected(null)}
        onDelete={(transaction) => { void deleteTransaction(transaction); }}
      />
    </SafeAreaView>
  );
}
