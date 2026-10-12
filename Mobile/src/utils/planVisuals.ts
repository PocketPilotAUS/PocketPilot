import type { FinancialPlan } from "../types/plans";

export const clampPercent = (value: number) => Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
export const percentOf = (value: number, total: number) => total > 0 ? clampPercent(value / total * 100) : 0;

export function planScenario(plan: FinancialPlan, proposed: boolean) {
  const spending = plan.allocations.reduce((sum, row) => sum + (proposed ? row.target : row.baseline), 0);
  const available = proposed ? plan.availableAfter : plan.availableBefore;
  const contribution = Math.max(0, Math.min(plan.requiredMonthly, available));
  return { spending, available, contribution, shortfall: Math.max(0, plan.requiredMonthly - available),
    fundedPercent: percentOf(contribution, plan.requiredMonthly), expenseDeficit: Math.max(0, -available) };
}

export function donutSlice(start: number, fraction: number, outer = 90, inner = 66): string {
  const point = (radius: number, angle: number) => `${100 + radius * Math.cos(angle)} ${100 + radius * Math.sin(angle)}`;
  if (fraction >= 1 - 1e-9) {
    return `M 100 ${100 - outer} A ${outer} ${outer} 0 1 1 100 ${100 + outer} A ${outer} ${outer} 0 1 1 100 ${100 - outer} M 100 ${100 - inner} A ${inner} ${inner} 0 1 0 100 ${100 + inner} A ${inner} ${inner} 0 1 0 100 ${100 - inner} Z`;
  }
  const a = start * Math.PI * 2 - Math.PI / 2;
  const b = (start + fraction) * Math.PI * 2 - Math.PI / 2;
  const large = fraction > .5 ? 1 : 0;
  return `M ${point(outer, a)} A ${outer} ${outer} 0 ${large} 1 ${point(outer, b)} L ${point(inner, b)} A ${inner} ${inner} 0 ${large} 0 ${point(inner, a)} Z`;
}
