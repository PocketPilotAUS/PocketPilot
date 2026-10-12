import React, { useEffect, useState } from "react";
import { Pressable, RefreshControl, ScrollView, StatusBar } from "react-native";
import { Text, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { RefreshCw, TriangleAlert } from "lucide-react-native";

import CategoryChanges, { AIState } from "../components/insights/CategoryChanges";
import InsightSummary from "../components/insights/InsightSummary";
import InsightsOverview from "../components/insights/InsightsOverview";
import MonthSelector from "../components/insights/MonthSelector";
import SpendingTrend from "../components/insights/SpendingTrend";
import { useInsightsTheme } from "../components/insights/useInsightsTheme";
import { apiFetch, SessionExpiredError } from "../services/apiClient";
import type { DashboardData } from "../utils/dashboard";
import {
  AIRecommendation,
  MonthComparison,
  RuleRecommendation,
  buildCategoryChanges,
  buildTrend,
} from "../utils/insights";
import type { Transaction } from "../utils/transactions";
import { usePreferences } from "../preferences/PreferencesContext";

type Props = { apiBaseUrl: string; onBack: () => void };

// Data for one month; `key` records which month/refresh it belongs to, so a
// new month shows as loading without resetting state inside an effect
type MonthResult =
  | { key: string; status: "ready"; budget: DashboardData; comparison: MonthComparison; rules: RuleRecommendation[] }
  | { key: string; status: "error" };

async function getJson<T>(apiBaseUrl: string, path: string, signal?: AbortSignal): Promise<T> {
  const response = await apiFetch(apiBaseUrl, path, { signal });
  if (!response.ok) throw Object.assign(new Error(path), { status: response.status });
  return response.json();
}

export default function AIInsightsScreen({ apiBaseUrl }: Props) {
  const { language } = usePreferences();
  const { styles, ins, palette, mode } = useInsightsTheme();

  const [month, setMonth] = useState(() => {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 1);
  });
  const [reload, setReload] = useState(0);
  const [aiAttempt, setAiAttempt] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const [monthResult, setMonthResult] = useState<MonthResult | null>(null);
  const [transactions, setTransactions] = useState<{ key: number; data: Transaction[] | null } | null>(null);
  const [aiResult, setAiResult] = useState<{ key: string; state: AIState } | null>(null);

  const year = month.getFullYear();
  const monthNumber = month.getMonth() + 1;
  const monthKey = `${year}-${monthNumber}-${reload}`;

  const today = new Date();
  const isCurrentMonth = year === today.getFullYear() && month.getMonth() === today.getMonth();

  // Overview, insight and category comparison for the selected month
  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const [budget, comparison, rules] = await Promise.all([
          getJson<DashboardData>(apiBaseUrl, `/budget/monthly?year=${year}&month=${monthNumber}`),
          getJson<MonthComparison>(apiBaseUrl, `/spending/compare?year=${year}&month=${monthNumber}`),
          // Backend rule: categories that changed by 20% or more
          getJson<{ recommendations: RuleRecommendation[] }>(apiBaseUrl, `/recommendations/?year=${year}&month=${monthNumber}`),
        ]);

        if (active) setMonthResult({ key: monthKey, status: "ready", budget, comparison, rules: rules.recommendations });
      } catch (err) {
        if (active && !(err instanceof SessionExpiredError)) setMonthResult({ key: monthKey, status: "error" });
      } finally {
        if (active) setRefreshing(false);
      }
    };

    void load();

    return () => {
      active = false;
    };
  }, [apiBaseUrl, year, monthNumber, monthKey]);

  // All transactions, for the monthly trend
  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const data = await getJson<Transaction[]>(apiBaseUrl, "/transactions/");
        if (active) setTransactions({ key: reload, data });
      } catch (err) {
        if (active && !(err instanceof SessionExpiredError)) setTransactions({ key: reload, data: null });
      }
    };

    void load();

    return () => {
      active = false;
    };
  }, [apiBaseUrl, reload]);

  const monthLoading = monthResult?.key !== monthKey;
  const ready = !monthLoading && monthResult?.status === "ready" ? monthResult : null;
  const flagged = ready ? ready.rules.length > 0 : false;
  const aiKey = `${monthKey}-${aiAttempt}-${language}`;

  // AI explanations (same request and timeout as before); only needed when
  // the 20% rule flagged something
  useEffect(() => {
    if (!flagged) return;

    let active = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 180000);

    const load = async () => {
      try {
        const data = await getJson<{ ai_recommendations: AIRecommendation[] }>(
          apiBaseUrl,
          `/recommendations/ai?year=${year}&month=${monthNumber}&language=${language}`,
          controller.signal
        );

        if (!Array.isArray(data.ai_recommendations)) throw new Error("format");
        if (active) setAiResult({ key: aiKey, state: { status: "ready", items: data.ai_recommendations } });
      } catch (err) {
        if (!active || err instanceof SessionExpiredError) return;

        const status = (err as { status?: number }).status;
        const message = controller.signal.aborted
          ? "AI explanations took too long to generate."
          : status === 503
            ? "AI explanations are temporarily unavailable."
            : status !== undefined
              ? "Could not load AI explanations."
              : "Could not connect for AI explanations.";

        setAiResult({ key: aiKey, state: { status: "error", message } });
      } finally {
        clearTimeout(timeout);
      }
    };

    void load();

    return () => {
      active = false;
      clearTimeout(timeout);
      controller.abort();
    };
  }, [apiBaseUrl, year, monthNumber, flagged, aiKey]);

  const aiState: AIState = !flagged
    ? { status: "idle" }
    : aiResult?.key === aiKey
      ? aiResult.state
      : { status: "loading" };

  const changeMonth = (offset: number) => {
    setMonth((current) => new Date(current.getFullYear(), current.getMonth() + offset, 1));
  };

  const refresh = () => {
    setRefreshing(true);
    setReload((value) => value + 1);
  };

  const trendLoading = transactions?.key !== reload;
  const trend = buildTrend(transactions?.data ?? [], year, monthNumber);
  const previousMonth = ready?.comparison.previous_month ?? new Date(year, monthNumber - 2, 1).getMonth() + 1;

  return (
    <SafeAreaView style={styles.screen} edges={["top", "left", "right"]}>
      <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />

      <ScrollView
        contentContainerStyle={ins.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={palette.accent} />}
      >
        <View style={styles.header}>
          <View style={styles.headerText}>
            <Text style={styles.eyebrow}>Your insights</Text>
            <Text style={styles.title}>Insights</Text>
          </View>
        </View>

        <MonthSelector
          month={month}
          canGoBack={!(year <= 2 && month.getMonth() === 0)}
          canGoForward={!isCurrentMonth}
          onChange={changeMonth}
        />

        {monthResult?.key === monthKey && monthResult.status === "error" ? (
          <View style={[styles.card, ins.centerCard]} accessibilityRole="alert">
            <View style={[styles.insightIcon, { backgroundColor: palette.dangerSoft }]}>
              <TriangleAlert size={17} color={palette.danger} strokeWidth={2.2} />
            </View>
            <Text style={styles.emptyTitle}>Couldn’t load your insights</Text>
            <Text style={styles.emptyText}>Check your connection and try again.</Text>
            <Pressable
              onPress={refresh}
              style={({ pressed }) => [styles.emptyButton, pressed && styles.buttonDisabled]}
              accessibilityRole="button"
            >
              <RefreshCw size={15} color={palette.onAccent} strokeWidth={2.4} />
              <Text style={styles.emptyButtonText}>Try again</Text>
            </Pressable>
          </View>
        ) : (
          <>
            <InsightsOverview data={ready?.budget ?? null} loading={monthLoading} />
            <InsightSummary data={ready?.budget ?? null} loading={monthLoading} />
          </>
        )}

        <SpendingTrend
          months={trend}
          loading={trendLoading}
          error={!trendLoading && transactions?.data === null}
          onSelect={(selectedYear, selectedMonth) => setMonth(new Date(selectedYear, selectedMonth - 1, 1))}
        />

        {monthLoading && (
          <View accessibilityLabel="Loading category changes">
            {[0, 1, 2].map((index) => (
              <View key={index} style={[ins.skeletonBlock, ins.skeletonCard]} />
            ))}
          </View>
        )}

        {ready && (
          <CategoryChanges
            changes={buildCategoryChanges(ready.comparison, ready.rules)}
            month={monthNumber}
            previousMonth={previousMonth}
            ai={aiState}
            onRetryAI={() => setAiAttempt((value) => value + 1)}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
