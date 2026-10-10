import React, { useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, StatusBar, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import AmbientBackground from "../components/AmbientBackground";
import MetallicGlassButton from "../components/MetallicGlassButton";
import MetallicGlassCard from "../components/MetallicGlassCard";
import { apiFetch, SessionExpiredError } from "../services/apiClient";
import { useAppTheme } from "../theme/ThemeContext";
import { createAIInsightsStyles } from "../styles/AIInsightsStyles";

type Insight = {
  category: string;
  priority: string;
  percentage_change: number;
  recommendation: string;
  ai_explanation: string | null;
};
type Props = { apiBaseUrl: string; onBack: () => void };

export default function AIInsightsScreen({ apiBaseUrl, onBack }: Props) {
  const { colors, mode } = useAppTheme();
  const styles = createAIInsightsStyles(colors);
  const [month, setMonth] = useState(() => {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 1);
  });
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const monthLabel = month.toLocaleDateString("en", { month: "long", year: "numeric" });
  const today = new Date();
  const isCurrentMonth = month.getFullYear() === today.getFullYear() && month.getMonth() === today.getMonth();

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 180000);
    setLoading(true);
    setError("");
    setInsights([]);
    const load = async () => {
      try {
        const response = await apiFetch(apiBaseUrl,
          `/recommendations/ai?year=${month.getFullYear()}&month=${month.getMonth() + 1}`,
          { signal: controller.signal });
        if (!response.ok) {
          throw new Error(response.status === 503
            ? "AI insights are temporarily unavailable. Please try again later."
            : "Could not load AI insights. Please try again.");
        }
        const data: { ai_recommendations: Insight[] } = await response.json();
        if (!Array.isArray(data.ai_recommendations)) throw new Error("Could not load AI insights. Please try again.");
        if (active) setInsights(data.ai_recommendations);
      } catch (err) {
        if (!active || err instanceof SessionExpiredError) return;
        setError(controller.signal.aborted
          ? "AI insights took too long to generate. Please try again."
          : err instanceof Error && (err.message.startsWith("AI insights") || err.message.startsWith("Could not load"))
            ? err.message
            : "Could not connect. Check your connection and try again.");
      } finally {
        clearTimeout(timeout);
        if (active) setLoading(false);
      }
    };
    void load();
    return () => { active = false; clearTimeout(timeout); controller.abort(); };
  }, [apiBaseUrl, month, attempt]);

  const changeMonth = (offset: number) => {
    setLoading(true);
    setMonth(current => new Date(current.getFullYear(), current.getMonth() + offset, 1));
  };

  return (
    <SafeAreaView style={styles.container} edges={["top", "left", "right"]}>
      <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />
      <AmbientBackground />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>AI Insights</Text>
        <Text style={styles.subtitle}>Understand your spending with explanations based on your recorded expenses.</Text>
        <MetallicGlassCard>
          <Text style={styles.month}>{monthLabel}</Text>
          <Text style={styles.caption}>Compared with the previous month</Text>
          <View style={styles.controls}>
            <View style={styles.control}><MetallicGlassButton title="Previous" variant="secondary" onPress={() => changeMonth(-1)} disabled={month.getFullYear() <= 2 && month.getMonth() === 0} /></View>
            <View style={styles.control}><MetallicGlassButton title="Next" variant="secondary" onPress={() => changeMonth(1)} disabled={isCurrentMonth} /></View>
          </View>
        </MetallicGlassCard>
        {loading ? (
          <MetallicGlassCard>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={styles.loading}>Preparing your AI insights… This may take a moment.</Text>
          </MetallicGlassCard>
        ) : error ? (
          <MetallicGlassCard>
            <Text style={styles.error} accessibilityRole="alert">{error}</Text>
            <MetallicGlassButton title="Try Again" onPress={() => setAttempt(value => value + 1)} />
          </MetallicGlassCard>
        ) : insights.length === 0 ? (
          <MetallicGlassCard>
            <Text style={styles.heading}>No insights for this month yet</Text>
            <Text style={styles.body}>Insights appear when spending in a category changes by at least 20% from the previous month. Record expenses in both months or choose another month.</Text>
          </MetallicGlassCard>
        ) : insights.map((insight, index) => (
          <MetallicGlassCard key={`${insight.category}-${index}`}>
            <Text style={styles.heading}>{insight.category}</Text>
            <Text style={styles.caption}>{insight.percentage_change >= 0 ? "Increased" : "Decreased"} by {Math.abs(insight.percentage_change).toFixed(1)}% · {insight.priority === "high" ? "Worth reviewing" : "Spending update"}</Text>
            <Text style={styles.body}>{insight.recommendation}</Text>
            <View style={styles.explanation}>
              <Text style={styles.label}>AI EXPLANATION</Text>
              <Text style={styles.body}>{insight.ai_explanation?.trim() || "An explanation was not returned. Please refresh to try again."}</Text>
            </View>
          </MetallicGlassCard>
        ))}
        {!loading && !error && insights.length > 0 && <MetallicGlassButton title="Refresh Insights" variant="secondary" onPress={() => setAttempt(value => value + 1)} />}
      </ScrollView>
    </SafeAreaView>
  );
}
