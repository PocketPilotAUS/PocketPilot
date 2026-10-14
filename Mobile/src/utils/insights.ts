import { toDisplayAmount } from "../preferences/currency";
// Calculations for the Insights screen. Everything is derived from the
// user's real data; the 20% rule stays in the backend (/recommendations/).

import { formatAmount, monthName } from "./dashboard";
import type { Transaction } from "./transactions";

// Spending trend

export type TrendMonth = {
  key: string; // YYYY-MM
  year: number;
  month: number; // 1-12
  label: string; // "Oct"
  total: number;
  // false for months before the user's first recorded transaction, so
  // "no data yet" is never shown as AED 0 of spending
  hasData: boolean;
};

export function monthKey(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, "0")}`;
}

// The `count` months ending with the selected month (oldest first)
export function buildTrend(
  transactions: Transaction[],
  endYear: number,
  endMonth: number,
  count = 6
): TrendMonth[] {
  const totals = new Map<string, number>();
  let firstKey: string | null = null;

  for (const transaction of transactions) {
    const key = transaction.date.slice(0, 7);
    // Summed in cents so many small amounts never drift
    totals.set(key, (totals.get(key) ?? 0) + Math.round(transaction.amount * 100));
    if (firstKey === null || key < firstKey) firstKey = key;
  }

  const months: TrendMonth[] = [];

  for (let offset = count - 1; offset >= 0; offset--) {
    const date = new Date(endYear, endMonth - 1 - offset, 1);
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const key = monthKey(year, month);

    months.push({
      key,
      year,
      month,
      label: monthName(month).slice(0, 3),
      total: (totals.get(key) ?? 0) / 100,
      hasData: firstKey !== null && key >= firstKey,
    });
  }

  return months;
}

export function trendStats(months: TrendMonth[]) {
  const withData = months.filter((month) => month.hasData);
  const current = months[months.length - 1];
  const previous = months[months.length - 2];

  const average = withData.length
    ? withData.reduce((sum, month) => sum + month.total, 0) / withData.length
    : null;

  // Change vs the previous month, only when both months have data and
  // the previous month had spending to compare against
  const change =
    current && previous && current.hasData && previous.hasData && previous.total > 0
      ? ((current.total - previous.total) / previous.total) * 100
      : null;

  return { average, monthsWithData: withData.length, change };
}

// "1.2k" style labels for chart bars
export function compactAED(value: number): string {
  value = toDisplayAmount(value);
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1).replace(/\.0$/, "")}k`;
  return formatAmount(value).replace(/\.00$/, "");
}

// Category changes

// GET /spending/compare
export type MonthComparison = {
  year: number;
  month: number;
  previous_year: number;
  previous_month: number;
  current_spending: Record<string, number>;
  previous_spending: Record<string, number>;
  percentage_changes: Record<string, number>;
};

// GET /recommendations/ (rule-based, ±20% threshold)
export type RuleRecommendation = {
  category: string;
  type: "spending_increase" | "spending_decrease";
  priority: string;
  percentage_change: number;
  message: string;
};

// GET /recommendations/ai
export type AIRecommendation = {
  category: string;
  priority: string;
  percentage_change: number;
  recommendation: string;
  ai_explanation: string | null;
};

export type CategoryChange = {
  category: string;
  current: number;
  previous: number;
  // null when there is nothing to compare against (new, or stopped)
  change: number | null;
  status: "increase" | "decrease" | "new" | "stopped";
  // Set when the backend's ±20% rule flagged this category
  recommendation: RuleRecommendation | null;
};

export function buildCategoryChanges(
  comparison: MonthComparison,
  recommendations: RuleRecommendation[]
): CategoryChange[] {
  const categories = new Set([
    ...Object.keys(comparison.current_spending),
    ...Object.keys(comparison.previous_spending),
  ]);

  const changes: CategoryChange[] = [...categories].map((category) => {
    const current = comparison.current_spending[category] ?? 0;
    const previous = comparison.previous_spending[category] ?? 0;
    const change = comparison.percentage_changes[category] ?? null;

    let status: CategoryChange["status"];
    if (change !== null) status = change >= 0 ? "increase" : "decrease";
    else if (current > 0) status = "new";
    else status = "stopped";

    return {
      category,
      current,
      previous,
      change,
      status,
      recommendation: recommendations.find((item) => item.category === category) ?? null,
    };
  });

  // Flagged first (largest change first), then by this month's spending
  return changes.sort((a, b) => {
    const flagged = Number(b.recommendation !== null) - Number(a.recommendation !== null);
    if (flagged !== 0) return flagged;
    if (a.recommendation && b.recommendation) {
      return Math.abs(b.recommendation.percentage_change) - Math.abs(a.recommendation.percentage_change);
    }
    return b.current - a.current || a.category.localeCompare(b.category);
  });
}
