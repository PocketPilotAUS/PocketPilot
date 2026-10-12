export type IncomeCategory = { label: string; amount: number; color: string };

/** Percentages use income; the circle never silently normalizes expenses to 100%. */
export function incomeChart(categories: IncomeCategory[], income: number | null | undefined) {
  const validIncome = typeof income === "number" && Number.isFinite(income) && income > 0;
  const total = Math.round(categories.reduce((sum, category) => sum + Math.max(0, category.amount), 0) * 100) / 100;
  const remaining = validIncome ? Math.max(0, Math.round((income - total) * 100) / 100) : null;
  const overBy = validIncome ? Math.max(0, Math.round((total - income) * 100) / 100) : 0;
  return {
    validIncome, total, remaining, overBy,
    usedPercent: validIncome ? total / income * 100 : null,
    remainingPercent: validIncome ? Math.max(0, income - total) / income * 100 : null,
    slices: categories.map(category => ({ ...category,
      percentage: validIncome ? Math.max(0, category.amount) / income * 100 : null,
      // Above income, render a full deficit ring rather than misleading category arcs.
      fraction: validIncome && overBy === 0 ? Math.max(0, category.amount) / income : 0,
    })),
  };
}
