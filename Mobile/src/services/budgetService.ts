import { apiFetch } from "./apiClient";
import type { DashboardData } from "../utils/dashboard";

async function putJson(apiBaseUrl: string, path: string, body: object): Promise<DashboardData> {
  const response = await apiFetch(apiBaseUrl, path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : Array.isArray(body.detail) ? body.detail.map((item: { msg?: string }) => item.msg?.replace(/^Value error, /, "")).filter(Boolean).join("\n") : "";
    throw new Error(detail || "Could not save your budget. Please try again.");
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

export function saveBudgetSetup(apiBaseUrl: string, year: number, month: number, income: string, categories: { name: string; amount: string }[]): Promise<DashboardData> {
  return putJson(apiBaseUrl, `/budget/setup?year=${year}&month=${month}`, { income, categories });
}
