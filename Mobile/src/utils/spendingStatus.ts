// Plain-language descriptions of GET /planning/status. All figures come from
// the server's deterministic check; nothing is calculated here.
import type { SpendingStatus } from "../types/plans";
import { formatAED } from "./dashboard";

// Separate sentences so each one can be translated
export type StatusMessage = { title: string; lines: string[]; action: string };

function overspending(status: SpendingStatus): string {
  const over = status.over_budget;
  if (over.length === 1) return `${over[0].category} spending is ${formatAED(over[0].over)} over your monthly budget.`;
  if (over.length > 1) return `${over.length} categories are ${formatAED(over.reduce((sum, row) => sum + row.over, 0))} over budget in total.`;
  return "";
}

export function statusMessage(status: SpendingStatus | null): StatusMessage | null {
  if (!status || !status.has_budget || status.level === 0) return null;
  const over = overspending(status);
  const goals = status.required_contributions > 0;
  if (status.level === 3) {
    return {
      title: goals ? "Savings goal unaffordable this month" : "Spending is above your income",
      lines: goals
        ? [`Recorded spending and upcoming bills leave ${formatAED(Math.max(0, status.available_committed ?? 0))} this month, ${formatAED(status.shortfall)} short of ${formatAED(status.required_contributions)} for your savings goals.`,
          "Money already spent can't be recovered, but a recovery plan can help with the rest of the month."]
        : [`Recorded spending and upcoming bills are ${formatAED(status.shortfall)} more than this month's income.`],
      action: "Get AI recovery plan",
    };
  }
  if (status.level === 2) {
    const lines: string[] = [];
    if (status.risk_reasons.includes("low_buffer") && status.buffer != null) {
      lines.push(goals
        ? `You can spend about ${formatAED(Math.max(0, status.buffer))} more this month before your savings goal becomes unaffordable: about ${formatAED(status.daily_allowance ?? 0)} a day for the next ${status.days_left} days.`
        : `You can spend about ${formatAED(Math.max(0, status.buffer))} more this month before running out of income: about ${formatAED(status.daily_allowance ?? 0)} a day for the next ${status.days_left} days.`);
      lines.push(`Your budget still plans about ${formatAED(status.still_needed ?? 0)} for the rest of the month.`);
    }
    if (status.risk_reasons.includes("projection")) {
      lines.push(goals
        ? `At your expected spending, about ${formatAED(Math.max(0, status.available_projected ?? 0))} would be left for ${formatAED(status.required_contributions)} of goal savings: a projected shortfall of ${formatAED(Math.max(0, (status.required_contributions) - (status.available_projected ?? 0)))}.`
        : `At your expected spending, you would spend ${formatAED(Math.max(0, -(status.available_projected ?? 0)))} more than this month's income.`);
      lines.push(status.forecast_confidence === "high" ? "Based on your spending pace and your past months. This is a projection, not a confirmed outcome."
        : "Based on limited spending history, so treat it as a rough estimate, not a confirmed outcome.");
    }
    return { title: goals ? "Savings goal at risk" : "Spending may exceed your income", lines, action: "Get AI adjustment plan" };
  }
  return {
    title: "Over budget",
    lines: [over, status.income_missing ? "Add this month's income to check whether your goals are on track."
      : goals && status.available_projected != null
        ? `After expected spending of ${formatAED(status.projected_spending)}, about ${formatAED(status.available_projected)} is left: enough for your ${formatAED(status.required_contributions)} savings goal, with about ${formatAED(status.available_projected - status.required_contributions)} to spare.`
        : "Keep an eye on your remaining spending.",
      !status.income_missing && status.forecast_confidence === "low" ? "There isn't enough spending history yet for a reliable forecast." : ""].filter(Boolean),
    action: "Review with AI",
  };
}
