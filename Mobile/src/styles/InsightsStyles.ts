import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";

// Insights screen styles, on the shared Dashboard palette
export const createInsightsStyles = (p: DashboardPalette) =>
  StyleSheet.create({
    // Extra bottom space so the raised centre AI tab never covers content
    content: {
      paddingHorizontal: 18,
      paddingTop: 8,
      paddingBottom: 48,
    },

    // Month selector

    monthSelector: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      backgroundColor: p.card,
      borderRadius: 18,
      borderWidth: 1,
      borderColor: p.border,
      padding: 5,
      marginBottom: 16,
    },

    monthButton: {
      width: 40,
      height: 40,
      borderRadius: 13,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: p.cardRaised,
    },

    monthButtonDisabled: {
      opacity: 0.35,
    },

    monthCenter: {
      alignItems: "center",
      flex: 1,
    },

    monthTitle: {
      color: p.text,
      fontSize: 16,
      fontWeight: "700",
    },

    monthCaption: {
      color: p.textMuted,
      fontSize: 12,
      marginTop: 1,
    },

    // Overview tiles

    tileGrid: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "space-between",
      rowGap: 10,
    },

    tile: {
      width: "48.5%",
      backgroundColor: p.cardRaised,
      borderRadius: 16,
      paddingHorizontal: 14,
      paddingVertical: 12,
    },

    tileLabel: {
      color: p.textMuted,
      fontSize: 12,
      fontWeight: "500",
    },

    tileValue: {
      color: p.text,
      fontSize: 17,
      fontWeight: "700",
      marginTop: 4,
      fontVariant: ["tabular-nums"],
    },

    tileValueMuted: {
      color: p.textMuted,
      fontSize: 14,
      fontWeight: "600",
    },

    tileValueAccent: {
      color: p.accent,
    },

    tileValueDanger: {
      color: p.danger,
    },

    // Trend chart

    chart: {
      flexDirection: "row",
      alignItems: "flex-end",
      justifyContent: "space-between",
      height: 170,
      marginTop: 4,
    },

    barColumn: {
      flex: 1,
      alignItems: "center",
      justifyContent: "flex-end",
      height: "100%",
    },

    barValue: {
      color: p.textMuted,
      fontSize: 11,
      fontWeight: "600",
      marginBottom: 6,
      fontVariant: ["tabular-nums"],
    },

    barValueSelected: {
      color: p.accent,
      fontWeight: "700",
    },

    barTrack: {
      width: 26,
      flex: 1,
      justifyContent: "flex-end",
    },

    bar: {
      width: "100%",
      borderRadius: 8,
      backgroundColor: p.track,
      minHeight: 4,
    },

    barSelected: {
      backgroundColor: p.accent,
    },

    barNoData: {
      backgroundColor: "transparent",
      borderWidth: 1,
      borderColor: p.track,
      borderStyle: "dashed",
      height: 4,
    },

    barLabel: {
      color: p.textMuted,
      fontSize: 12,
      marginTop: 8,
    },

    barLabelSelected: {
      color: p.text,
      fontWeight: "700",
    },

    chartStats: {
      flexDirection: "row",
      gap: 10,
      marginTop: 16,
    },

    chartNote: {
      color: p.textMuted,
      fontSize: 12,
      lineHeight: 17,
      marginTop: 12,
    },

    // Category changes

    sectionHeader: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 10,
      marginTop: 4,
      paddingHorizontal: 2,
    },

    sectionTitle: {
      color: p.text,
      fontSize: 17,
      fontWeight: "700",
      letterSpacing: -0.2,
    },

    sectionCaption: {
      color: p.textMuted,
      fontSize: 12,
    },

    changeCard: {
      backgroundColor: p.card,
      borderRadius: 20,
      borderWidth: 1,
      borderColor: p.border,
      padding: 14,
      marginBottom: 10,
    },

    changeCardFlagged: {
      borderColor: p.warningSoft,
    },

    changeHeader: {
      flexDirection: "row",
      alignItems: "center",
      gap: 12,
    },

    changeText: {
      flex: 1,
      minWidth: 0,
    },

    changeCategory: {
      color: p.text,
      fontSize: 15,
      fontWeight: "700",
    },

    changeAmounts: {
      color: p.textMuted,
      fontSize: 12,
      marginTop: 2,
      fontVariant: ["tabular-nums"],
    },

    changeBadge: {
      flexDirection: "row",
      alignItems: "center",
      gap: 3,
      borderRadius: 999,
      paddingHorizontal: 9,
      paddingVertical: 5,
    },

    changeBadgeText: {
      fontSize: 13,
      fontWeight: "700",
      fontVariant: ["tabular-nums"],
    },

    compareBars: {
      marginTop: 12,
      gap: 6,
    },

    compareRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 8,
    },

    compareLabel: {
      width: 34,
      color: p.textMuted,
      fontSize: 11,
      fontWeight: "600",
    },

    compareTrack: {
      flex: 1,
      height: 6,
      borderRadius: 3,
      backgroundColor: p.track,
      overflow: "hidden",
    },

    compareFill: {
      height: "100%",
      borderRadius: 3,
    },

    flagRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
      marginTop: 10,
    },

    flagText: {
      color: p.textSecondary,
      fontSize: 12,
      fontWeight: "600",
      flex: 1,
    },

    explanation: {
      marginTop: 10,
      paddingTop: 10,
      borderTopWidth: 1,
      borderTopColor: p.border,
    },

    explanationLabel: {
      flexDirection: "row",
      alignItems: "center",
      gap: 5,
      marginBottom: 4,
    },

    explanationLabelText: {
      color: p.accent,
      fontSize: 11,
      fontWeight: "700",
      letterSpacing: 0.8,
      textTransform: "uppercase",
    },

    explanationText: {
      color: p.textSecondary,
      fontSize: 13,
      lineHeight: 19,
    },

    aiNotice: {
      flexDirection: "row",
      alignItems: "center",
      gap: 10,
      backgroundColor: p.card,
      borderRadius: 16,
      borderWidth: 1,
      borderColor: p.border,
      paddingHorizontal: 14,
      paddingVertical: 12,
      marginBottom: 10,
    },

    aiNoticeText: {
      flex: 1,
      color: p.textSecondary,
      fontSize: 13,
      lineHeight: 18,
    },

    // PocketPilot insight

    insightTone: {
      alignSelf: "flex-start",
      flexDirection: "row",
      alignItems: "center",
      gap: 5,
      borderRadius: 999,
      paddingHorizontal: 10,
      paddingVertical: 5,
      marginBottom: 10,
    },

    insightToneText: {
      fontSize: 12,
      fontWeight: "700",
    },

    insightAccent: {
      position: "absolute",
      left: 0,
      top: 18,
      bottom: 18,
      width: 3,
      borderTopRightRadius: 3,
      borderBottomRightRadius: 3,
    },

    insightTitle: {
      color: p.text,
      fontSize: 19,
      fontWeight: "700",
      letterSpacing: -0.3,
      marginBottom: 6,
    },

    insightMessage: {
      color: p.textSecondary,
      fontSize: 14,
      lineHeight: 21,
    },

    insightFigure: {
      color: p.text,
      fontWeight: "700",
    },

    centerCard: {
      alignItems: "center",
    },

    selfStart: {
      alignSelf: "flex-start",
    },

    tileGridSpaced: {
      marginTop: 14,
    },

    overviewHint: {
      marginTop: 12,
    },

    // Skeleton

    skeletonBlock: {
      backgroundColor: p.track,
      borderRadius: 8,
    },

    skeletonLabel: { width: "50%", height: 10 },
    skeletonValue: { width: "75%", height: 16, marginTop: 10 },
    skeletonChip: { width: "35%", height: 22, borderRadius: 11 },
    skeletonTitle: { width: "70%", height: 16, marginTop: 14 },
    skeletonLine: { width: "95%", height: 10, marginTop: 12 },
    skeletonLineShort: { width: "80%", height: 10, marginTop: 8 },
    skeletonBar: { width: 26 },
    skeletonCard: { height: 92, borderRadius: 20, marginBottom: 10 },
  });

export type InsightsStyles = ReturnType<typeof createInsightsStyles>;
