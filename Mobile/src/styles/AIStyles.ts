import { StyleSheet } from "react-native";
import type { DashboardPalette } from "./DashboardStyles";

// AI screen styles, on the same palette as the Dashboard and Transactions
export const createAIStyles = (p: DashboardPalette) =>
  StyleSheet.create({
    screen: {
      flex: 1,
      backgroundColor: p.background,
    },

    flex: {
      flex: 1,
    },

    pressed: {
      opacity: 0.6,
    },

    centered: {
      alignSelf: "center",
    },

    retryPill: {
      alignSelf: "flex-start",
      marginTop: 10,
    },

    plansHint: {
      textAlign: "center",
      marginBottom: 12,
    },

    // Header and section switch

    header: {
      paddingHorizontal: 18,
      paddingTop: 8,
      paddingBottom: 12,
    },

    headerRow: {
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 14,
    },

    newChat: {
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

    newChatText: {
      color: p.textSecondary,
      fontSize: 13,
      fontWeight: "600",
    },

    segmented: {
      flexDirection: "row",
      backgroundColor: p.card,
      borderRadius: 16,
      borderWidth: 1,
      borderColor: p.border,
      padding: 4,
    },

    segment: {
      flex: 1,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "center",
      gap: 6,
      paddingVertical: 10,
      borderRadius: 12,
    },

    segmentActive: {
      backgroundColor: p.accentSoft,
    },

    segmentText: {
      color: p.textSecondary,
      fontSize: 14,
      fontWeight: "600",
    },

    segmentTextActive: {
      color: p.accent,
      fontWeight: "700",
    },

    // Conversation

    conversation: {
      paddingHorizontal: 18,
      paddingTop: 4,
      paddingBottom: 16,
      flexGrow: 1,
    },

    // Welcome

    welcome: {
      alignItems: "center",
      paddingTop: 8,
      paddingBottom: 18,
    },

    orb: {
      width: 64,
      height: 64,
      borderRadius: 32,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 14,
    },

    welcomeTitle: {
      color: p.text,
      fontSize: 22,
      fontWeight: "700",
      letterSpacing: -0.4,
      textAlign: "center",
    },

    welcomeText: {
      color: p.textSecondary,
      fontSize: 14,
      lineHeight: 21,
      textAlign: "center",
      marginTop: 6,
      maxWidth: 320,
    },

    suggestionGrid: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "space-between",
      rowGap: 10,
    },

    suggestion: {
      width: "48.5%",
      backgroundColor: p.card,
      borderRadius: 20,
      borderWidth: 1,
      borderColor: p.border,
      padding: 14,
      minHeight: 128,
    },

    suggestionIcon: {
      width: 36,
      height: 36,
      borderRadius: 12,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: p.accentSoft,
      marginBottom: 10,
    },

    suggestionTitle: {
      color: p.text,
      fontSize: 14,
      fontWeight: "700",
    },

    suggestionText: {
      color: p.textMuted,
      fontSize: 12,
      lineHeight: 17,
      marginTop: 4,
    },

    disclaimer: {
      flexDirection: "row",
      alignItems: "flex-start",
      gap: 8,
      marginTop: 16,
      paddingHorizontal: 4,
    },

    disclaimerText: {
      flex: 1,
      color: p.textMuted,
      fontSize: 12,
      lineHeight: 18,
    },

    // Bubbles

    messageRow: {
      flexDirection: "row",
      alignItems: "flex-end",
      gap: 8,
      marginBottom: 12,
    },

    messageRowUser: {
      justifyContent: "flex-end",
    },

    avatar: {
      width: 28,
      height: 28,
      borderRadius: 14,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: p.accentSoft,
    },

    bubble: {
      maxWidth: "84%",
      borderRadius: 20,
      paddingHorizontal: 14,
      paddingVertical: 11,
    },

    userBubble: {
      backgroundColor: p.accent,
      borderBottomRightRadius: 6,
    },

    assistantBubble: {
      backgroundColor: p.card,
      borderWidth: 1,
      borderColor: p.border,
      borderBottomLeftRadius: 6,
      flexShrink: 1,
    },

    userText: {
      color: p.onAccent,
      fontSize: 15,
      lineHeight: 21,
    },

    assistantText: {
      color: p.text,
      fontSize: 15,
      lineHeight: 22,
    },

    bold: {
      fontWeight: "700",
    },

    blockGap: {
      marginTop: 8,
    },

    heading: {
      color: p.text,
      fontSize: 15,
      fontWeight: "700",
    },

    listRow: {
      flexDirection: "row",
      gap: 8,
    },

    listMarker: {
      color: p.accent,
      fontSize: 15,
      lineHeight: 22,
      fontWeight: "700",
      minWidth: 14,
    },

    listText: {
      flex: 1,
    },

    // Typing indicator

    typing: {
      flexDirection: "row",
      alignItems: "center",
      gap: 5,
      paddingVertical: 4,
    },

    dot: {
      width: 7,
      height: 7,
      borderRadius: 4,
      backgroundColor: p.accent,
    },

    typingNote: {
      color: p.textMuted,
      fontSize: 12,
      marginTop: 6,
    },

    // Proposal confirmation

    proposal: {
      marginTop: 12,
      backgroundColor: p.cardRaised,
      borderRadius: 16,
      padding: 12,
    },

    proposalHeader: {
      flexDirection: "row",
      alignItems: "center",
      gap: 8,
    },

    proposalKind: {
      color: p.textSecondary,
      fontSize: 12,
      fontWeight: "700",
      letterSpacing: 0.8,
      textTransform: "uppercase",
    },

    proposalAmount: {
      color: p.text,
      fontSize: 22,
      fontWeight: "700",
      marginTop: 6,
      fontVariant: ["tabular-nums"],
    },

    proposalDetail: {
      color: p.textSecondary,
      fontSize: 13,
      marginTop: 2,
    },

    proposalButtons: {
      flexDirection: "row",
      gap: 8,
      marginTop: 12,
    },

    proposalStatus: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
      marginTop: 10,
    },

    proposalStatusText: {
      color: p.textSecondary,
      fontSize: 13,
      fontWeight: "600",
    },

    // Error

    errorCard: {
      backgroundColor: p.dangerSoft,
      borderRadius: 18,
      padding: 14,
      marginBottom: 12,
    },

    errorHeader: {
      flexDirection: "row",
      alignItems: "center",
      gap: 8,
    },

    errorTitle: {
      color: p.danger,
      fontSize: 14,
      fontWeight: "700",
      flex: 1,
    },

    errorText: {
      color: p.textSecondary,
      fontSize: 13,
      lineHeight: 19,
      marginTop: 4,
    },

    // Composer

    composer: {
      flexDirection: "row",
      alignItems: "flex-end",
      gap: 10,
      paddingHorizontal: 14,
      paddingTop: 10,
      paddingBottom: 10,
      borderTopWidth: 1,
      borderTopColor: p.border,
      backgroundColor: p.background,
    },

    composerInput: {
      flex: 1,
      minHeight: 46,
      maxHeight: 132,
      backgroundColor: p.card,
      borderWidth: 1,
      borderColor: p.border,
      borderRadius: 23,
      paddingHorizontal: 16,
      paddingTop: 13,
      paddingBottom: 13,
      color: p.text,
      fontSize: 15,
      lineHeight: 20,
      textAlignVertical: "top",
    },

    sendButton: {
      width: 46,
      height: 46,
      borderRadius: 23,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: p.accent,
    },

    sendButtonDisabled: {
      backgroundColor: p.track,
    },

    composerNote: {
      color: p.textMuted,
      fontSize: 11,
      textAlign: "center",
      paddingBottom: 6,
      backgroundColor: p.background,
    },

    // Financial plans

    plansContent: {
      paddingHorizontal: 18,
      paddingTop: 4,
      paddingBottom: 32,
    },

    plansHero: {
      alignItems: "center",
      paddingVertical: 8,
    },

    featureList: {
      marginTop: 18,
      gap: 14,
    },

    featureRow: {
      flexDirection: "row",
      alignItems: "flex-start",
      gap: 12,
    },

    featureIcon: {
      width: 36,
      height: 36,
      borderRadius: 12,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: p.cardRaised,
    },

    featureText: {
      flex: 1,
    },

    featureTitle: {
      color: p.text,
      fontSize: 14,
      fontWeight: "700",
    },

    featureDescription: {
      color: p.textMuted,
      fontSize: 13,
      lineHeight: 19,
      marginTop: 2,
    },

    comingSoon: {
      alignSelf: "center",
      backgroundColor: p.accentSoft,
      borderRadius: 999,
      paddingHorizontal: 10,
      paddingVertical: 4,
      marginBottom: 10,
    },

    comingSoonText: {
      color: p.accent,
      fontSize: 11,
      fontWeight: "700",
      letterSpacing: 0.8,
      textTransform: "uppercase",
    },

    planTitle: {
      color: p.text,
      fontSize: 16,
      fontWeight: "700",
    },

    planMeta: {
      flexDirection: "row",
      flexWrap: "wrap",
      gap: 8,
      marginTop: 10,
    },

    planTag: {
      flexDirection: "row",
      alignItems: "center",
      gap: 5,
      backgroundColor: p.cardRaised,
      borderRadius: 999,
      paddingHorizontal: 10,
      paddingVertical: 5,
    },

    planTagText: {
      color: p.textSecondary,
      fontSize: 12,
      fontWeight: "600",
    },

    planCut: {
      flexDirection: "row",
      justifyContent: "space-between",
      marginTop: 6,
    },
  });

export type AIStyles = ReturnType<typeof createAIStyles>;
