
import { StyleSheet } from "react-native";
import { AppColors } from "../theme/colors";

export const createRegisterStyles = (colors: AppColors) =>
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
      paddingHorizontal: 24,
      paddingTop: 24,
      paddingBottom: 48,
      justifyContent: "center",
    },

    backButton: {
      flexDirection: "row",
      alignItems: "center",
      gap: 8,
      marginBottom: 32,
      alignSelf: "flex-start",
    },

    backText: {
      color: colors.textSecondary,
      fontSize: 14,
    },

    eyebrow: {
      color: colors.primary,
      fontSize: 12,
      fontWeight: "700",
      letterSpacing: 2,
      marginBottom: 12,
    },

    title: {
      color: colors.text,
      fontSize: 34,
      fontWeight: "800",
      letterSpacing: -1,
      marginBottom: 10,
    },

    subtitle: {
      color: colors.textSecondary,
      fontSize: 15,
      lineHeight: 23,
      marginBottom: 28,
    },

    label: {
      color: colors.text,
      fontSize: 13,
      fontWeight: "600",
      marginBottom: 9,
    },

    input: {
      color: colors.text,
      backgroundColor: colors.glassSurface,
      borderColor: colors.border,
      height: 52,
      borderWidth: 1,
      borderRadius: 14,
      paddingHorizontal: 15,
      fontSize: 15,
      marginBottom: 20,
    },

    passwordContainer: {
      backgroundColor: colors.glassSurface,
      borderColor: colors.border,
      height: 52,
      borderWidth: 1,
      borderRadius: 14,
      paddingHorizontal: 15,
      flexDirection: "row",
      alignItems: "center",
      marginBottom: 20,
    },

    passwordInput: {
      color: colors.text,
      flex: 1,
      height: "100%",
      fontSize: 15,
    },

    confirmPasswordInput: {
      color: colors.text,
      backgroundColor: colors.glassSurface,
      borderColor: colors.border,
      height: 52,
      borderWidth: 1,
      borderRadius: 14,
      paddingHorizontal: 15,
      fontSize: 15,
      marginBottom: 0,
    },

    error: {
      color: colors.error,
      fontSize: 13,
      marginTop: 14,
      lineHeight: 19,
    },

    submitContainer: {
      marginTop: 28,
      minHeight: 52,
      justifyContent: "center",
    },

    loginRow: {
      flexDirection: "row",
      justifyContent: "center",
      flexWrap: "wrap",
      marginTop: 30,
    },

    loginPrompt: {
      color: colors.textSecondary,
      fontSize: 14,
    },

    loginLink: {
      color: colors.text,
      fontSize: 14,
      fontWeight: "700",
    },

    demoNote: {
      color: colors.textMuted,
      fontSize: 11,
      textAlign: "center",
      marginTop: 28,
    },
  });
