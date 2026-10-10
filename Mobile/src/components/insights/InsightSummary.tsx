import React from "react";
import { Text, View } from "react-native";
import { CircleAlert, Sparkles, TrendingUp, TriangleAlert, Wallet } from "lucide-react-native";

import { useInsightsTheme } from "./useInsightsTheme";
import { DashboardData, InsightTone, buildInsight } from "../../utils/dashboard";

type Props = {
  data: DashboardData | null;
  loading: boolean;
};

// AED amounts and percentages inside the message are shown in bold
const FIGURE = /(-?AED [\d,]+\.\d{2}|\d+(?:\.\d+)?%)/g;

export default function InsightSummary({ data, loading }: Props) {
  const { styles, ins, palette } = useInsightsTheme();

  // Same calculation as before (utils/dashboard.ts)
  const insight = buildInsight(data, new Date());

  const tones: Record<InsightTone, { label: string; color: string; background: string; Icon: typeof Sparkles }> = {
    danger: { label: "Needs attention", color: palette.danger, background: palette.dangerSoft, Icon: CircleAlert },
    warning: { label: "Heads up", color: palette.warning, background: palette.warningSoft, Icon: TriangleAlert },
    positive: { label: "On track", color: palette.accent, background: palette.accentSoft, Icon: TrendingUp },
    neutral: { label: "Overview", color: palette.accent, background: palette.accentSoft, Icon: Wallet },
  };

  const tone = insight ? tones[insight.tone] : null;

  return (
    <View style={styles.card}>
      {tone && <View style={[ins.insightAccent, { backgroundColor: tone.color }]} />}

      <View style={styles.cardHeader}>
        <View style={styles.insightHeader}>
          <View style={[styles.insightIcon, { backgroundColor: palette.accentSoft }]}>
            <Sparkles size={16} color={palette.accent} strokeWidth={2.2} />
          </View>
          <Text style={styles.cardLabel}>PocketPilot insight</Text>
        </View>
      </View>

      {loading ? (
        <View>
          <View style={[ins.skeletonBlock, ins.skeletonChip]} />
          <View style={[ins.skeletonBlock, ins.skeletonTitle]} />
          <View style={[ins.skeletonBlock, ins.skeletonLine]} />
          <View style={[ins.skeletonBlock, ins.skeletonLineShort]} />
        </View>
      ) : insight && tone ? (
        <View accessible accessibilityLabel={`${tone.label}. ${insight.title}. ${insight.message}`}>
          <View style={[ins.insightTone, { backgroundColor: tone.background }]}>
            <tone.Icon size={13} color={tone.color} strokeWidth={2.4} />
            <Text style={[ins.insightToneText, { color: tone.color }]}>{tone.label}</Text>
          </View>

          <Text style={ins.insightTitle}>{insight.title}</Text>

          <Text style={ins.insightMessage}>
            {insight.message.split(FIGURE).map((part, index) =>
              index % 2 === 1 ? (
                <Text key={index} style={ins.insightFigure}>{part}</Text>
              ) : (
                part
              )
            )}
          </Text>
        </View>
      ) : (
        <>
          <Text style={ins.insightTitle}>Not enough data yet</Text>
          <Text style={ins.insightMessage}>
            Add your monthly income and record a few expenses. PocketPilot will then highlight the
            one thing that matters most for your budget.
          </Text>
        </>
      )}
    </View>
  );
}
