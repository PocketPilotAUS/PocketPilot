
import type { FinancialPlan } from "../types/plans";

// 1. Percentage helpers
export const clampPercent = (value: number) =>
  Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));

export const percentOf = (value: number, total: number) =>
  total > 0 ? clampPercent((value / total) * 100) : 0;

// 2. Donut chart helper
export function donutSlice(start: number, fraction: number): string {
  const cx = 100;
  const cy = 100;
  const outerRadius = 90;
  const innerRadius = 66;

  const startAngle = start * 2 * Math.PI - Math.PI / 2;
  const endAngle = (start + fraction) * 2 * Math.PI - Math.PI / 2;

  const point = (radius: number, angle: number) => ({
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  });

  // A full circle needs two arcs in SVG.
  if (fraction >= 0.999999) {
    const outerTop = point(outerRadius, -Math.PI / 2);
    const outerBottom = point(outerRadius, Math.PI / 2);
    const innerTop = point(innerRadius, -Math.PI / 2);
    const innerBottom = point(innerRadius, Math.PI / 2);

    return [
      `M ${outerTop.x} ${outerTop.y}`,
      `A ${outerRadius} ${outerRadius} 0 1 1 ${outerBottom.x} ${outerBottom.y}`,
      `A ${outerRadius} ${outerRadius} 0 1 1 ${outerTop.x} ${outerTop.y}`,
      `Z`,
      `M ${innerTop.x} ${innerTop.y}`,
      `A ${innerRadius} ${innerRadius} 0 1 0 ${innerBottom.x} ${innerBottom.y}`,
      `A ${innerRadius} ${innerRadius} 0 1 0 ${innerTop.x} ${innerTop.y}`,
      `Z`,
    ].join(" ");
  }

  if (fraction <= 0) return "";

  const outerStart = point(outerRadius, startAngle);
  const outerEnd = point(outerRadius, endAngle);
  const innerStart = point(innerRadius, startAngle);
  const innerEnd = point(innerRadius, endAngle);
  const largeArc = fraction > 0.5 ? 1 : 0;

  return [
    `M ${outerStart.x} ${outerStart.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${outerEnd.x} ${outerEnd.y}`,
    `L ${innerEnd.x} ${innerEnd.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${innerStart.x} ${innerStart.y}`,
    `Z`,
  ].join(" ");
}

// 3. Plan calculations
export function planScenario(plan: FinancialPlan, proposed: boolean) {
  const spending = plan.allocations.reduce(
    (sum, row) => sum + (proposed ? row.target : row.baseline),
    0
  );

  const available = proposed
    ? plan.availableAfter
    : plan.availableBefore;

  // AI budget-goal plans use their selected monthly contribution.
  // Guided plans use preferred savings when provided.
  const fundingTarget = plan.budgetGoalSource
    ? plan.monthlyContribution
    : (plan.fundingTarget ?? plan.requiredMonthly);

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
