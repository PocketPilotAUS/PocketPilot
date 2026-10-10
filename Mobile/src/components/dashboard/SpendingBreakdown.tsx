import React from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import Svg, { Circle, G } from "react-native-svg";
import { Plus } from "lucide-react-native";

import { useDashboardTheme } from "./useDashboardTheme";
import {
  DashboardData,
  Slice,
  buildSlices,
  formatAED,
  formatAmount,
  formatPercent,
  monthName,
} from "../../utils/dashboard";

const SIZE = 184;
const STROKE = 20;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const GAP = 3;

type Props = {
  data: DashboardData | null;
  loading: boolean;
  onAddExpense: () => void;
};

function Donut({ slices, track }: { slices: Slice[]; track: string }) {
  const gap = slices.length > 1 ? GAP : 0;
  const lengths = slices.map((slice) => (slice.percentage / 100) * CIRCUMFERENCE);
  // Where each slice starts along the circle
  const starts = lengths.map((_, index) =>
    lengths.slice(0, index).reduce((sum, length) => sum + length, 0)
  );

  return (
    <Svg width={SIZE} height={SIZE}>
      {/* Rotate so the first slice starts at 12 o'clock */}
      <G rotation={-90} origin={`${SIZE / 2}, ${SIZE / 2}`}>
        <Circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          stroke={track}
          strokeWidth={STROKE}
          fill="none"
        />
        {slices.map((slice, index) => {
          // Very small categories stay visible as a thin sliver
          const visible = Math.max(lengths[index] - gap, 0.75);

          return (
            <Circle
              key={slice.label}
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={RADIUS}
              stroke={slice.color}
              strokeWidth={STROKE}
              strokeDasharray={`${visible} ${CIRCUMFERENCE}`}
              strokeDashoffset={-starts[index]}
              strokeLinecap="butt"
              fill="none"
            />
          );
        })}
      </G>
    </Svg>
  );
}

export default function SpendingBreakdown({ data, loading, onAddExpense }: Props) {
  const { styles, palette, chartColors } = useDashboardTheme();

  const slices = data ? buildSlices(data.category_spending, chartColors) : [];
  const total = slices.reduce((sum, slice) => sum + slice.amount, 0);
  const month = data ? monthName(data.month) : "";

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardTitleBlock}>
          <Text style={styles.cardLabel}>Spending breakdown</Text>
          {data && <Text style={styles.cardSubtitle}>By category · {month}</Text>}
        </View>
      </View>

      {loading && !data ? (
        <ActivityIndicator color={palette.accent} style={styles.loader} />
      ) : slices.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.chartWrap}>
            <Donut slices={[]} track={palette.track} />
            <View style={styles.chartCenter}>
              <Text style={styles.chartCenterLabel}>Total spent</Text>
              <Text style={styles.chartCenterCurrency}>AED</Text>
              <Text style={styles.chartCenterValue}>{formatAmount(0)}</Text>
            </View>
          </View>

          <Text style={styles.emptyTitle}>No expenses yet{month ? ` for ${month}` : ""}</Text>
          <Text style={styles.emptyText}>
            Your spending by category appears here once you record an expense.
          </Text>

          <Pressable
            onPress={onAddExpense}
            style={({ pressed }) => [styles.emptyButton, pressed && styles.buttonDisabled]}
            accessibilityRole="button"
          >
            <Plus size={15} color={palette.onAccent} strokeWidth={2.6} />
            <Text style={styles.emptyButtonText}>Add an expense</Text>
          </Pressable>
        </View>
      ) : (
        <>
          <View
            style={styles.chartWrap}
            accessible
            accessibilityLabel={`Spending by category: ${slices
              .map((slice) => `${slice.label} ${formatPercent(slice.percentage)}`)
              .join(", ")}`}
          >
            <Donut slices={slices} track={palette.track} />
            <View style={styles.chartCenter}>
              <Text style={styles.chartCenterLabel}>Total spent</Text>
              <Text style={styles.chartCenterCurrency}>AED</Text>
              <Text style={styles.chartCenterValue} adjustsFontSizeToFit numberOfLines={1}>
                {formatAmount(total)}
              </Text>
            </View>
          </View>

          <View style={styles.legend}>
            {slices.map((slice) => (
              <View key={slice.label} style={styles.legendRow}>
                <View style={[styles.legendDot, { backgroundColor: slice.color }]} />
                <Text style={styles.legendName} numberOfLines={1}>
                  {slice.label}
                </Text>
                <Text style={styles.legendAmount}>{formatAED(slice.amount)}</Text>
                <Text style={styles.legendPercent}>{formatPercent(slice.percentage)}</Text>
              </View>
            ))}
          </View>
        </>
      )}
    </View>
  );
}
