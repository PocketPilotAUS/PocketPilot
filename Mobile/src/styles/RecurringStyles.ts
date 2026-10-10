import { StyleSheet } from "react-native";
import type { AppColors } from "../theme/colors";
export const createRecurringStyles = (colors: AppColors) => StyleSheet.create({
  title: { color: colors.text, fontSize: 22, fontWeight: "700", marginVertical: 20 },
  heading: { color: colors.text, fontSize: 17, fontWeight: "700" },
  body: { color: colors.textSecondary, fontSize: 14, lineHeight: 22, marginVertical: 12 },
  error: { color: colors.error, fontSize: 14, lineHeight: 22, marginBottom: 12 },
  input: { color: colors.text, backgroundColor: colors.surfaceElevated, borderWidth: 1, borderColor: colors.glassBorder, borderRadius: 14, padding: 14, marginVertical: 8 },
});
