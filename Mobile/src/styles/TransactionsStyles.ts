import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";

// Transactions screen styles, built on the Dashboard palette so both
// screens share the same colours, radii and typography
export const createTransactionsStyles = (p: DashboardPalette) =>
  StyleSheet.create({
    addButton: {
      flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
      minHeight: 48, backgroundColor: p.accent, borderRadius: 16,
      paddingHorizontal: 16, paddingVertical: 12, marginBottom: 18,
    },
    addButtonText: { color: p.onAccent, fontSize: 15, fontWeight: "700" },
    // Summary

    summaryRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 12,
    },

    summaryAmount: {
      color: p.text,
      fontSize: 30,
      fontWeight: "700",
      letterSpacing: -0.8,
      marginTop: 4,
      fontVariant: ["tabular-nums"],
    },

    countBadge: {
      backgroundColor: p.accentSoft,
      borderRadius: 999,
      paddingHorizontal: 12,
      paddingVertical: 6,
    },

    countText: {
      color: p.accent,
      fontSize: 13,
      fontWeight: "700",
      fontVariant: ["tabular-nums"],
    },

    summaryCaption: {
      color: p.textMuted,
      fontSize: 12,
      marginTop: 10,
    },

    // Search

    searchBar: {
      flexDirection: "row",
      alignItems: "center",
      gap: 10,
      backgroundColor: p.card,
      borderRadius: 16,
      borderWidth: 1,
      borderColor: p.border,
      paddingHorizontal: 14,
      marginBottom: 12,
    },

    searchInput: {
      flex: 1,
      color: p.text,
      fontSize: 15,
      paddingVertical: 12,
    },

    // Filter chips

    chipScroll: {
      marginHorizontal: -18,
      marginBottom: 18,
    },

    chipRow: {
      paddingHorizontal: 18,
      gap: 8,
    },

    chip: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
      backgroundColor: p.card,
      borderRadius: 999,
      borderWidth: 1,
      borderColor: p.border,
      paddingHorizontal: 13,
      paddingVertical: 8,
    },

    chipActive: {
      backgroundColor: p.accentSoft,
      borderColor: p.accent,
    },

    chipText: {
      color: p.textSecondary,
      fontSize: 13,
      fontWeight: "600",
    },

    chipTextActive: {
      color: p.accent,
    },

    // Groups and rows

    groupHeader: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
      paddingHorizontal: 4,
      marginBottom: 8,
      marginTop: 4,
    },

    groupTitle: {
      color: p.textSecondary,
      fontSize: 13,
      fontWeight: "700",
    },

    groupTotal: {
      color: p.textMuted,
      fontSize: 12,
      fontWeight: "600",
      fontVariant: ["tabular-nums"],
    },

    groupCard: {
      backgroundColor: p.card,
      borderRadius: 20,
      borderWidth: 1,
      borderColor: p.border,
      paddingHorizontal: 14,
      marginBottom: 16,
    },

    row: {
      flexDirection: "row",
      alignItems: "center",
      gap: 12,
      paddingVertical: 12,
    },

    rowDivider: {
      borderTopWidth: 1,
      borderTopColor: p.border,
    },

    rowPressed: {
      opacity: 0.6,
    },

    categoryIcon: {
      width: 40,
      height: 40,
      borderRadius: 13,
      alignItems: "center",
      justifyContent: "center",
    },

    rowText: {
      flex: 1,
      minWidth: 0,
    },

    rowTitle: {
      color: p.text,
      fontSize: 15,
      fontWeight: "600",
    },

    rowSubtitle: {
      color: p.textMuted,
      fontSize: 13,
      marginTop: 2,
    },

    rowAmount: {
      color: p.text,
      fontSize: 15,
      fontWeight: "700",
      fontVariant: ["tabular-nums"],
    },

    // States

    skeletonRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 12,
      paddingVertical: 12,
    },

    skeletonIcon: {
      width: 40,
      height: 40,
      borderRadius: 13,
      backgroundColor: p.track,
    },

    skeletonLines: {
      flex: 1,
      gap: 8,
    },

    skeletonLine: {
      height: 10,
      borderRadius: 5,
      backgroundColor: p.track,
    },

    skeletonLineShort: {
      width: "45%",
    },

    skeletonLineLong: {
      width: "70%",
    },

    skeletonAmount: {
      width: 64,
      height: 12,
      borderRadius: 6,
      backgroundColor: p.track,
    },

    stateCard: {
      alignItems: "center",
      paddingVertical: 28,
    },

    stateIcon: {
      width: 52,
      height: 52,
      borderRadius: 26,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: p.accentSoft,
    },

    stateIconDanger: {
      backgroundColor: p.dangerSoft,
    },

    secondaryPill: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
      marginTop: 14,
      backgroundColor: p.track,
      borderRadius: 999,
      paddingHorizontal: 16,
      paddingVertical: 10,
    },

    secondaryPillText: {
      color: p.text,
      fontSize: 14,
      fontWeight: "600",
    },

    recurringSection: {
      marginTop: 8,
    },

    // Bottom sheets

    sheetBackdrop: {
      flex: 1,
      backgroundColor: "rgba(0,0,0,0.55)",
      justifyContent: "flex-end",
    },

    sheetDismissArea: {
      flex: 1,
    },

    sheet: {
      backgroundColor: p.card,
      borderTopLeftRadius: 28,
      borderTopRightRadius: 28,
      paddingHorizontal: 20,
      paddingTop: 10,
      maxHeight: "88%",
    },

    sheetHandle: {
      alignSelf: "center",
      width: 40,
      height: 5,
      borderRadius: 3,
      backgroundColor: p.track,
      marginBottom: 14,
    },

    sheetHeader: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 14,
    },

    sheetTitle: {
      color: p.text,
      fontSize: 19,
      fontWeight: "700",
      letterSpacing: -0.3,
    },

    sheetClose: {
      width: 34,
      height: 34,
      borderRadius: 17,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: p.track,
    },

    optionRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      paddingVertical: 14,
      borderBottomWidth: 1,
      borderBottomColor: p.border,
    },

    optionText: {
      color: p.text,
      fontSize: 15,
      fontWeight: "500",
    },

    optionTextSelected: {
      color: p.accent,
      fontWeight: "700",
    },

    segmented: {
      flexDirection: "row",
      backgroundColor: p.track,
      borderRadius: 14,
      padding: 4,
      marginBottom: 14,
    },

    segment: {
      flex: 1,
      alignItems: "center",
      paddingVertical: 9,
      borderRadius: 11,
    },

    segmentActive: {
      backgroundColor: p.card,
    },

    segmentText: {
      color: p.textSecondary,
      fontSize: 13,
      fontWeight: "600",
    },

    segmentTextActive: {
      color: p.text,
    },

    amountInputs: {
      flexDirection: "row",
      gap: 10,
    },

    amountField: {
      flex: 1,
    },

    // Calendar

    calendar: {
      backgroundColor: p.cardRaised,
      borderRadius: 18,
      padding: 12,
      marginTop: 6,
    },

    calendarHeader: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 8,
    },

    calendarNav: {
      width: 34,
      height: 34,
      borderRadius: 17,
      alignItems: "center",
      justifyContent: "center",
    },

    calendarNavDisabled: {
      opacity: 0.3,
    },

    calendarMonth: {
      color: p.text,
      fontSize: 15,
      fontWeight: "700",
    },

    weekRow: {
      flexDirection: "row",
    },

    weekday: {
      flex: 1,
      textAlign: "center",
      color: p.textMuted,
      fontSize: 11,
      fontWeight: "600",
      paddingVertical: 6,
    },

    dayCell: {
      flex: 1,
      aspectRatio: 1,
      alignItems: "center",
      justifyContent: "center",
    },

    dayInRange: {
      backgroundColor: p.accentSoft,
    },

    dayRangeStart: {
      borderTopLeftRadius: 999,
      borderBottomLeftRadius: 999,
    },

    dayRangeEnd: {
      borderTopRightRadius: 999,
      borderBottomRightRadius: 999,
    },

    dayBubble: {
      width: 34,
      height: 34,
      borderRadius: 17,
      alignItems: "center",
      justifyContent: "center",
    },

    dayBubbleSelected: {
      backgroundColor: p.accent,
    },

    dayText: {
      color: p.text,
      fontSize: 14,
      fontVariant: ["tabular-nums"],
    },

    dayTextMuted: {
      color: p.textMuted,
    },

    dayTextSelected: {
      color: p.onAccent,
      fontWeight: "700",
    },

    dayTextToday: {
      color: p.accent,
      fontWeight: "700",
    },

    rangeSummary: {
      color: p.textSecondary,
      fontSize: 13,
      marginTop: 10,
      textAlign: "center",
    },

    // Detail

    detailHero: {
      alignItems: "center",
      paddingVertical: 8,
    },

    detailIcon: {
      width: 60,
      height: 60,
      borderRadius: 20,
      alignItems: "center",
      justifyContent: "center",
    },

    detailCategory: {
      color: p.textSecondary,
      fontSize: 15,
      fontWeight: "600",
      marginTop: 12,
    },

    detailAmount: {
      color: p.text,
      fontSize: 34,
      fontWeight: "700",
      letterSpacing: -0.8,
      marginTop: 4,
      fontVariant: ["tabular-nums"],
    },

    detailList: {
      backgroundColor: p.cardRaised,
      borderRadius: 18,
      paddingHorizontal: 16,
      marginTop: 18,
    },

    detailRow: {
      paddingVertical: 13,
    },

    detailLabel: {
      color: p.textMuted,
      fontSize: 12,
      fontWeight: "600",
      letterSpacing: 0.6,
      textTransform: "uppercase",
    },

    detailValue: {
      color: p.text,
      fontSize: 15,
      marginTop: 4,
      lineHeight: 21,
    },

    deleteButton: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 8,
      backgroundColor: p.dangerSoft,
      borderRadius: 16,
      paddingVertical: 15,
      marginTop: 18,
    },

    deleteText: {
      color: p.danger,
      fontSize: 15,
      fontWeight: "700",
    },
  });

export type TransactionsStyles = ReturnType<typeof createTransactionsStyles>;
