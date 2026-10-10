import React from "react";
import { Pressable, Text, View } from "react-native";

import { useInsightsTheme } from "./useInsightsTheme";
import { formatAED, formatPercent, monthName } from "../../utils/dashboard";
import { TrendMonth, compactAED, trendStats } from "../../utils/insights";

type Props = {
  months: TrendMonth[];
  loading: boolean;
  error: boolean;
  onSelect: (year: number, month: number) => void;
};

export default function SpendingTrend({ months, loading, error, onSelect }: Props) {
  const { styles, ins } = useInsightsTheme();

  const selected = months[months.length - 1];
  const stats = trendStats(months);
  const max = Math.max(0, ...months.filter((month) => month.hasData).map((month) => month.total));
  const anyNoData = months.some((month) => !month.hasData);

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardTitleBlock}>
          <Text style={styles.cardLabel}>Spending trend</Text>
          <Text style={styles.cardSubtitle}>Last 6 months · tap a month to view it</Text>
        </View>
      </View>

      {loading ? (
        <View style={ins.chart}>
          {[40, 70, 55, 90, 60, 80].map((height, index) => (
            <View key={index} style={ins.barColumn}>
              <View style={[ins.skeletonBlock, ins.skeletonBar, { height: `${height}%` }]} />
            </View>
          ))}
        </View>
      ) : error ? (
        <Text style={styles.mutedText}>Your spending trend couldn’t be loaded. Pull down to try again.</Text>
      ) : stats.monthsWithData === 0 ? (
        <Text style={styles.mutedText}>
          No expenses recorded yet. Your monthly trend will appear here as you add expenses.
        </Text>
      ) : (
        <>
          <View style={ins.chart} accessible accessibilityLabel={`Monthly spending: ${months
            .map((month) => `${monthName(month.month)} ${month.hasData ? formatAED(month.total) : "no data"}`)
            .join(", ")}`}
          >
            {months.map((month) => {
              const isSelected = month.key === selected.key;
              const height = max > 0 ? (month.total / max) * 100 : 0;

              return (
                <Pressable
                  key={month.key}
                  onPress={() => onSelect(month.year, month.month)}
                  style={ins.barColumn}
                  accessibilityRole="button"
                  accessibilityLabel={`View ${monthName(month.month)} ${month.year}`}
                >
                  <Text style={[ins.barValue, isSelected && ins.barValueSelected]}>
                    {month.hasData ? compactAED(month.total) : "—"}
                  </Text>
                  <View style={ins.barTrack}>
                    <View
                      style={[
                        ins.bar,
                        month.hasData ? { height: `${height}%` } : ins.barNoData,
                        month.hasData && isSelected && ins.barSelected,
                      ]}
                    />
                  </View>
                  <Text style={[ins.barLabel, isSelected && ins.barLabelSelected]}>{month.label}</Text>
                </Pressable>
              );
            })}
          </View>

          <View style={ins.chartStats}>
            <View style={ins.tile}>
              <Text style={ins.tileLabel}>Monthly average</Text>
              <Text style={ins.tileValue} adjustsFontSizeToFit numberOfLines={1}>
                {stats.average === null ? "—" : formatAED(stats.average)}
              </Text>
            </View>
            <View style={ins.tile}>
              <Text style={ins.tileLabel}>vs {monthName(months[months.length - 2].month)}</Text>
              <Text
                style={[
                  ins.tileValue,
                  stats.change === null && ins.tileValueMuted,
                  stats.change !== null && (stats.change > 0 ? ins.tileValueDanger : ins.tileValueAccent),
                ]}
                numberOfLines={1}
              >
                {stats.change === null ? "Not comparable" : `${stats.change > 0 ? "+" : ""}${formatPercent(stats.change)}`}
              </Text>
            </View>
          </View>

          <Text style={ins.chartNote}>
            Average of the {stats.monthsWithData} {stats.monthsWithData === 1 ? "month" : "months"} with recorded data.
            {anyNoData ? " Dashed bars are before your first recorded expense." : ""}
          </Text>
        </>
      )}
    </View>
  );
}
