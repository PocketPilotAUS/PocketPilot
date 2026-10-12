import { StyleSheet } from "react-native";
import type { ThemeMode } from "../theme/colors";

// Dashboard-only palette: charcoal surfaces with mint/teal accents.
// Other screens keep the app-wide theme in theme/colors.ts.
const darkPalette = {
  background: "#101214",
  card: "#171A1D",
  cardRaised: "#1E2225",
  border: "rgba(255,255,255,0.06)",
  text: "#F2F5F4",
  textSecondary: "#A0AAA7",
  textMuted: "#6C7673",
  accent: "#4FE3C1",
  accentStrong: "#2CC9A6",
  accentSoft: "rgba(79,227,193,0.12)",
  onAccent: "#04241C",
  track: "#262B2E",
  danger: "#FF7B7B",
  dangerSoft: "rgba(255,123,123,0.12)",
  warning: "#F6C86B",
  warningSoft: "rgba(246,200,107,0.12)",
  input: "#111416",
};

export type DashboardPalette = typeof darkPalette;

const lightPalette: DashboardPalette = {
  background: "#F2F5F4",
  card: "#FFFFFF",
  cardRaised: "#F4F8F7",
  border: "rgba(16,24,22,0.07)",
  text: "#111816",
  textSecondary: "#54605D",
  textMuted: "#87928F",
  accent: "#0E9F83",
  accentStrong: "#0B8A71",
  accentSoft: "rgba(14,159,131,0.10)",
  onAccent: "#FFFFFF",
  track: "#E5ECEA",
  danger: "#D64545",
  dangerSoft: "rgba(214,69,69,0.10)",
  warning: "#B7791F",
  warningSoft: "rgba(183,121,31,0.12)",
  input: "#F2F5F4",
};

// Distinct, harmonious category colours for the donut chart
const darkChartColors = [
  "#4FE3C1", "#5B9DFF", "#B18CFF", "#FF9F6B", "#F6C86B",
  "#FF7EA6", "#7ED957", "#5ED3F3", "#9AA5A3",
] as const;

const lightChartColors = [
  "#12A887", "#3A7BE0", "#8B62E6", "#E5793F", "#C99A1E",
  "#D9527F", "#4FA83A", "#2BA9CC", "#7C8784",
] as const;

export function getDashboardPalette(mode: ThemeMode): DashboardPalette {
  return mode === "dark" ? darkPalette : lightPalette;
}

export function getChartColors(mode: ThemeMode): readonly string[] {
  return mode === "dark" ? darkChartColors : lightChartColors;
}

export const createDashboardStyles = (p: DashboardPalette) =>
  StyleSheet.create({
    screen: {
      flex: 1,
      backgroundColor: p.background,
    },

    content: {
      paddingHorizontal: 18,
      paddingTop: 8,
      paddingBottom: 32,
    },

    // Header

    header: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 20,
    },

    headerText: {
      flex: 1,
      paddingRight: 12,
    },

    eyebrow: {
      color: p.accent,
      fontSize: 12,
      fontWeight: "600",
      letterSpacing: 1.2,
      textTransform: "uppercase",
      marginBottom: 4,
    },

    title: {
      color: p.text,
      fontSize: 30,
      fontWeight: "700",
      letterSpacing: -0.8,
    },

    iconButton: {
      width: 42,
      height: 42,
      borderRadius: 21,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: p.card,
      borderWidth: 1,
      borderColor: p.border,
    },

    errorBanner: {
      flexDirection: "row",
      alignItems: "center",
      gap: 10,
      backgroundColor: p.dangerSoft,
      borderRadius: 16,
      paddingHorizontal: 14,
      paddingVertical: 12,
      marginBottom: 16,
    },

    errorBannerText: {
      color: p.danger,
      fontSize: 13,
      fontWeight: "500",
      flex: 1,
    },

    // Cards

    card: {
      backgroundColor: p.card,
      borderRadius: 24,
      borderWidth: 1,
      borderColor: p.border,
      padding: 20,
      marginBottom: 16,
    },

    cardHeader: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 16,
      gap: 12,
    },

    cardTitleBlock: {
      flex: 1,
    },

    cardLabel: {
      color: p.textSecondary,
      fontSize: 12,
      fontWeight: "600",
      letterSpacing: 1.1,
      textTransform: "uppercase",
    },

    cardSubtitle: {
      color: p.textMuted,
      fontSize: 13,
      marginTop: 3,
    },

    pill: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
      backgroundColor: p.accentSoft,
      borderRadius: 999,
      paddingHorizontal: 12,
      paddingVertical: 8,
    },

    pillText: {
      color: p.accent,
      fontSize: 13,
      fontWeight: "600",
    },

    loader: {
      paddingVertical: 28,
    },

    mutedText: {
      color: p.textMuted,
      fontSize: 13,
      lineHeight: 19,
    },

    // Financial overview

    heroLabel: {
      color: p.textSecondary,
      fontSize: 14,
      fontWeight: "500",
    },

    heroAmount: {
      color: p.text,
      fontSize: 36,
      fontWeight: "700",
      letterSpacing: -1,
      marginTop: 4,
      fontVariant: ["tabular-nums"],
    },

    heroAmountAccent: {
      color: p.accent,
    },

    heroAmountDanger: {
      color: p.danger,
    },

    heroHint: {
      color: p.textMuted,
      fontSize: 13,
      lineHeight: 19,
      marginTop: 6,
    },

    progressTrack: {
      height: 8,
      borderRadius: 4,
      backgroundColor: p.track,
      overflow: "hidden",
      marginTop: 16,
    },

    progressFill: {
      height: "100%",
      borderRadius: 4,
      backgroundColor: p.accent,
    },

    progressFillDanger: {
      backgroundColor: p.danger,
    },

    progressCaption: {
      color: p.textMuted,
      fontSize: 12,
      marginTop: 8,
      fontVariant: ["tabular-nums"],
    },

    statRow: {
      flexDirection: "row",
      gap: 10,
      marginTop: 18,
    },

    statTile: {
      flex: 1,
      backgroundColor: p.cardRaised,
      borderRadius: 16,
      paddingHorizontal: 14,
      paddingVertical: 12,
    },

    statLabel: {
      color: p.textMuted,
      fontSize: 12,
      fontWeight: "500",
    },

    statValue: {
      color: p.text,
      fontSize: 16,
      fontWeight: "700",
      marginTop: 4,
      fontVariant: ["tabular-nums"],
    },

    statValueMuted: {
      color: p.textMuted,
      fontWeight: "600",
    },

    // Forms

    editor: {
      marginTop: 18,
      backgroundColor: p.cardRaised,
      borderRadius: 18,
      padding: 14,
    },

    editorLabel: {
      color: p.textSecondary,
      fontSize: 13,
      fontWeight: "600",
      marginBottom: 8,
    },

    inputRow: {
      flexDirection: "row",
      alignItems: "center",
      backgroundColor: p.input,
      borderRadius: 14,
      borderWidth: 1,
      borderColor: p.border,
      paddingHorizontal: 14,
    },

    inputPrefix: {
      color: p.textMuted,
      fontSize: 15,
      fontWeight: "600",
      marginRight: 8,
    },

    input: {
      flex: 1,
      color: p.text,
      fontSize: 17,
      fontWeight: "600",
      paddingVertical: 12,
      fontVariant: ["tabular-nums"],
    },

    buttonRow: {
      flexDirection: "row",
      gap: 10,
      marginTop: 12,
    },

    primaryButton: {
      flex: 1,
      backgroundColor: p.accent,
      borderRadius: 14,
      paddingVertical: 13,
      alignItems: "center",
    },

    primaryButtonText: {
      color: p.onAccent,
      fontSize: 15,
      fontWeight: "700",
    },

    secondaryButton: {
      flex: 1,
      backgroundColor: p.track,
      borderRadius: 14,
      paddingVertical: 13,
      alignItems: "center",
    },

    secondaryButtonText: {
      color: p.text,
      fontSize: 15,
      fontWeight: "600",
    },

    buttonDisabled: {
      opacity: 0.55,
    },

    formError: {
      color: p.danger,
      fontSize: 13,
      lineHeight: 19,
      marginTop: 10,
    },

    // Spending breakdown

    chartWrap: {
      alignItems: "center",
      justifyContent: "center",
      marginVertical: 6,
    },
    chartDeficit: { color: p.danger, fontSize: 13, lineHeight: 20, marginTop: 8 },

    chartCenter: {
      position: "absolute",
      // Fits inside the donut's inner circle
      width: 124,
      alignItems: "center",
      justifyContent: "center",
    },

    chartCenterLabel: {
      color: p.textMuted,
      fontSize: 12,
      fontWeight: "500",
    },

    chartCenterCurrency: {
      color: p.textSecondary,
      fontSize: 12,
      fontWeight: "600",
      letterSpacing: 0.8,
      marginTop: 6,
    },

    chartCenterValue: {
      color: p.text,
      fontSize: 22,
      fontWeight: "700",
      letterSpacing: -0.4,
      fontVariant: ["tabular-nums"],
    },

    legend: {
      marginTop: 18,
      gap: 12,
    },

    legendRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 10,
    },

    legendDot: {
      width: 10,
      height: 10,
      borderRadius: 5,
    },

    legendName: {
      flex: 1,
      color: p.text,
      fontSize: 14,
      fontWeight: "500",
    },

    legendAmount: {
      color: p.textSecondary,
      fontSize: 13,
      fontVariant: ["tabular-nums"],
    },

    legendPercent: {
      minWidth: 52,
      textAlign: "right",
      color: p.text,
      fontSize: 13,
      fontWeight: "700",
      fontVariant: ["tabular-nums"],
    },

    emptyState: {
      alignItems: "center",
      paddingVertical: 8,
    },

    emptyTitle: {
      color: p.text,
      fontSize: 15,
      fontWeight: "600",
      marginTop: 14,
      textAlign: "center",
    },

    emptyText: {
      color: p.textMuted,
      fontSize: 13,
      lineHeight: 19,
      marginTop: 4,
      textAlign: "center",
    },

    emptyButton: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
      marginTop: 14,
      backgroundColor: p.accent,
      borderRadius: 999,
      paddingHorizontal: 16,
      paddingVertical: 10,
    },

    emptyButtonText: {
      color: p.onAccent,
      fontSize: 14,
      fontWeight: "700",
    },

    // Budget tracker

    budgetList: {
      gap: 14,
    },
    budgetSetupAction: { marginTop: 16, minHeight: 46 },
    budgetReviewButton: { marginTop: 16, minHeight: 46, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, backgroundColor: p.accentSoft, borderRadius: 14, padding: 12 },

    budgetHeaderRow: {
      flexDirection: "row",
      alignItems: "baseline",
      justifyContent: "space-between",
      gap: 10,
    },

    budgetName: {
      flex: 1,
      color: p.text,
      fontSize: 14,
      fontWeight: "600",
    },

    budgetFigures: {
      color: p.textSecondary,
      fontSize: 13,
      fontVariant: ["tabular-nums"],
    },

    budgetFiguresStrong: {
      color: p.text,
      fontWeight: "700",
    },

    budgetTrack: {
      height: 6,
      borderRadius: 3,
      backgroundColor: p.track,
      overflow: "hidden",
      marginTop: 8,
    },

    budgetFill: {
      height: "100%",
      borderRadius: 3,
      backgroundColor: p.accent,
    },

    budgetFillWarning: {
      backgroundColor: p.warning,
    },

    budgetFillDanger: {
      backgroundColor: p.danger,
    },

    overBadge: {
      alignSelf: "flex-start",
      flexDirection: "row",
      alignItems: "center",
      gap: 4,
      backgroundColor: p.dangerSoft,
      borderRadius: 999,
      paddingHorizontal: 8,
      paddingVertical: 3,
      marginTop: 6,
    },

    overBadgeText: {
      color: p.danger,
      fontSize: 12,
      fontWeight: "600",
      fontVariant: ["tabular-nums"],
    },

    statusOk: {
      color: p.accent,
    },

    statusDanger: {
      color: p.danger,
    },

    budgetFooter: {
      marginTop: 16,
      paddingTop: 14,
      borderTopWidth: 1,
      borderTopColor: p.border,
      gap: 6,
    },

    editorIntro: {
      marginBottom: 12,
    },

    trackerHint: {
      marginBottom: 14,
    },

    splitGrid: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "space-between",
      rowGap: 10,
    },

    splitItem: {
      width: "48%",
      flexDirection: "row",
      alignItems: "center",
      backgroundColor: p.input,
      borderRadius: 12,
      borderWidth: 1,
      borderColor: p.border,
      paddingLeft: 12,
      paddingRight: 8,
    },

    splitName: {
      flex: 1,
      color: p.textSecondary,
      fontSize: 13,
    },

    splitInput: {
      width: 40,
      color: p.text,
      fontSize: 15,
      fontWeight: "700",
      textAlign: "right",
      paddingVertical: 10,
      fontVariant: ["tabular-nums"],
    },

    splitPercent: {
      color: p.textMuted,
      fontSize: 13,
      marginLeft: 2,
    },

    splitTotal: {
      color: p.textSecondary,
      fontSize: 13,
      fontWeight: "600",
      marginTop: 12,
      fontVariant: ["tabular-nums"],
    },

    // Insight

    insightCard: {
      borderWidth: 1,
    },

    insightHeader: {
      flexDirection: "row",
      alignItems: "center",
      gap: 10,
      marginBottom: 12,
    },

    insightIcon: {
      width: 34,
      height: 34,
      borderRadius: 17,
      alignItems: "center",
      justifyContent: "center",
    },

    insightTitle: {
      color: p.text,
      fontSize: 17,
      fontWeight: "700",
      letterSpacing: -0.2,
      marginBottom: 6,
    },

    insightMessage: {
      color: p.textSecondary,
      fontSize: 14,
      lineHeight: 21,
    },

    // Footer

    logoutButton: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 8,
      marginTop: 8,
      paddingVertical: 14,
      borderRadius: 16,
      borderWidth: 1,
      borderColor: p.border,
      backgroundColor: p.card,
    },

    logoutText: {
      color: p.textSecondary,
      fontSize: 15,
      fontWeight: "600",
    },
  });

export type DashboardStyles = ReturnType<typeof createDashboardStyles>;
