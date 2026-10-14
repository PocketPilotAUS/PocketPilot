import React from "react";
import { StatusBar } from "react-native";
import { Text, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { TriangleAlert } from "lucide-react-native";
import BackButton from "../components/BackButton";
import { navigationStyles } from "../styles/NavigationStyles";
import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import SpendingBreakdown from "../components/dashboard/SpendingBreakdown";
import BudgetTracker from "../components/dashboard/BudgetTracker";
import { useDashboardTheme } from "../components/dashboard/useDashboardTheme";
import type { DashboardData } from "../utils/dashboard";

type Props = {
  data: DashboardData | null; loading: boolean; error: string; apiBaseUrl: string;
  onBack: () => void; onAddExpense: () => void; onSaved: (data: DashboardData) => void;
  onReview: () => void; aiBusy: boolean;
};

export default function SpendingScreen({ data, loading, error, apiBaseUrl, onBack, onAddExpense, onSaved, onReview, aiBusy }: Props) {
  const { styles, palette, mode } = useDashboardTheme();
  return <SafeAreaView style={styles.screen} edges={["top", "left", "right"]}>
    <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />
    <KeyboardFormScrollView contentContainerStyle={styles.content}>
      <View style={[styles.header, navigationStyles.header]}>
        <BackButton onPress={onBack} label="Back to Home" />
        <View style={styles.headerText}><Text style={styles.eyebrow}>Your finances</Text><Text style={styles.title}>Spending</Text></View>
      </View>
      {!!error && <View style={styles.errorBanner}><TriangleAlert size={16} color={palette.danger} /><Text style={styles.errorBannerText}>{error}</Text></View>}
      <SpendingBreakdown data={data} loading={loading} onAddExpense={onAddExpense} />
      <BudgetTracker data={data} apiBaseUrl={apiBaseUrl} onSaved={onSaved} onReview={onReview} aiBusy={aiBusy} />
    </KeyboardFormScrollView>
  </SafeAreaView>;
}
