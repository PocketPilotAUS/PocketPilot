import React, { useEffect, useState } from "react";
import { Keyboard, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Home, History, Plus, Sparkles, ChartNoAxesCombined } from "lucide-react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useAppTheme } from "../theme/ThemeContext";
import { createBottomNavigationStyles } from "../styles/BottomNavigationStyles";

export type AppTab = "dashboard" | "history" | "addTransaction" | "aiChat" | "aiInsights";
// AI Chat sits in the centre as the prominent tab
const tabs = [
  { screen: "dashboard", label: "Home", icon: Home },
  { screen: "history", label: "History", icon: History },
  { screen: "aiChat", label: "AI Chat", icon: Sparkles },
  { screen: "addTransaction", label: "Add", icon: Plus },
  { screen: "aiInsights", label: "Insights", icon: ChartNoAxesCombined },
] as const;

export default function BottomNavigation({ active, onSelect }: { active: AppTab; onSelect: (tab: AppTab) => void }) {
  const { colors, mode } = useAppTheme();
  const styles = createBottomNavigationStyles(colors);
  const insets = useSafeAreaInsets();
  const [keyboardOpen, setKeyboardOpen] = useState(Keyboard.isVisible());
  useEffect(() => {
    const show = Keyboard.addListener("keyboardDidShow", () => setKeyboardOpen(true));
    const hide = Keyboard.addListener("keyboardDidHide", () => setKeyboardOpen(false));
    return () => { show.remove(); hide.remove(); };
  }, []);
  if (keyboardOpen) return null;
  return <View style={[styles.container, { paddingBottom: Math.max(insets.bottom, 10) }]}>
    <View style={styles.bar}>
      {tabs.map(({ screen, label, icon: Icon }) => {
        const selected = active === screen;
        const prominent = screen === "aiChat";
        return <Pressable key={screen} accessibilityRole="tab" accessibilityLabel={screen === "addTransaction" ? "Add expense" : label} accessibilityState={{ selected }} onPress={() => onSelect(screen)} style={({ pressed }) => [styles.tab, selected && !prominent && styles.selected, { opacity: pressed ? 0.7 : 1 }]}>
          {prominent ? <LinearGradient colors={mode === "dark" ? ["#5FF0CE", "#1FA88A"] : ["#2CC9A6", "#0B8A71"]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[styles.ai, selected && styles.aiSelected]}><Icon size={24} color={mode === "dark" ? "#04241C" : "#FFFFFF"} strokeWidth={2.3} /></LinearGradient> : <Icon size={22} color={selected ? colors.text : colors.textMuted} strokeWidth={selected ? 2.3 : 1.7} />}
          <Text style={[styles.label, selected && styles.activeLabel, prominent && styles.aiLabel]}>{label}</Text>
          {!prominent && <View style={[styles.indicator, { backgroundColor: selected ? colors.primary : "transparent" }]} />}
        </Pressable>;
      })}
    </View>
  </View>;
}
