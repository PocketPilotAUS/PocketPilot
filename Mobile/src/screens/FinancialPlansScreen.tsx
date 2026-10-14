import React from "react";
import { StatusBar } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import FinancialPlans from "../components/ai/FinancialPlans";
import { useAITheme } from "../components/ai/useAITheme";
import type { FinancialPlan, PlanningProfile } from "../types/plans";

type Props = {
  apiBaseUrl: string;
  initialProfile?: PlanningProfile;
  onPreview: (plan: FinancialPlan) => void;
  onStartPlanning: () => void;
};

export default function FinancialPlansScreen(props: Props) {
  const { ai, mode } = useAITheme();
  return <SafeAreaView style={ai.screen} edges={["top", "left", "right"]}>
    <StatusBar barStyle={mode === "dark" ? "light-content" : "dark-content"} />
    <FinancialPlans {...props} />
  </SafeAreaView>;
}
