import React from "react";
import { Text, View } from "../../preferences/LocalizedNative";

import { useInsightsTheme } from "./useInsightsTheme";
import { DashboardData, formatAED, formatPercent, monthName } from "../../utils/dashboard";

type Props = {
  data: DashboardData | null;
  loading: boolean;
};

export default function InsightsOverview({ data, loading }: Props) {
  const { styles, ins } = useInsightsTheme();

  if (loading || !data) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardLabel}>Overview</Text>
        <View style={[ins.tileGrid, ins.tileGridSpaced]}>
          {[0, 1, 2, 3].map((index) => (
            <View key={index} style={ins.tile}>
              <View style={[ins.skeletonBlock, ins.skeletonLabel]} />
              <View style={[ins.skeletonBlock, ins.skeletonValue]} />
            </View>
          ))}
        </View>
      </View>
    );
  }

  const today = new Date();
  const isCurrentMonth = data.year === today.getFullYear() && data.month === today.getMonth() + 1;
  const income = data.income;
  const remaining = data.remaining;
  const over = remaining !== null && remaining < 0;

  const tiles = [
    {
      label: "Income",
      value: income === null ? "Not set" : formatAED(income),
      muted: income === null,
    },
    {
      label: "Spent",
      value: formatAED(data.spent),
    },
    {
      label: over ? "Over income by" : "Remaining",
      value: remaining === null ? "Add income" : formatAED(Math.abs(remaining)),
      muted: remaining === null,
      tone: remaining === null ? undefined : over ? ins.tileValueDanger : ins.tileValueAccent,
    },
    {
      label: "Of income spent",
      value: data.spent_percentage === null ? (income === 0 ? "No income" : "Add income") : formatPercent(data.spent_percentage),
      muted: data.spent_percentage === null,
      tone: data.spent_percentage !== null && over ? ins.tileValueDanger : undefined,
    },
  ];

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardLabel}>Overview</Text>
      </View>

      <View style={ins.tileGrid}>
        {tiles.map(({ label, value, muted, tone }) => (
          <View key={label} style={ins.tile}>
            <Text style={ins.tileLabel}>{label}</Text>
            <Text style={[ins.tileValue, muted && ins.tileValueMuted, tone]} adjustsFontSizeToFit numberOfLines={1}>
              {value}
            </Text>
          </View>
        ))}
      </View>

      {data.spent_percentage !== null && (
        <View style={styles.progressTrack}>
          <View
            style={[
              styles.progressFill,
              over && styles.progressFillDanger,
              { width: `${Math.min(100, Math.max(0, data.spent_percentage))}%` },
            ]}
          />
        </View>
      )}

      {income === null && (
        <Text style={[styles.mutedText, ins.overviewHint]}>
          No income recorded for {monthName(data.month)}.
          {isCurrentMonth ? " Add it on the Home tab to see what’s left." : ""}
        </Text>
      )}
    </View>
  );
}
