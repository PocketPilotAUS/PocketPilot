import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";

// Add expense screen styles, on the shared Dashboard palette
export const createAddExpenseStyles = (p: DashboardPalette) =>
  StyleSheet.create({
    flex: {
      flex: 1,
    },

    content: {
      paddingHorizontal: 18,
      paddingTop: 8,
      paddingBottom: 20,
    },

    dateChip: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
      backgroundColor: p.card,
      borderWidth: 1,
      borderColor: p.border,
      borderRadius: 999,
      paddingHorizontal: 12,
      paddingVertical: 8,
    },

    dateChipText: {
      color: p.textSecondary,
      fontSize: 13,
      fontWeight: "600",
    },

    // Amount

    amountCard: {
      alignItems: "center",
      paddingVertical: 22,
    },

    amountRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      marginTop: 6,
      maxWidth: "100%",
    },

    currency: {
      color: p.textMuted,
      fontSize: 22,
      fontWeight: "700",
      marginRight: 8,
    },

    amountInput: {
      color: p.text,
      fontWeight: "700",
      letterSpacing: -1,
      maxWidth: "80%",
      paddingVertical: 2,
      textAlign: "center",
      fontVariant: ["tabular-nums"],
    },

    amountHint: {
      color: p.textMuted,
      fontSize: 12,
      marginTop: 6,
    },

    // Category tiles

    grid: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "space-between",
      rowGap: 8,
    },

    tile: {
      width: "23.5%",
      alignItems: "center",
      paddingVertical: 10,
      paddingHorizontal: 2,
      borderRadius: 16,
      borderWidth: 1.5,
      borderColor: "transparent",
      backgroundColor: p.cardRaised,
    },

    tileSelected: {
      borderColor: p.accent,
      backgroundColor: p.accentSoft,
    },

    tileLabel: {
      color: p.textSecondary,
      fontSize: 11,
      fontWeight: "600",
      marginTop: 6,
      textAlign: "center",
    },

    tileLabelSelected: {
      color: p.text,
      fontWeight: "700",
    },

    customField: {
      marginTop: 14,
    },

    // Description

    fieldRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 10,
      backgroundColor: p.card,
      borderRadius: 18,
      borderWidth: 1,
      borderColor: p.border,
      paddingHorizontal: 14,
      marginBottom: 16,
    },

    fieldInput: {
      flex: 1,
      color: p.text,
      fontSize: 15,
      paddingVertical: 15,
    },

    // Repeat monthly

    repeatRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 12,
    },

    repeatIcon: {
      width: 38,
      height: 38,
      borderRadius: 12,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: p.accentSoft,
    },

    repeatText: {
      flex: 1,
    },

    repeatTitle: {
      color: p.text,
      fontSize: 15,
      fontWeight: "700",
    },

    repeatSubtitle: {
      color: p.textMuted,
      fontSize: 12,
      marginTop: 2,
    },

    repeatDetails: {
      marginTop: 14,
      paddingTop: 14,
      borderTopWidth: 1,
      borderTopColor: p.border,
    },

    dayRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
    },

    dayLabel: {
      color: p.textSecondary,
      fontSize: 14,
      fontWeight: "600",
    },

    stepper: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
    },

    stepButton: {
      width: 36,
      height: 36,
      borderRadius: 12,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: p.track,
    },

    dayInput: {
      width: 48,
      color: p.text,
      fontSize: 18,
      fontWeight: "700",
      textAlign: "center",
      paddingVertical: 6,
      fontVariant: ["tabular-nums"],
    },

    repeatNote: {
      color: p.textMuted,
      fontSize: 12,
      lineHeight: 18,
      marginTop: 10,
    },

    // Save footer (sits above the keyboard and the tab bar)

    footer: {
      paddingHorizontal: 18,
      paddingTop: 10,
      paddingBottom: 12,
      backgroundColor: p.background,
      borderTopWidth: 1,
      borderTopColor: p.border,
    },

    saveButton: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 8,
      backgroundColor: p.accent,
      borderRadius: 18,
      paddingVertical: 16,
    },

    saveText: {
      color: p.onAccent,
      fontSize: 16,
      fontWeight: "700",
    },
  });

export type AddExpenseStyles = ReturnType<typeof createAddExpenseStyles>;
