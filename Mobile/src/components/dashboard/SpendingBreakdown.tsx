import { formatDisplayAmount } from "../../preferences/currency";
import React from "react";
import { ActivityIndicator, Pressable } from "react-native";
import { Text, View } from "../../preferences/LocalizedNative";
import IncomeDonut from "../IncomeDonut";
import { incomeChart } from "../../utils/incomeChart";
import { Plus } from "lucide-react-native";

import { useDashboardTheme } from "./useDashboardTheme";
import {
  DashboardData,
  buildSlices,
  buildBudgetRows,
  formatAED,
  formatPercent,
  monthName,
} from "../../utils/dashboard";

const SIZE = 184;

type Props = {
  data: DashboardData | null;
  loading: boolean;
  onAddExpense: () => void;
};

export default function SpendingBreakdown({ data, loading, onAddExpense }: Props) {
  const { styles, palette, chartColors } = useDashboardTheme();

  const chart = incomeChart(data ? buildSlices(data.category_spending, chartColors) : [], data?.income);
  const slices = chart.slices;
  const total = chart.total;
  const month = data ? monthName(data.month) : "";
  // Planned budget amounts are targets, never payments: only recorded
  // expenses count as spending
  const budget = data?.ideal_budget ?? null;
  const plannedRows = budget ? buildBudgetRows(budget.allocations, budget.mode === "amounts") : [];
  const plannedTotal = budget ? budget.allocations.reduce((sum, row) => sum + (row.target ?? 0), 0) : 0;
  const recordedTotal = data?.spent ?? 0;

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.cardTitleBlock}>
          <Text style={styles.cardLabel}>Spending breakdown</Text>
          {data && <Text style={styles.cardSubtitle}>Share of income · {month}</Text>}
        </View>
      </View>

      {loading && !data ? (
        <ActivityIndicator color={palette.accent} style={styles.loader} />
      ) : slices.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.chartWrap}>
            <IncomeDonut chart={chart} size={SIZE} grey={palette.textMuted} danger={palette.danger} />
            <View style={styles.chartCenter}>
              <Text style={styles.chartCenterLabel}>{chart.validIncome ? "Monthly income" : "Income needed"}</Text>
              <Text style={styles.chartCenterCurrency}>AED</Text>
              <Text style={styles.chartCenterValue} adjustsFontSizeToFit numberOfLines={1}>{chart.validIncome ? formatDisplayAmount(data!.income!) : "—"}</Text>
            </View>
          </View>

          <Text style={styles.emptyTitle}>No expenses recorded yet{month ? ` for ${month}` : ""}</Text>
          <Text style={styles.emptyText}>
            {chart.validIncome ? `${formatAED(chart.remaining!)} of your income is unspent. Grey represents the remaining income.` : "Add your monthly income to see spending as a share of it."}
          </Text>
          {budget && <Text style={styles.emptyText}>Your budget plans {formatAED(plannedTotal)} for this month. Planned amounts are not payments; add expenses as you pay them.</Text>}

        </View>
      ) : (
        <>
          <View
            style={styles.chartWrap}
            accessible
            accessibilityLabel={`Spending by category: ${slices
              .map((slice) => `${slice.label} ${slice.percentage === null ? "income unknown" : formatPercent(slice.percentage) + " of income"}`)
              .join(", ")}. ${chart.remaining === null ? "Add monthly income." : `${formatAED(chart.remaining)} unspent.`}`}
          >
            <IncomeDonut chart={chart} size={SIZE} grey={palette.textMuted} danger={palette.danger} />
            <View style={styles.chartCenter}>
              <Text style={styles.chartCenterLabel}>{chart.validIncome ? "Monthly income" : "Income needed"}</Text>
              <Text style={styles.chartCenterCurrency}>AED</Text>
              <Text style={styles.chartCenterValue} adjustsFontSizeToFit numberOfLines={1}>
                {chart.validIncome ? formatDisplayAmount(data!.income!) : "—"}
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
                <Text style={styles.legendPercent}>{slice.percentage === null ? "—" : formatPercent(slice.percentage)}</Text>
              </View>
            ))}
            {chart.validIncome && <View style={styles.legendRow}>
              <View style={[styles.legendDot, { backgroundColor: palette.textMuted }]} />
              <Text style={styles.legendName}>Unspent income</Text>
              <Text style={styles.legendAmount}>{formatAED(chart.remaining!)}</Text>
              <Text style={styles.legendPercent}>{formatPercent(chart.remainingPercent!)}</Text>
            </View>}
          </View>
          <Text style={styles.cardSubtitle}>{chart.validIncome ? `${formatAED(total)} spent · ${formatPercent(chart.usedPercent!)} of income. Grey is unspent income.` : "Enter a positive monthly income to calculate percentages. Recorded spending is shown above."}</Text>
          {chart.overBy > 0 && <Text style={styles.chartDeficit}>{formatAED(chart.overBy)} over income. The full red ring means all income has been used; category percentages show the actual overage.</Text>}
        </>
      )}
      {budget && plannedRows.length > 0 && <View style={styles.budgetList}>
        <View style={styles.cardTitleBlock}>
          <Text style={styles.cardLabel}>Planned vs recorded</Text>
          <Text style={styles.cardSubtitle}>{formatAED(recordedTotal)} recorded of {formatAED(plannedTotal)} planned{month ? ` · ${month}` : ""}</Text>
        </View>
        {plannedRows.map(row => {
          const ratio = row.ratio ?? 0;
          const percent = Math.min(100, Number.isFinite(ratio) ? ratio * 100 : 100);
          return <View key={row.category}>
            <View style={styles.budgetHeaderRow}>
              <Text style={styles.budgetName}>{row.category}</Text>
              <Text style={styles.budgetFigures}><Text style={[styles.budgetFiguresStrong, row.over && styles.statusDanger]}>{formatAED(row.spent)}</Text>{row.target != null ? ` / ${formatAED(row.target)} planned` : ""}</Text>
            </View>
            {row.target != null && <View style={styles.budgetTrack} accessibilityRole="progressbar" accessibilityLabel={`${row.category} recorded against plan`} accessibilityValue={{ min: 0, max: 100, now: Math.round(percent), text: `${formatAED(row.spent)} / ${formatAED(row.target)}` }}>
              <View style={[styles.budgetFill, row.over ? styles.budgetFillDanger : ratio >= .8 ? styles.budgetFillWarning : null, { width: `${percent}%` }]} />
            </View>}
          </View>;
        })}
        <Text style={styles.mutedText}>Recorded amounts come only from expenses you add. Savings are tracked separately.</Text>
      </View>}
      <Pressable
        onPress={onAddExpense}
        style={({ pressed }) => [
          styles.compactAddButton,
          styles.spendingAddAction,
          pressed && styles.buttonDisabled,
        ]}
        accessibilityRole="button"
        accessibilityLabel="Add expenses"
      >
        <Plus size={16} color={palette.onAccent} strokeWidth={2.6} />
        <Text style={styles.compactAddButtonText}>Add expenses</Text>
      </Pressable>
    </View>
  );
}
