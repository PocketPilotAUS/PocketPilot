import React from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import { ArrowDownRight, ArrowUpRight, CloudOff, Flag, RefreshCw, Sparkles } from "lucide-react-native";

import { useInsightsTheme } from "./useInsightsTheme";
import CategoryIcon from "../transactions/CategoryIcon";
import { formatAED, formatPercent, monthName } from "../../utils/dashboard";
import { AIRecommendation, CategoryChange } from "../../utils/insights";

export type AIState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; items: AIRecommendation[] }
  | { status: "error"; message: string };

type Props = {
  changes: CategoryChange[];
  month: number;
  previousMonth: number;
  ai: AIState;
  onRetryAI: () => void;
};

export default function CategoryChanges({ changes, month, previousMonth, ai, onRetryAI }: Props) {
  const { styles, ins, palette } = useInsightsTheme();

  const flaggedCount = changes.filter((change) => change.recommendation).length;
  const current = monthName(month).slice(0, 3);
  const previous = monthName(previousMonth).slice(0, 3);

  const explanationFor = (category: string) =>
    ai.status === "ready"
      ? ai.items.find((item) => item.category === category)?.ai_explanation?.trim() || null
      : null;

  return (
    <View>
      <View style={ins.sectionHeader}>
        <Text style={ins.sectionTitle}>Category changes</Text>
        <Text style={ins.sectionCaption}>
          {flaggedCount > 0 ? `${flaggedCount} changed by 20% or more` : `vs ${monthName(previousMonth)}`}
        </Text>
      </View>

      {changes.length === 0 ? (
        <View style={[styles.card, ins.centerCard]}>
          <Text style={styles.emptyTitle}>Nothing to compare yet</Text>
          <Text style={styles.emptyText}>
            Record expenses in {monthName(previousMonth)} and {monthName(month)} to see how your categories change.
          </Text>
        </View>
      ) : (
        <>
          {flaggedCount > 0 && ai.status === "error" && (
            <View style={ins.aiNotice} accessibilityRole="alert">
              <CloudOff size={17} color={palette.textMuted} strokeWidth={2.2} />
              <Text style={ins.aiNoticeText}>{ai.message}</Text>
              <Pressable onPress={onRetryAI} style={styles.pill} accessibilityRole="button" accessibilityLabel="Retry AI explanations">
                <RefreshCw size={13} color={palette.accent} strokeWidth={2.4} />
                <Text style={styles.pillText}>Retry</Text>
              </Pressable>
            </View>
          )}

          {changes.map((change) => {
            const max = Math.max(change.current, change.previous, 1);
            const up = change.status === "increase";
            // New, stopped and unchanged (0%) categories are shown neutrally
            const neutral = change.status === "new" || change.status === "stopped" || change.change === 0;
            const badgeColor = neutral ? palette.textSecondary : up ? palette.warning : palette.accent;
            const badgeBackground = neutral ? palette.track : up ? palette.warningSoft : palette.accentSoft;
            const explanation = change.recommendation ? explanationFor(change.category) : null;

            return (
              <View key={change.category} style={[ins.changeCard, change.recommendation && ins.changeCardFlagged]}>
                <View style={ins.changeHeader}>
                  <CategoryIcon category={change.category} />
                  <View style={ins.changeText}>
                    <Text style={ins.changeCategory} numberOfLines={1}>{change.category}</Text>
                    <Text style={ins.changeAmounts} numberOfLines={1}>
                      {formatAED(change.current)} · was {formatAED(change.previous)}
                    </Text>
                  </View>

                  <View style={[ins.changeBadge, { backgroundColor: badgeBackground }]}>
                    {change.change !== null && change.change !== 0 &&
                      (up
                        ? <ArrowUpRight size={14} color={badgeColor} strokeWidth={2.6} />
                        : <ArrowDownRight size={14} color={badgeColor} strokeWidth={2.6} />)}
                    <Text style={[ins.changeBadgeText, { color: badgeColor }]}>
                      {change.change !== null
                        ? `${change.change > 0 ? "+" : ""}${formatPercent(change.change)}`
                        : change.status === "new" ? "New" : "Stopped"}
                    </Text>
                  </View>
                </View>

                <View style={ins.compareBars} accessible accessibilityLabel={`${current} ${formatAED(change.current)}, ${previous} ${formatAED(change.previous)}`}>
                  {[
                    { label: current, value: change.current, color: palette.accent },
                    { label: previous, value: change.previous, color: palette.textMuted },
                  ].map((row) => (
                    <View key={row.label} style={ins.compareRow}>
                      <Text style={ins.compareLabel}>{row.label}</Text>
                      <View style={ins.compareTrack}>
                        <View style={[ins.compareFill, { width: `${(row.value / max) * 100}%`, backgroundColor: row.color }]} />
                      </View>
                    </View>
                  ))}
                </View>

                {change.recommendation && (
                  <>
                    <View style={ins.flagRow}>
                      <Flag size={13} color={change.recommendation.type === "spending_increase" ? palette.warning : palette.accent} strokeWidth={2.4} />
                      <Text style={ins.flagText}>
                        {change.recommendation.type === "spending_increase"
                          ? "Worth reviewing: up 20% or more"
                          : "Spending down 20% or more"}
                      </Text>
                    </View>

                    {(explanation || ai.status === "loading") && (
                      <View style={ins.explanation}>
                        <View style={ins.explanationLabel}>
                          <Sparkles size={12} color={palette.accent} strokeWidth={2.4} />
                          <Text style={ins.explanationLabelText}>AI explanation</Text>
                        </View>
                        {explanation ? (
                          <Text style={ins.explanationText} selectable>{explanation}</Text>
                        ) : (
                          <ActivityIndicator color={palette.accent} style={ins.selfStart} />
                        )}
                      </View>
                    )}
                  </>
                )}
              </View>
            );
          })}
        </>
      )}
    </View>
  );
}
