import React, { useEffect, useState } from "react";
import { Keyboard, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Home, History, Plus, MessageCircle, ChartNoAxesCombined } from "lucide-react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useAppTheme } from "../theme/ThemeContext";
import { createBottomNavigationStyles } from "../styles/BottomNavigationStyles";

export type AppTab = "dashboard" | "history" | "addTransaction" | "aiChat" | "aiInsights";
const tabs = [
  { screen: "dashboard", label: "Home", icon: Home },
  { screen: "history", label: "History", icon: History },
  { screen: "addTransaction", label: "Add", icon: Plus },
  { screen: "aiChat", label: "AI Chat", icon: MessageCircle },
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
        return <Pressable key={screen} accessibilityRole="tab" accessibilityLabel={screen === "addTransaction" ? "Add expense" : label} accessibilityState={{ selected }} onPress={() => onSelect(screen)} style={({ pressed }) => [styles.tab, selected && styles.selected, { opacity: pressed ? 0.7 : 1 }]}>
          {screen === "addTransaction" ? <LinearGradient colors={mode === "dark" ? ["#DCE0E7", "#727B89"] : ["#737B88", "#303640"]} style={styles.add}><Icon size={26} color={colors.primaryText} strokeWidth={2.5} /></LinearGradient> : <Icon size={22} color={selected ? colors.text : colors.textMuted} strokeWidth={selected ? 2.3 : 1.7} />}
          <Text style={[styles.label, selected && styles.activeLabel]}>{label}</Text>
          <View style={[styles.indicator, { backgroundColor: selected ? colors.primary : "transparent" }]} />
        </Pressable>;
      })}
    </View>
  </View>;
}
