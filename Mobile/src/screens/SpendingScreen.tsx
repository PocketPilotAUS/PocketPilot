
import React, { useRef, useState } from "react";
import { Modal, StatusBar } from "react-native";
import { Text, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { TriangleAlert } from "lucide-react-native";
import AddTransactionScreen from "./AddTransactionScreen";
import BackButton from "../components/BackButton";
import { navigationStyles } from "../styles/NavigationStyles";
import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import SpendingBreakdown from "../components/dashboard/SpendingBreakdown";
import { useDashboardTheme } from "../components/dashboard/useDashboardTheme";
import type { DashboardData } from "../utils/dashboard";

type Props = {
  data: DashboardData | null;
  loading: boolean;
  error: string;
  onBack: () => void;
  apiBaseUrl: string;
  onExpenseSaved: () => void;
};

export default function SpendingScreen({
  data,
  loading,
  error,
  onBack,
  apiBaseUrl,
  onExpenseSaved,
}: Props) {
  const { styles, palette, mode } = useDashboardTheme();
  const [adding, setAdding] = useState(false);
  const saving = useRef(false);
  const close = () => {
    if (!saving.current) setAdding(false);
  };

  return (
    <SafeAreaView
      style={styles.screen}
      edges={["top", "left", "right"]}
    >
      <StatusBar
        barStyle={mode === "dark" ? "light-content" : "dark-content"}
      />

      <KeyboardFormScrollView contentContainerStyle={styles.content}>
        <View style={[styles.header, navigationStyles.header]}>
          <BackButton onPress={onBack} label="Back to Home" />

          <View style={styles.headerText}>
            <Text style={styles.eyebrow}>Your finances</Text>
            <Text style={styles.title}>Spending</Text>
          </View>
        </View>

        {!!error && (
          <View style={styles.errorBanner}>
            <TriangleAlert size={16} color={palette.danger} />
            <Text style={styles.errorBannerText}>{error}</Text>
          </View>
        )}

        <SpendingBreakdown
          data={data}
          loading={loading}
          onAddExpense={() => setAdding(true)}
        />
      </KeyboardFormScrollView>
      <Modal visible={adding} animationType="slide" presentationStyle="pageSheet" onRequestClose={close}>
        {adding && <AddTransactionScreen
          apiBaseUrl={apiBaseUrl}
          budgetCategories={data?.ideal_budget?.allocations.map(row => row.category)}
          onBack={close}
          onBusyChange={busy => { saving.current = busy; }}
          onSaved={() => {
            saving.current = false;
            setAdding(false);
            onExpenseSaved();
          }}
        />}
      </Modal>
    </SafeAreaView>
  );
}
