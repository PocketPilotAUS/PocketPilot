import { StyleSheet } from "react-native";
import type { AppColors } from "../theme/colors";
export const createBottomNavigationStyles = (colors: AppColors) => StyleSheet.create({
  container: { backgroundColor: colors.background, paddingHorizontal: 12, paddingTop: 8 },
  bar: { flexDirection: "row", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.glassBorder, borderRadius: 24, padding: 5, alignItems: "center" },
  tab: { flex: 1, minHeight: 66, borderRadius: 18, alignItems: "center", justifyContent: "center", paddingVertical: 4 },
  selected: { backgroundColor: colors.glassSurface },
  label: { color: colors.textMuted, fontSize: 10, fontWeight: "500", marginTop: 4 },
  activeLabel: { color: colors.text, fontWeight: "700" },
  add: { width: 42, height: 32, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  // Prominent centre AI button (mint/teal), raised slightly above the bar
  ai: { width: 52, height: 52, borderRadius: 26, alignItems: "center", justifyContent: "center", marginTop: -22, shadowColor: "#2CC9A6", shadowOpacity: 0.45, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 6 },
  aiSelected: { borderWidth: 2, borderColor: colors.text },
  aiLabel: { color: colors.text, fontWeight: "700" },
  indicator: { width: 12, height: 2, borderRadius: 1, marginTop: 4 },
});
