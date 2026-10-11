import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";
export const createPlanningStyles = (p: DashboardPalette) => StyleSheet.create({
  content: { padding: 18, gap: 16, paddingBottom: 36 },
  card: { padding: 18, borderRadius: 22, backgroundColor: p.card, borderColor: p.border, borderWidth: 1, gap: 12 },
  title: { color: p.text, fontSize: 20, fontWeight: "700" },
  text: { color: p.textSecondary, fontSize: 14, lineHeight: 21 },
  label: { color: p.text, fontSize: 14, fontWeight: "600" },
  input: { backgroundColor: p.input, color: p.text, borderColor: p.border, borderWidth: 1, padding: 13, borderRadius: 14, fontSize: 15 },
  button: { backgroundColor: p.accent, borderRadius: 14, padding: 13, alignItems: "center" },
  buttonText: { color: p.onAccent, fontSize: 14, fontWeight: "700" },
  secondary: { backgroundColor: p.cardRaised, borderColor: p.border, borderWidth: 1 },
  secondaryText: { color: p.text },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { backgroundColor: p.cardRaised, padding: 10, borderRadius: 12, borderColor: p.border, borderWidth: 1 },
  selected: { borderColor: p.accent, backgroundColor: p.accentSoft },
  error: { color: p.danger, fontSize: 14, lineHeight: 21 },
  muted: { opacity: .5 },
});
