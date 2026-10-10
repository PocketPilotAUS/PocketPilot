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
  indicator: { width: 12, height: 2, borderRadius: 1, marginTop: 4 },
});
