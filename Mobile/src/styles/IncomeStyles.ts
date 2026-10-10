import { StyleSheet } from "react-native";
import type { AppColors } from "../theme/colors";
export const createIncomeStyles = (colors: AppColors) => StyleSheet.create({
  label: { color: colors.textSecondary, fontSize: 12, fontWeight: "600", letterSpacing: 1 },
  amount: { color: colors.text, fontSize: 30, fontWeight: "700", marginTop: 12 },
  hint: { color: colors.textMuted, fontSize: 12, lineHeight: 19, marginTop: 8 },
  row: { flexDirection: "row", justifyContent: "space-between", gap: 10, marginTop: 16 },
  body: { color: colors.textSecondary, fontSize: 14 },
  value: { color: colors.text, fontSize: 14, fontWeight: "600" },
  track: { height: 12, borderRadius: 6, backgroundColor: colors.surfaceElevated, overflow: "hidden", marginTop: 20 },
  fill: { height: "100%", borderRadius: 6 },
  input: { backgroundColor: colors.surfaceElevated, borderColor: colors.glassBorder, borderWidth: 1, borderRadius: 14, color: colors.text, padding: 14, marginVertical: 16 },
  button: { marginTop: 18 },
  error: { color: colors.error, fontSize: 14, lineHeight: 21 },
});
