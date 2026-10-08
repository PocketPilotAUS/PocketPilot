
import { StyleSheet } from "react-native";
import type { AppColors } from "../theme/colors";

export const createTransactionHistoryStyles = (colors: AppColors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },

    content: {
      paddingHorizontal: 22,
      paddingTop: 20,
      paddingBottom: 60,
    },

    backButton: {
      alignSelf: "flex-start",
      minWidth: 190,
      marginBottom: 24,
    },

    title: {
      color: colors.text,
      fontSize: 30,
      fontWeight: "700",
      letterSpacing: -0.7,
      marginBottom: 8,
    },

    subtitle: {
      color: colors.textSecondary,
      fontSize: 15,
      marginBottom: 28,
    },

    row: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "flex-start",
    },

    details: {
      flex: 1,
      paddingRight: 12,
    },

    category: {
      color: colors.text,
      fontSize: 17,
      fontWeight: "700",
      marginBottom: 6,
    },

    description: {
      color: colors.textSecondary,
      fontSize: 14,
      marginBottom: 8,
    },

    date: {
      color: colors.textMuted,
      fontSize: 12,
    },

    amount: {
      color: colors.text,
      fontSize: 17,
      fontWeight: "700",
      textAlign: "right",
    },

    empty: {
      color: colors.textSecondary,
      fontSize: 15,
      textAlign: "center",
      lineHeight: 23,
    },

    error: {
      color: colors.error,
      fontSize: 15,
      lineHeight: 23,
    },

    deleteButtonContainer: {
      marginTop: 18,
      paddingTop: 16,
      borderTopWidth: 1,
      borderTopColor: colors.border,
      alignItems: "flex-end",
    },

    deleteButton: {
      minWidth: 160,
      marginBottom: 0,
    },
  });
