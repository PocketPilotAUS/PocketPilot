import { StyleSheet } from "react-native";
import type { AppColors } from "../theme/colors";

export const createAIInsightsStyles = (colors: AppColors) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { paddingHorizontal: 22, paddingTop: 20, paddingBottom: 60 },
  backButton: { alignSelf: "flex-start", minWidth: 190, marginBottom: 24 },
  title: { color: colors.text, fontSize: 30, fontWeight: "700", letterSpacing: -0.7, marginBottom: 8 },
  subtitle: { color: colors.textSecondary, fontSize: 15, lineHeight: 23, marginBottom: 28 },
  month: { color: colors.text, fontSize: 21, fontWeight: "700" },
  caption: { color: colors.textMuted, fontSize: 13, lineHeight: 20, marginTop: 8 },
  controls: { flexDirection: "row", gap: 12, marginTop: 18 },
  control: { flex: 1, minWidth: 0 },
  heading: { color: colors.text, fontSize: 18, fontWeight: "700", marginBottom: 6 },
  body: { color: colors.textSecondary, fontSize: 15, lineHeight: 24, marginTop: 12 },
  explanation: { borderTopWidth: 1, borderTopColor: colors.border, marginTop: 20, paddingTop: 16 },
  label: { color: colors.primary, fontSize: 12, fontWeight: "600", letterSpacing: 1 },
  loading: { color: colors.textSecondary, fontSize: 15, lineHeight: 23, textAlign: "center", marginTop: 16 },
  error: { color: colors.error, fontSize: 15, lineHeight: 23, marginBottom: 18 },
});
