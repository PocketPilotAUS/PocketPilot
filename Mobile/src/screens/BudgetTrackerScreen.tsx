import React from "react";
import { ActivityIndicator, StatusBar } from "react-native";
import { Text, View } from "../preferences/LocalizedNative";
import { SafeAreaView } from "react-native-safe-area-context";
import { TriangleAlert } from "lucide-react-native";
import BackButton from "../components/BackButton";
import { navigationStyles } from "../styles/NavigationStyles";
import KeyboardFormScrollView from "../components/KeyboardFormScrollView";
import BudgetTracker from "../components/dashboard/BudgetTracker";
import { useDashboardTheme } from "../components/dashboard/useDashboardTheme";

type Props = React.ComponentProps<typeof BudgetTracker> & {
  loading: boolean;
  error: string;
  onBack: () => void;
};

export default function BudgetTrackerScreen({ loading, error, onBack, ...trackerProps }: Props) {
  const { styles, palette, mode } = useDashboardTheme();

  return (
    <SafeAreaView style={styles.screen} edges={["top", "left", "right"]}>
      <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />
      <KeyboardFormScrollView contentContainerStyle={styles.content}>
        <View style={[styles.header, navigationStyles.header]}>
          <BackButton onPress={onBack} label="Back to Home" />
          <View style={styles.headerText}>
            <Text style={styles.eyebrow}>Your finances</Text>
            <Text style={styles.title}>Budget Tracker</Text>
          </View>
        </View>
        {!!error && (
          <View style={styles.errorBanner}>
            <TriangleAlert size={16} color={palette.danger} />
            <Text style={styles.errorBannerText}>{error}</Text>
          </View>
        )}
        {loading ? (
          <ActivityIndicator color={palette.accent} accessibilityLabel="Loading budget" />
        ) : (
          <BudgetTracker {...trackerProps} />
        )}
      </KeyboardFormScrollView>
    </SafeAreaView>
  );
}
