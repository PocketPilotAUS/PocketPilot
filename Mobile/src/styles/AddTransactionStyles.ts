
import { StyleSheet } from "react-native";
import { AppColors } from "../theme/colors";

export const createAddTransactionStyles = (colors: AppColors) =>
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
      minWidth: 110,
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

    label: {
      color: colors.textSecondary,
      fontSize: 14,
      fontWeight: "600",
      marginBottom: 10,
      marginTop: 14,
    },

    input: {
      backgroundColor: colors.glassSurface,
      color: colors.text,
      borderWidth: 1,
      borderColor: colors.glassBorder,
      paddingHorizontal: 16,
      paddingVertical: 15,
      borderRadius: 14,
      fontSize: 16,
      marginBottom: 16,
    },

    categories: {
      flexDirection: "row",
      flexWrap: "wrap",
      gap: 10,
      marginBottom: 16,
    },

    categoryButton: {
      backgroundColor: colors.glassSurface,
      borderWidth: 1,
      borderColor: colors.glassBorder,
      borderRadius: 12,
      paddingVertical: 12,
      paddingHorizontal: 15,
      alignItems: "center",
      justifyContent: "center",
    },

    selectedCategory: {
      backgroundColor: colors.primary,
      borderColor: colors.primary,
    },

    categoryText: {
      color: colors.textSecondary,
      fontSize: 14,
      fontWeight: "500",
    },

    selectedCategoryText: {
      color: colors.primaryText,
      fontWeight: "700",
    },
  });
