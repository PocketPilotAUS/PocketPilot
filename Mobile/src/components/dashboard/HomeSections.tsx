import React from "react";
import { Pressable } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import { ChevronRight, CreditCard, PiggyBank, Wallet } from "lucide-react-native";
import { useDashboardTheme } from "./useDashboardTheme";
import { createHomeSectionsStyles } from "../../styles/HomeSectionsStyles";

export default function HomeSections({ onOpenSpending, onOpenDebt, onOpenSavings }: { onOpenSpending: () => void; onOpenDebt: () => void; onOpenSavings: () => void }) {
  const { palette } = useDashboardTheme();
  const s = createHomeSectionsStyles(palette);
  const sections = [
    { title: "Debt", Icon: CreditCard, enabled: true },
    { title: "Spending", Icon: Wallet, enabled: true },
    { title: "Savings", Icon: PiggyBank, enabled: true },
  ];
  return <View style={s.list}>
    {sections.map(({ title, Icon, enabled }) => <Pressable key={title} disabled={!enabled} onPress={title === "Debt" ? onOpenDebt : title === "Savings" ? onOpenSavings : onOpenSpending}
      accessibilityRole="button" accessibilityLabel={title} accessibilityState={{ disabled: !enabled }} accessibilityHint={title === "Debt" ? "Manage your debts" : title === "Savings" ? "Review and confirm monthly savings" : "Open spending breakdown and budget tracker"}
      style={({ pressed }) => [s.card, pressed && s.pressed]}>
      <View style={[s.icon, !enabled && s.placeholderIcon]}><Icon size={24} color={enabled ? palette.accent : palette.textMuted} /></View>
      <View style={s.body}><Text style={s.title}>{title}</Text><Text style={s.subtitle}>{title === "Debt" ? "Balances and estimated payments" : title === "Savings" ? "Confirmed savings and monthly history" : "Spending breakdown and budget tracker"}</Text></View>
      {enabled && <ChevronRight size={21} color={palette.accent} />}
    </Pressable>)}
  </View>;
}
