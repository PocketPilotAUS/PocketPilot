import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";
export const createHomeSectionsStyles = (p: DashboardPalette) => StyleSheet.create({
  list: { gap: 12, marginBottom: 16 },
  card: { flexDirection: "row", alignItems: "center", gap: 14, minHeight: 88, padding: 18, borderRadius: 20, borderWidth: 1, borderColor: p.border, backgroundColor: p.card },
  icon: { width: 46, height: 46, borderRadius: 14, alignItems: "center", justifyContent: "center", backgroundColor: p.accentSoft },
  placeholderIcon: { backgroundColor: p.track },
  body: { flex: 1, gap: 4 },
  title: { color: p.text, fontSize: 18, fontWeight: "700" },
  subtitle: { color: p.textSecondary, fontSize: 12, lineHeight: 18 },
  pressed: { opacity: .75 },
});
