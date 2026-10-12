import React from "react";
import { ActivityIndicator, Pressable } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import { CircleCheck, CircleX, Receipt, Wallet } from "lucide-react-native";

import { useAITheme } from "./useAITheme";
import type { Proposal } from "../../types/chat";
import { formatAED, monthName } from "../../utils/dashboard";
import { formatLongDate } from "../../utils/transactions";

type Props = {
  proposal: Proposal;
  saving: boolean;
  disabled: boolean;
  onConfirm: () => void;
  onDismiss: () => void;
};

// An expense or income the AI proposed; nothing is saved until confirmed
export default function ProposalCard({ proposal, saving, disabled, onConfirm, onDismiss }: Props) {
  const { ai, styles, palette } = useAITheme();

  const expense = proposal.kind === "expense";
  const Icon = expense ? Receipt : Wallet;

  const detail = expense
    ? `${proposal.category ?? ""}${proposal.date ? ` · ${formatLongDate(proposal.date)}` : ""}`
    : `${proposal.month ? monthName(proposal.month) : ""} ${proposal.year ?? ""} · Replaces income for this month`;

  return (
    <View style={ai.proposal}>
      <View style={ai.proposalHeader}>
        <Icon size={15} color={palette.accent} strokeWidth={2.2} />
        <Text style={ai.proposalKind}>{expense ? "Add expense" : "Set monthly income"}</Text>
      </View>

      <Text style={ai.proposalAmount}>{formatAED(Number(proposal.amount))}</Text>
      <Text style={ai.proposalDetail}>{detail}</Text>

      {proposal.status === "pending" ? (
        <View style={ai.proposalButtons}>
          <Pressable
            onPress={onDismiss}
            disabled={disabled}
            style={[styles.secondaryButton, disabled && styles.buttonDisabled]}
            accessibilityRole="button"
            accessibilityLabel={`Dismiss ${expense ? "expense" : "income"}`}
          >
            <Text style={styles.secondaryButtonText}>Dismiss</Text>
          </Pressable>

          <Pressable
            onPress={onConfirm}
            disabled={disabled}
            style={[styles.primaryButton, disabled && styles.buttonDisabled]}
            accessibilityRole="button"
            accessibilityLabel={`Confirm ${expense ? "expense" : "income"}`}
          >
            {saving ? (
              <ActivityIndicator color={palette.onAccent} />
            ) : (
              <Text style={styles.primaryButtonText}>Confirm</Text>
            )}
          </Pressable>
        </View>
      ) : (
        <View style={ai.proposalStatus}>
          {proposal.status === "saved" ? (
            <CircleCheck size={16} color={palette.accent} strokeWidth={2.2} />
          ) : (
            <CircleX size={16} color={palette.textMuted} strokeWidth={2.2} />
          )}
          <Text style={ai.proposalStatusText}>
            {proposal.status === "saved" ? "Saved to your account" : "Dismissed — nothing saved"}
          </Text>
        </View>
      )}
    </View>
  );
}
