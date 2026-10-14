import type { FinancialPlan } from "../types/plans";

// 1. Percentage helpers
export const clampPercent = (value: number) =>
  Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));

export const percentOf = (value: number, total: number) =>
  total > 0 ? clampPercent((value / total) * 100) : 0;

// 2. Plan calculations
export function planScenario(plan: FinancialPlan, proposed: boolean) {
  const spending = plan.allocations.reduce(
    (sum, row) => sum + (proposed ? row.target : row.baseline),
    0
  );

  const available = proposed
    ? plan.availableAfter
    : plan.availableBefore;

  const fundingTarget = plan.fundingTarget ?? plan.requiredMonthly;

  const contribution = Math.max(
    0,
    Math.min(fundingTarget, available)
  );

  return {
    spending,
    available,
    contribution,
    shortfall: Math.max(0, fundingTarget - available),
    fundedPercent: percentOf(contribution, fundingTarget),
    expenseDeficit: Math.max(0, -available),
  };
}