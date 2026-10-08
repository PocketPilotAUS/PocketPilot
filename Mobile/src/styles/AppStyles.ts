import { StyleSheet } from "react-native";
import type { AppColors } from "../theme/colors";

export const createAppStyles = (colors: AppColors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },

    // Welcome screen

    welcomeContent: {
      flex: 1,
      justifyContent: "center",
      alignItems: "center",
      paddingHorizontal: 30,
    },

    welcomeLogoCard: {
      width: 100,
      height: 100,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 30,
    },

    welcomeLogoText: {
      color: colors.text,
      fontSize: 44,
      fontWeight: "800",
      letterSpacing: -2,
      textAlign: "center",
    },

    welcomeButtonContainer: {
      width: "100%",
      maxWidth: 320,
    },

    logo: {
      width: 90,
      height: 90,
      backgroundColor: colors.primary,
      borderRadius: 25,
      justifyContent: "center",
      alignItems: "center",
      marginBottom: 25,
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    logoText: {
      fontSize: 52,
      fontWeight: "bold",
      color: colors.primaryText,
    },

    title: {
      fontSize: 36,
      fontWeight: "bold",
      color: colors.text,
      marginBottom: 10,
    },

    subtitle: {
      fontSize: 18,
      color: colors.textSecondary,
      marginBottom: 25,
      textAlign: "center",
    },

    description: {
      fontSize: 16,
      color: colors.textSecondary,
      textAlign: "center",
      lineHeight: 25,
      marginBottom: 40,
    },

    button: {
      backgroundColor: colors.primary,
      paddingVertical: 16,
      paddingHorizontal: 55,
      borderRadius: 14,
      alignItems: "center",
      borderWidth: 1,
      borderColor: colors.glassBorder,
    },

    buttonText: {
      color: colors.primaryText,
      fontSize: 17,
      fontWeight: "bold",
    },

    // Dashboard layout

    dashboard: {
      paddingHorizontal: 22,
      paddingTop: 20,
      paddingBottom: 60,
    },

    headerRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 26,
    },

    headerText: {
      flex: 1,
      paddingRight: 12,
    },

    greeting: {
      color: colors.textSecondary,
      fontSize: 11,
      fontWeight: "600",
      letterSpacing: 1.4,
      marginBottom: 7,
    },

    heading: {
      color: colors.text,
      fontSize: 32,
      fontWeight: "700",
      letterSpacing: -0.8,
    },

    themeToggle: {
      backgroundColor: colors.surfaceElevated,
      borderWidth: 1,
      borderColor: colors.glassBorder,
      width: 44,
      height: 44,
      borderRadius: 22,
      alignItems: "center",
      justifyContent: "center",
    },

    // Financial cards

    card: {
      backgroundColor: colors.surface,
      padding: 22,
      borderRadius: 18,
      marginBottom: 20,
      borderWidth: 1,
      borderColor: colors.border,
    },

    cardLabel: {
      color: colors.textSecondary,
      fontSize: 13,
      fontWeight: "500",
      letterSpacing: 0.3,
    },

    amount: {
      color: colors.text,
      fontSize: 36,
      fontWeight: "700",
      letterSpacing: -1,
      marginTop: 12,
    },

    cardHint: {
      color: colors.textMuted,
      fontSize: 12,
      marginTop: 8,
    },

    sectionTitle: {
      color: colors.text,
      fontSize: 19,
      fontWeight: "700",
      letterSpacing: -0.3,
      marginBottom: 15,
      marginTop: 12,
    },

    emptyText: {
      color: colors.textSecondary,
      fontSize: 15,
      lineHeight: 23,
    },

    // Quick actions

    quickActions: {
      flexDirection: "row",
      gap: 12,
      marginBottom: 14,
    },

    quickActionItem: {
      flex: 1,
      minWidth: 0,
    },

    // Category breakdown

    categoryRow: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
      gap: 10,
    },

    categoryAmount: {
      color: colors.text,
      fontSize: 14,
      fontWeight: "600",
    },

    progressTrack: {
      height: 7,
      borderRadius: 4,
      backgroundColor: colors.surfaceElevated,
      overflow: "hidden",
      marginTop: 12,
    },

    progressFill: {
      height: "100%",
      borderRadius: 4,
      backgroundColor: colors.primary,
    },

    // Navigation

    secondaryButton: {
      padding: 16,
      alignItems: "center",
      marginTop: 4,
    },

    secondaryButtonText: {
      color: colors.textSecondary,
      fontSize: 14,
      fontWeight: "600",
    },

    // Older button styles retained for compatibility

    addTransactionButton: {
      marginBottom: 20,
    },

    historyButton: {
      backgroundColor: colors.surface,
      paddingVertical: 16,
      paddingHorizontal: 20,
      borderRadius: 14,
      alignItems: "center",
      marginBottom: 25,
      borderWidth: 1,
      borderColor: colors.border,
    },

    historyButtonText: {
      color: colors.text,
      fontSize: 16,
      fontWeight: "600",
    },

    sessionLoader: {
      flex: 1,
      justifyContent: "center",
      alignItems: "center",
    },

    logoutContainer: {
      marginTop: 28,
      marginBottom: 12,
    },
  });
