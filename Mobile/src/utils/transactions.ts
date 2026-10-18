// Search, filtering, sorting and grouping for the Transactions screen.
// Transaction rows and recorded debt payments share one display list; no duplicate ledger entries are created.

export type Transaction = {
  id: number;
  debt_payment_id?: number;
  amount: number;
  category: string;
  description: string | null;
  date: string; // YYYY-MM-DD
};

export type DateFilter =
  | { kind: "all" }
  | { kind: "thisWeek" }
  | { kind: "thisMonth" }
  | { kind: "lastMonth" }
  | { kind: "custom"; start: string; end: string };

export type AmountFilter =
  | { kind: "any" }
  | { kind: "above"; min: number }
  | { kind: "below"; max: number }
  | { kind: "between"; min: number; max: number };

export type SortOrder = "newest" | "oldest" | "highest" | "lowest";

export type Filters = {
  search: string;
  date: DateFilter;
  category: string | null; // null = all categories
  amount: AmountFilter;
  sort: SortOrder;
};

export const DEFAULT_FILTERS: Filters = {
  search: "",
  date: { kind: "thisMonth" },
  category: null,
  amount: { kind: "any" },
  sort: "newest",
};

const MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_LONG = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const DAYS_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const DAYS_LONG = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

// Dates

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

// Local calendar date as YYYY-MM-DD (never shifted by time zones)
export function toISODate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function parseISODate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function addDays(date: Date, days: number): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
}

// Inclusive [start, end] as YYYY-MM-DD strings, or null for all time.
// Weeks run Monday to Sunday.
export function dateRange(filter: DateFilter, today: Date): { start: string; end: string } | null {
  const year = today.getFullYear();
  const month = today.getMonth();

  switch (filter.kind) {
    case "all":
      return null;
    case "thisWeek": {
      const monday = addDays(today, -((today.getDay() + 6) % 7));
      return { start: toISODate(monday), end: toISODate(addDays(monday, 6)) };
    }
    case "thisMonth":
      return { start: toISODate(new Date(year, month, 1)), end: toISODate(new Date(year, month + 1, 0)) };
    case "lastMonth":
      return { start: toISODate(new Date(year, month - 1, 1)), end: toISODate(new Date(year, month, 0)) };
    case "custom":
      return filter.start <= filter.end
        ? { start: filter.start, end: filter.end }
        : { start: filter.end, end: filter.start };
  }
}

export function formatShortDate(value: string, today: Date = new Date()): string {
  const date = parseISODate(value);
  const label = `${date.getDate()} ${MONTHS_SHORT[date.getMonth()]}`;
  return date.getFullYear() === today.getFullYear() ? label : `${label} ${date.getFullYear()}`;
}

export function formatLongDate(value: string): string {
  const date = parseISODate(value);
  return `${DAYS_LONG[date.getDay()]}, ${date.getDate()} ${MONTHS_LONG[date.getMonth()]} ${date.getFullYear()}`;
}

export function dayGroupLabel(value: string, today: Date): string {
  if (value === toISODate(today)) return "Today";
  if (value === toISODate(addDays(today, -1))) return "Yesterday";

  const date = parseISODate(value);
  return `${DAYS_SHORT[date.getDay()]}, ${formatShortDate(value, today)}`;
}

export function monthTitle(year: number, month: number): string {
  return `${MONTHS_LONG[month]} ${year}`;
}

// Filtering and sorting

export function matchesSearch(transaction: Transaction, search: string): boolean {
  const query = search.trim().toLowerCase();

  if (!query) return true;

  return (
    transaction.category.toLowerCase().includes(query) ||
    (transaction.description ?? "").toLowerCase().includes(query)
  );
}

function matchesAmount(amount: number, filter: AmountFilter): boolean {
  switch (filter.kind) {
    case "any":
      return true;
    case "above":
      return amount >= filter.min;
    case "below":
      return amount <= filter.max;
    case "between":
      return amount >= filter.min && amount <= filter.max;
  }
}

const SORTERS: Record<SortOrder, (a: Transaction, b: Transaction) => number> = {
  newest: (a, b) => b.date.localeCompare(a.date) || b.id - a.id,
  oldest: (a, b) => a.date.localeCompare(b.date) || a.id - b.id,
  highest: (a, b) => b.amount - a.amount || b.date.localeCompare(a.date) || b.id - a.id,
  lowest: (a, b) => a.amount - b.amount || b.date.localeCompare(a.date) || b.id - a.id,
};

export function applyFilters(transactions: Transaction[], filters: Filters, today: Date): Transaction[] {
  const range = dateRange(filters.date, today);

  return transactions
    .filter((t) => matchesSearch(t, filters.search))
    .filter((t) => filters.category === null || t.category === filters.category)
    .filter((t) => range === null || (t.date >= range.start && t.date <= range.end))
    .filter((t) => matchesAmount(t.amount, filters.amount))
    .sort(SORTERS[filters.sort]);
}

export function summarize(transactions: Transaction[]): { total: number; count: number } {
  return {
    // Summed in cents so many small amounts never drift
    total: Math.round(transactions.reduce((sum, t) => sum + Math.round(t.amount * 100), 0)) / 100,
    count: transactions.length,
  };
}

export function categoriesOf(transactions: Transaction[]): string[] {
  return [...new Set(transactions.map((t) => t.category))].sort((a, b) => a.localeCompare(b));
}

export type TransactionGroup = {
  key: string;
  title: string;
  total: number;
  items: Transaction[];
};

// Date sorts are grouped by day; amount sorts stay one list so the
// amount order is not broken up by dates
export function groupTransactions(transactions: Transaction[], sort: SortOrder, today: Date): TransactionGroup[] {
  if (transactions.length === 0) return [];

  if (sort === "highest" || sort === "lowest") {
    return [{
      key: sort,
      title: sort === "highest" ? "Highest amount first" : "Lowest amount first",
      total: summarize(transactions).total,
      items: transactions,
    }];
  }

  const groups: TransactionGroup[] = [];

  for (const transaction of transactions) {
    const last = groups[groups.length - 1];

    if (last && last.key === transaction.date) {
      last.items.push(transaction);
    } else {
      groups.push({ key: transaction.date, title: dayGroupLabel(transaction.date, today), total: 0, items: [transaction] });
    }
  }

  return groups.map((group) => ({ ...group, total: summarize(group.items).total }));
}

// Labels for the filter chips

export function dateFilterLabel(filter: DateFilter, today: Date = new Date()): string {
  switch (filter.kind) {
    case "all":
      return "All time";
    case "thisWeek":
      return "This week";
    case "thisMonth":
      return "This month";
    case "lastMonth":
      return "Last month";
    case "custom": {
      const range = dateRange(filter, today)!;
      return range.start === range.end
        ? formatShortDate(range.start, today)
        : `${formatShortDate(range.start, today)} – ${formatShortDate(range.end, today)}`;
    }
  }
}

function shortAmount(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

export function amountFilterLabel(filter: AmountFilter): string {
  switch (filter.kind) {
    case "any":
      return "Any amount";
    case "above":
      return `≥ AED ${shortAmount(filter.min)}`;
    case "below":
      return `≤ AED ${shortAmount(filter.max)}`;
    case "between":
      return `AED ${shortAmount(filter.min)}–${shortAmount(filter.max)}`;
  }
}

export const SORT_LABELS: Record<SortOrder, string> = {
  newest: "Newest",
  oldest: "Oldest",
  highest: "Highest",
  lowest: "Lowest",
};

export function activeFilterCount(filters: Filters): number {
  return (
    (filters.date.kind !== DEFAULT_FILTERS.date.kind ? 1 : 0) +
    (filters.category !== null ? 1 : 0) +
    (filters.amount.kind !== "any" ? 1 : 0)
  );
}

// Validates the amount filter form; returns the filter or an error message
export function parseAmountFilter(
  kind: AmountFilter["kind"],
  minDraft: string,
  maxDraft: string
): AmountFilter | string {
  const valid = (value: string) => /^\d+(\.\d{1,2})?$/.test(value.trim());
  const min = Number(minDraft.trim());
  const max = Number(maxDraft.trim());

  switch (kind) {
    case "any":
      return { kind: "any" };
    case "above":
      return valid(minDraft) ? { kind: "above", min } : "Enter a valid amount, e.g. 100 or 49.99.";
    case "below":
      return valid(maxDraft) ? { kind: "below", max } : "Enter a valid amount, e.g. 100 or 49.99.";
    case "between":
      if (!valid(minDraft) || !valid(maxDraft)) return "Enter valid minimum and maximum amounts.";
      if (min > max) return "The minimum must not be more than the maximum.";
      return { kind: "between", min, max };
  }
}


// Negative display IDs keep debt-payment IDs separate from transaction IDs.
export function debtPaymentTransactions(payments: { id: number; amount: number; paid_on: string; debt_name: string; automatic?: boolean }[]): Transaction[] {
  return payments.map(payment => ({
    id: -payment.id,
    debt_payment_id: payment.id,
    amount: payment.amount,
    category: "Debt",
    description: `${payment.debt_name}${payment.automatic ? " - Automatically recorded" : " - Debt payment"}`,
    date: payment.paid_on,
  }));
}
