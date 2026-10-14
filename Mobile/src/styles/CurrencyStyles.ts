import { StyleSheet } from "react-native";
import type { AppColors } from "../theme/colors";
export const createCurrencyStyles = (colors: AppColors) => StyleSheet.create({
  notice: { paddingHorizontal: 18, paddingVertical: 5, alignItems: "center", gap: 2 },
  text: { color: colors.textMuted, fontSize: 10, textAlign: "center" },
  link: { color: colors.primary, fontSize: 10, paddingVertical: 2, textDecorationLine: "underline" },
});
