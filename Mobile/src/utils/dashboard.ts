import type {
  BudgetAllocation,
  MonthlyBudget,
} from "../components/MonthlyIncomeCard";

// Shape returned by GET /budget/monthly (and the PUT budget endpoints)
export type DashboardData = MonthlyBudget & {
  total_spending?: number;
  category_spending: Record<string, number>;
  category_percentages: Record<string, number>;
};

// Planned allocation in the budget split; it is not a spending category
export const SAVINGS_CATEGORY = "Savings / debt";
export const MAX_INCOME = 1_000_000_000;

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

// Amounts are compared to the cent, so float noise never shows as "over"
const CENT = 0.005;

export function monthName(month: number): string {
  return MONTHS[month - 1] ?? "";
}

// Manual formatting: consistent on every device, no Intl dependency
export function formatAmount(value: number): string {
  const [whole, cents] = Math.abs(value).toFixed(2).split(".");
  return `${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${cents}`;
}

export function formatAED(value: number): string {
  return `${value < 0 ? "-" : ""}AED ${formatAmount(value)}`;
}

export function formatPercent(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1)}%`;
}

function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

// Days left in the month, including today; null if the data is for
// another month
export function daysLeftInMonth(data: MonthlyBudget, today: Date): number | null {
  if (data.year !== today.getFullYear() || data.month !== today.getMonth() + 1) {
    return null;
  }

  const daysInMonth = new Date(data.year, data.month, 0).getDate();
  return daysInMonth - today.getDate() + 1;
}

// Spending breakdown (donut chart)

export type Slice = {
  label: string;
  amount: number;
  percentage: number;
  color: string;
};

export function buildSlices(
  categorySpending: Record<string, number>,
  colors: readonly string[]
): Slice[] {
  const entries = Object.entries(categorySpending)
    .filter(([, amount]) => amount > 0)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));

  const total = entries.reduce((sum, [, amount]) => sum + amount, 0);

  if (total <= 0) return [];

  // Beyond the number of distinct colours, the smallest categories are
  // combined so every slice stays distinguishable
  let shown = entries;

  if (entries.length > colors.length) {
    const rest = entries.slice(colors.length - 1);
    shown = [
      ...entries.slice(0, colors.length - 1),
      [`${rest.length} more categories`, rest.reduce((sum, [, amount]) => sum + amount, 0)],
    ];
  }

  return shown.map(([label, amount], index) => ({
    label,
    amount,
    percentage: (amount / total) * 100,
    color: colors[index],
  }));
}

export function largestCategory(categorySpending: Record<string, number>) {
  const entries = Object.entries(categorySpending).filter(([, amount]) => amount > 0);
  const total = entries.reduce((sum, [, amount]) => sum + amount, 0);

  if (total <= 0) return null;

  const [label, amount] = entries.reduce((best, entry) => (entry[1] > best[1] ? entry : best));

  return { label, amount, percentage: (amount / total) * 100 };
}

// Budget tracker

export type BudgetRow = {
  category: string;
  percentage: number;
  target: number | null;
  spent: number;
  // Share of the target used (1 = 100%); null without income
  ratio: number | null;
  over: boolean;
  overBy: number;
};

export function buildBudgetRows(allocations: BudgetAllocation[]): BudgetRow[] {
  return allocations
    .filter((item) => item.category !== SAVINGS_CATEGORY)
    .filter((item) => item.percentage > 0 || item.spent > 0)
    .map((item) => {
      const over = item.target !== null && item.spent - item.target > CENT;

      let ratio: number | null = null;

      if (item.target !== null) {
        ratio = item.target > 0 ? item.spent / item.target : item.spent > 0 ? Infinity : 0;
      }

      return {
        category: item.category,
        percentage: item.percentage,
        target: item.target,
        spent: item.spent,
        ratio,
        over,
        overBy: over && item.target !== null ? item.spent - item.target : 0,
      };
    });
}

// Validation (same rules as the backend)

export function validateIncome(draft: string): string | null {
  const value = draft.trim();

  if (!/^\d+(\.\d{1,2})?$/.test(value) || Number(value) > MAX_INCOME) {
    return "Enter an amount from 0 to 1,000,000,000 with up to two decimals.";
  }

  return null;
}

export function planTotal(draft: Record<string, string>): number {
  return Object.values(draft).reduce((sum, value) => sum + (Number(value) || 0), 0);
}

export function validatePlan(draft: Record<string, string>): string | null {
  const invalid = Object.values(draft).some(
    (value) => !/^\d{1,3}$/.test(value) || Number(value) > 100
  );

  if (invalid) return "Use whole percentages from 0 to 100.";

  const total = planTotal(draft);

  if (total !== 100) return `The split must total 100% (currently ${total}%).`;

  return null;
}

// PocketPilot insight: one message, built only from the user's own figures

export type InsightTone = "positive" | "warning" | "danger" | "neutral";

export type Insight = {
  tone: InsightTone;
  title: string;
  message: string;
};

export function buildInsight(data: DashboardData | null, today: Date): Insight | null {
  if (!data) return null;

  const income = data.income;
  const spent = data.spent;
  const hasSpending = spent > CENT;
  const month = monthName(data.month);
  const daysLeft = daysLeftInMonth(data, today);
  const top = largestCategory(data.category_spending);

  // Not enough information for a meaningful insight
  if (!hasSpending && (income === null || income === 0)) return null;

  // 1. Spending is above income
  if (income !== null && spent - income > CENT) {
    return {
      tone: "danger",
      title: "Spending is above your income",
      message:
        `You've spent ${formatAED(spent)} in ${month}, ${formatAED(spent - income)} more than your ${formatAED(income)} income.` +
        (top ? ` ${top.label} is your largest expense at ${formatAED(top.amount)}.` : "") +
        " Pausing non-essential purchases until next month will stop the gap growing.",
    };
  }

  const rows = data.ideal_budget ? buildBudgetRows(data.ideal_budget.allocations) : [];

  // 2. A category is over its budget (largest overspend first)
  const overRows = rows.filter((row) => row.over).sort((a, b) => b.overBy - a.overBy);

  if (overRows.length > 0) {
    const row = overRows[0];
    const others = overRows.length - 1;

    return {
      tone: "warning",
      title: `${row.category} is over budget`,
      message:
        `You've spent ${formatAED(row.spent)} on ${row.category} against a ${formatAED(row.target ?? 0)} budget, ${formatAED(row.overBy)} over.` +
        (daysLeft !== null
          ? ` Holding off on ${row.category} for the remaining ${plural(daysLeft, "day")} of ${month} will stop it rising further.`
          : "") +
        (others > 0
          ? ` ${plural(others, "other category", "other categories")} ${others === 1 ? "is" : "are"} also over budget.`
          : ""),
    };
  }

  // 3. A category has used most of its budget
  const nearRows = rows
    .filter((row) => row.target !== null && row.target > 0 && row.ratio !== null && row.ratio >= 0.8)
    .sort((a, b) => (b.ratio ?? 0) - (a.ratio ?? 0));

  if (nearRows.length > 0) {
    const row = nearRows[0];
    const target = row.target ?? 0;
    const left = Math.max(0, target - row.spent);

    return {
      tone: "warning",
      title: `${row.category} is close to its limit`,
      message:
        `${row.category} has used ${formatPercent((row.ratio ?? 0) * 100)} of its ${formatAED(target)} budget, leaving ${formatAED(left)}` +
        (daysLeft !== null
          ? ` for the next ${plural(daysLeft, "day")}: about ${formatAED(left / daysLeft)} a day.`
          : "."),
    };
  }

  // 4. Within budget, with spending recorded
  if (income !== null && income > 0 && hasSpending) {
    const remaining = income - spent;
    const used = formatPercent((spent / income) * 100);
    const largest = top ? ` Your largest expense ${daysLeft !== null ? "is" : "was"} ${top.label} at ${formatPercent(top.percentage)} of spending.` : "";

    return {
      tone: "positive",
      title: daysLeft !== null ? "You're within budget" : `${month} stayed within budget`,
      message:
        (daysLeft !== null
          ? `You've used ${used} of your income and have ${formatAED(remaining)} left for the next ${plural(daysLeft, "day")}: about ${formatAED(remaining / daysLeft)} a day.`
          : `You used ${used} of your ${month} income and finished with ${formatAED(remaining)} unspent.`) +
        largest,
    };
  }

  // 5. Income set, nothing spent
  if (income !== null && !hasSpending) {
    return daysLeft !== null
      ? {
          tone: "neutral",
          title: "A fresh start this month",
          message: `No expenses recorded for ${month} yet, so your full ${formatAED(income)} income is available. Log expenses as you go to keep this insight up to date.`,
        }
      : {
          tone: "neutral",
          title: `No expenses recorded for ${month}`,
          message: `Your ${formatAED(income)} income for ${month} has no expenses recorded against it.`,
        };
  }

  // 6. Spending recorded, no income
  if (top) {
    return {
      tone: "neutral",
      title: `${top.label} is your biggest expense`,
      message: `${top.label} makes up ${formatPercent(top.percentage)} of your ${month} spending (${formatAED(top.amount)} of ${formatAED(spent)}). Add your monthly income to see how much you have left.`,
    };
  }

  return null;
}
