import { StyleSheet } from "react-native";
import type { AppColors } from "../theme/colors";
export const createAIChatStyles = (colors: AppColors) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  header: { paddingHorizontal: 22, paddingTop: 16 },
  title: { color: colors.text, fontSize: 30, fontWeight: "700", marginBottom: 8 },
  subtitle: { color: colors.textSecondary, fontSize: 14, lineHeight: 21, marginBottom: 16 },
  conversation: { paddingHorizontal: 22, paddingBottom: 20 },
  heading: { color: colors.text, fontSize: 18, fontWeight: "700" },
  body: { color: colors.textSecondary, fontSize: 15, lineHeight: 23, marginVertical: 12 },
  bubble: { padding: 16, borderRadius: 18, borderWidth: 1, borderColor: colors.glassBorder, marginBottom: 14, maxWidth: "95%" },
  userBubble: { alignSelf: "flex-end", backgroundColor: colors.surfaceElevated },
  assistantBubble: { alignSelf: "flex-start", backgroundColor: colors.glassSurface },
  label: { color: colors.textMuted, fontSize: 11, fontWeight: "600", letterSpacing: 1, marginBottom: 8 },
  message: { color: colors.text, fontSize: 15, lineHeight: 24 },
  composer: { paddingHorizontal: 22, paddingTop: 12, paddingBottom: 8, borderTopWidth: 1, borderTopColor: colors.border },
  input: { color: colors.text, backgroundColor: colors.surfaceElevated, borderColor: colors.glassBorder, borderWidth: 1, borderRadius: 16, padding: 14, fontSize: 15, minHeight: 54, maxHeight: 130, marginBottom: 12, textAlignVertical: "top" },
  error: { color: colors.error, fontSize: 14, lineHeight: 22, marginBottom: 12 },
  note: { color: colors.textMuted, fontSize: 11, textAlign: "center" },
});
