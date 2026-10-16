
import React from "react";
import { Pressable } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import {
  ChartPie,
  ChevronRight,
  CreditCard,
  PiggyBank,
  Wallet,
} from "lucide-react-native";
import { useDashboardTheme } from "./useDashboardTheme";
import { createHomeSectionsStyles } from "../../styles/HomeSectionsStyles";

type Props = {
  onOpenBudget: () => void;
  onOpenSpending: () => void;
  onOpenDebt: () => void;
  onOpenSavings: () => void;
};

export default function HomeSections({
  onOpenBudget,
  onOpenSpending,
  onOpenDebt,
  onOpenSavings,
}: Props) {
  const { palette } = useDashboardTheme();
  const s = createHomeSectionsStyles(palette);

  const sections = [
    {
      title: "Budget Tracker",
      Icon: ChartPie,
      onPress: onOpenBudget,
      subtitle: "Monthly budget and category targets",
      hint: "Open your budget tracker",
    },
    {
      title: "Debt",
      Icon: CreditCard,
      onPress: onOpenDebt,
      subtitle: "Balances and estimated payments",
      hint: "Manage your debts",
    },
    {
      title: "Spending",
      Icon: Wallet,
      onPress: onOpenSpending,
      subtitle: "Spending breakdown and expenses",
      hint: "Open spending breakdown and expenses",
    },
    {
      title: "Savings",
      Icon: PiggyBank,
      onPress: onOpenSavings,
      subtitle: "Confirmed savings and monthly history",
      hint: "Review and confirm monthly savings",
    },
  ];

  return (
    <View style={s.list}>
      {sections.map(({ title, Icon, onPress, subtitle, hint }) => (
        <Pressable
          key={title}
          onPress={onPress}
          accessibilityRole="button"
          accessibilityLabel={title}
          accessibilityHint={hint}
          style={({ pressed }) => [
            s.card,
            pressed && s.pressed,
          ]}
        >
          <View style={s.icon}>
            <Icon size={24} color={palette.accent} />
          </View>

          <View style={s.body}>
            <Text style={s.title}>{title}</Text>
            <Text style={s.subtitle}>{subtitle}</Text>
          </View>

          <ChevronRight size={21} color={palette.accent} />
        </Pressable>
      ))}
    </View>
  );
}
