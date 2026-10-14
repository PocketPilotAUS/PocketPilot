import { StyleSheet } from "react-native";

export type BackButtonColors = { text: string; surface: string; border: string };
export const navigationStyles = StyleSheet.create({
  header: { flexDirection: "row", direction: "ltr", alignItems: "center", gap: 12 },
  toolbar: { flexDirection: "row", direction: "ltr", marginBottom: 24 },
});
export const createBackButtonStyles = (colors: BackButtonColors) => StyleSheet.create({
  button: { width: 44, height: 44, borderRadius: 14, flexShrink: 0, alignItems: "center", justifyContent: "center", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  disabled: { opacity: .5 },
  pressed: { opacity: .7 },
});
