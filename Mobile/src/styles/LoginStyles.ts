
import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";

export const createLoginStyles = (colors: DashboardPalette) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    keyboardContainer: {
      flex: 1,
    },
    content: {
      flexGrow: 1,
      paddingHorizontal: 18,
      paddingTop: 8,
      paddingBottom: 32,
      justifyContent: "center",
    },
    eyebrow: {
      color: colors.accent,
      fontSize: 12,
      fontWeight: "600",
      letterSpacing: 1.2,
      marginBottom: 4,
    },
    title: {
      color: colors.text,
      fontSize: 30,
      fontWeight: "700",
      letterSpacing: -0.8,
      marginBottom: 10,
    },
    subtitle: {
      color: colors.textSecondary,
      fontSize: 15,
      lineHeight: 22,
      marginBottom: 24,
    },
    label: {
      color: colors.textSecondary,
      fontSize: 13,
      fontWeight: "600",
      marginBottom: 8,
    },
    input: {
      color: colors.text,
      borderColor: colors.border,
      backgroundColor: colors.input,
      minHeight: 52,
      borderWidth: 1,
      borderRadius: 14,
      paddingHorizontal: 14,
      fontSize: 16,
      paddingVertical: 12,
      marginBottom: 20,
    },
    passwordContainer: {
      borderColor: colors.border,
      backgroundColor: colors.input,
      minHeight: 52,
      borderWidth: 1,
      borderRadius: 14,
      paddingLeft: 14,
      paddingRight: 4,
      flexDirection: "row",
      alignItems: "center",
    },
    passwordInput: {
      color: colors.text,
      flex: 1,
      fontSize: 16,
      minWidth: 0,
      paddingVertical: 12,
    },
    visibilityButton: {
      width: 44,
      minHeight: 44,
      alignItems: "center",
      justifyContent: "center",
    },
    error: {
      color: colors.danger,
      fontSize: 13,
      marginTop: 14,
      lineHeight: 19,
      backgroundColor: colors.dangerSoft,
      borderRadius: 14,
      padding: 12,
    },
    submitContainer: {
      marginTop: 24,
      minHeight: 52,
      justifyContent: "center",
    },
    submitButton: {
      flex: 0,
      minHeight: 52,
      justifyContent: "center",
    },
    pressed: {
      opacity: 0.75,
    },
    registerRow: {
      flexDirection: "row",
      justifyContent: "center",
      flexWrap: "wrap",
      marginTop: 8,
    },
    registerPrompt: {
      color: colors.textSecondary,
    },
    registerLink: {
      color: colors.accent,
      fontWeight: "700",
    },
    demoNote: {
      color: colors.textMuted,
      fontSize: 12,
      lineHeight: 18,
      textAlign: "center",
      marginTop: 24,
    },
  });
