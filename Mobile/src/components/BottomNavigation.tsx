import React, { useEffect, useState } from "react";
import { Keyboard, Pressable } from "react-native";
import { Text, View } from "../preferences/LocalizedNative";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Home, History, Sparkles, ChartNoAxesCombined } from "lucide-react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useAppTheme } from "../theme/ThemeContext";
import { createBottomNavigationStyles } from "../styles/BottomNavigationStyles";
import { usePreferences } from "../preferences/PreferencesContext";

export type AppTab = "dashboard" | "history" | "aiChat" | "aiInsights";
// Transactions combines the list and the add form in one destination.
const tabs = [
  { screen: "dashboard", label: "home", icon: Home },
  { screen: "history", label: "transactions", icon: History },
  { screen: "aiChat", label: "chat", icon: Sparkles },
  { screen: "aiInsights", label: "insights", icon: ChartNoAxesCombined },
] as const;

export default function BottomNavigation({ active, onSelect }: { active: AppTab; onSelect: (tab: AppTab) => void }) {
  const { colors, mode } = useAppTheme();
  const { t } = usePreferences();
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
        return <Pressable key={screen} accessibilityRole="tab" accessibilityLabel={t(label)} accessibilityState={{ selected }} onPress={() => onSelect(screen)} style={({ pressed }) => [styles.tab, selected && !prominent && styles.selected, { opacity: pressed ? 0.7 : 1 }]}>
          {prominent ? <LinearGradient colors={mode === "dark" ? ["#5FF0CE", "#1FA88A"] : ["#2CC9A6", "#0B8A71"]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={[styles.ai, selected && styles.aiSelected]}><Icon size={24} color={mode === "dark" ? "#04241C" : "#FFFFFF"} strokeWidth={2.3} /></LinearGradient> : <Icon size={22} color={selected ? colors.text : colors.textMuted} strokeWidth={selected ? 2.3 : 1.7} />}
          <Text numberOfLines={1} adjustsFontSizeToFit minimumFontScale={.7} style={[styles.label, selected && styles.activeLabel, prominent && styles.aiLabel]}>{t(label)}</Text>
          {!prominent && <View style={[styles.indicator, { backgroundColor: selected ? colors.primary : "transparent" }]} />}
        </Pressable>;
      })}
    </View>
  </View>;
}
