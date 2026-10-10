import { apiFetch } from "./apiClient";
import type { DashboardData } from "../utils/dashboard";

async function putJson(apiBaseUrl: string, path: string, body: object): Promise<DashboardData> {
  const response = await apiFetch(apiBaseUrl, path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  // Both endpoints return the updated monthly summary
  return response.json();
}

export function saveMonthlyIncome(
  apiBaseUrl: string,
  year: number,
  month: number,
  amount: string
): Promise<DashboardData> {
  return putJson(apiBaseUrl, `/budget/income?year=${year}&month=${month}`, { amount });
}

export function saveBudgetPlan(
  apiBaseUrl: string,
  year: number,
  month: number,
  percentages: Record<string, number>
): Promise<DashboardData> {
  return putJson(apiBaseUrl, `/budget/plan?year=${year}&month=${month}`, { percentages });
}
