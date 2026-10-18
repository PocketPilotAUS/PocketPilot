// Validation and request building for the Add expense screen. The rules,
// messages and request bodies are the same as before the redesign.

// Category values shared by expense and budget setup pickers
export const EXPENSE_CATEGORIES = [
  "Rent",
  "Entertainment",
  "Food",
  "Groceries",
  "Transport",
  "Shopping",
  "Subscriptions",
  "Bills",
  "Other",
] as const;

// Largest amount the backend accepts for one transaction
export const MAX_AMOUNT = 1_000_000_000;
// Backend limits for recurring schedules
export const CATEGORY_MAX_LENGTH = 40;
export const DESCRIPTION_MAX_LENGTH = 500;

export type ExpenseForm = {
  amount: string;
  category: string;
  customCategory: string;
  description: string;
  monthly: boolean;
  paymentDay: string;
};

// Some keyboards use a comma as the decimal point. A comma only counts as
// one when it is the sole separator with at most two digits after it
// ("12,5"); otherwise commas are thousands separators ("1,234.56", "1,234")
function normalizeSeparators(value: string): string {
  const commas = (value.match(/,/g) ?? []).length;

  if (commas === 1 && !value.includes(".") && /,\d{0,2}$/.test(value.replace(/[^0-9,]/g, ""))) {
    return value.replace(",", ".");
  }

  return value.replace(/,/g, "");
}

// Keeps the amount field to a valid shape as the user types or pastes:
// digits, one decimal point and at most two decimals, which recurring
// expenses require
export function sanitizeAmount(value: string): string {
  const cleaned = normalizeSeparators(value).replace(/[^0-9.]/g, "");
  const [whole, ...rest] = cleaned.split(".");

  if (rest.length === 0) return whole;

  return `${whole}.${rest.join("").slice(0, 2)}`;
}

export function sanitizeDay(value: string): string {
  return value.replace(/[^0-9]/g, "").slice(0, 2);
}

export function stepDay(value: string, step: number): string {
  const current = Number(value) || 0;
  return String(Math.min(31, Math.max(1, current + step)));
}

// Same checks and messages as before; null when the form is valid
export function validateExpense(form: ExpenseForm): { title: string; message: string } | null {
  const numericAmount = Number(form.amount);

  if (!form.amount.trim() || !Number.isFinite(numericAmount) || numericAmount <= 0) {
    return { title: "Invalid amount", message: "Please enter an amount greater than zero." };
  }

  if (numericAmount > MAX_AMOUNT) {
    return { title: "Invalid amount", message: "Please enter an amount of up to AED 1,000,000,000." };
  }

  if (form.category === "Other" && !form.customCategory.trim()) {
    return { title: "Category required", message: "Please enter a name for your custom category." };
  }

  if (
    form.monthly &&
    (!/^\d{1,2}$/.test(form.paymentDay) || Number(form.paymentDay) < 1 || Number(form.paymentDay) > 31)
  ) {
    return { title: "Payment day", message: "Choose a day from 1 to 31." };
  }

  return null;
}

function localISODate(date: Date): string {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

// Same endpoint and body as before: a one-off expense dated today, or a
// monthly schedule (the backend records today's payment immediately)
export function buildExpenseRequest(form: ExpenseForm, today: Date, requestKey: string) {
  return {
    path: form.monthly ? "/recurring/" : "/transactions/",
    body: {
      amount: Number(form.amount),
      category: form.category === "Other" ? form.customCategory.trim() : form.category,
      description: form.description.trim() || null,
      ...(form.monthly
        ? { day: Number(form.paymentDay), request_key: requestKey }
        : { date: localISODate(today) }),
    },
  };
}

// Random v4 UUID for recurring requests (same format as before)
export function newRequestKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const n = Math.floor(Math.random() * 16);
    return (c === "x" ? n : (n & 3) | 8).toString(16);
  });
}
