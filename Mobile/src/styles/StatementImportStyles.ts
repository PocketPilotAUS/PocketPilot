import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";
export const createStatementImportStyles = (p: DashboardPalette) => StyleSheet.create({
  flex: { flex: 1 },
  header: { paddingHorizontal: 18 },
  content: { paddingHorizontal: 18, paddingBottom: 24, gap: 14 },
  options: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginVertical: 8 },
  option: { paddingHorizontal: 13, paddingVertical: 11, borderRadius: 12, borderWidth: 1, borderColor: p.border, backgroundColor: p.card, minHeight: 44 },
  selected: { backgroundColor: p.accentSoft, borderColor: p.accent },
  text: { color: p.textSecondary, fontSize: 13, lineHeight: 19 },
  title: { color: p.text, fontSize: 15, fontWeight: "700" },
  muted: { opacity: .5 },
  card: { padding: 16, borderRadius: 18, backgroundColor: p.card, borderWidth: 1, borderColor: p.border, gap: 8 },
  warning: { color: p.danger, fontSize: 13, lineHeight: 19 },
  input: { color: p.text, borderWidth: 1, borderColor: p.border, padding: 12, borderRadius: 12, fontSize: 14 },
  footer: { padding: 16, gap: 8, borderTopWidth: 1, borderTopColor: p.border, backgroundColor: p.background },
  button: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, backgroundColor: p.accent, padding: 14, minHeight: 48, borderRadius: 14 },
  buttonText: { color: p.onAccent, fontSize: 15, fontWeight: "700" },
});
