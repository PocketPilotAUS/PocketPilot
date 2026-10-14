import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";
export const createSavingsStyles = (p: DashboardPalette) => StyleSheet.create({
  manualAddButton: { marginBottom: 16 },
  manualPressed: { opacity: .75 },
  manualRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: p.border },
  manualBody: { flex: 1, gap: 6 },
  manualAction: { width: 44, height: 44, alignItems: "center", justifyContent: "center", borderRadius: 14, backgroundColor: p.cardRaised },
  header: { marginTop: 4 },
  icon: { width: 42, height: 42, borderRadius: 14, alignItems: "center", justifyContent: "center", backgroundColor: p.accentSoft },
  selector: { flexDirection: "row", gap: 12, alignItems: "center", marginBottom: 18 },
  month: { flex: 1, color: p.text, fontSize: 17, fontWeight: "700", textAlign: "center" },
  monthButton: { width: 44, height: 44, borderRadius: 14, backgroundColor: p.cardRaised, alignItems: "center", justifyContent: "center" },
  field: { marginTop: 18 },
  action: { flexGrow: 0, marginTop: 18, minHeight: 46, justifyContent: "center" },
  note: { marginTop: 12 },
  historyTitle: { color: p.text, fontSize: 18, fontWeight: "700", marginBottom: 14 },
  historyRow: { paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: p.border, gap: 6 },
  historyHeading: { flexDirection: "row", flexWrap: "wrap", gap: 8, justifyContent: "space-between" },
  rowTitle: { color: p.text, fontSize: 15, fontWeight: "600" },
  rowValue: { color: p.accent, fontSize: 16, fontWeight: "700" },
});
