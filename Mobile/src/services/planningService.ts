import { apiFetch } from "./apiClient";
import type { FinancialPlan, PlanningContext, PlanningProfile } from "../types/plans";
export async function planningRequest<T>(base: string, path: string, method = "GET", profile?: PlanningProfile): Promise<T> {
  const response = await apiFetch(base, `/planning${path}`, { method, ...(profile ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(profile) } : {}) });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "Check the amounts, dates and required fields, then try again.");
  }
  return response.status === 204 ? undefined as T : response.json();
}
export const getPlanningContext = (base: string) => planningRequest<PlanningContext>(base, "/context");
export const getPlans = (base: string) => planningRequest<FinancialPlan[]>(base, "/plans");
export const savePlan = (base: string, profile: PlanningProfile, id?: string) => planningRequest<FinancialPlan>(base, id ? `/plans/${id}` : "/plans", id ? "PUT" : "POST", profile);

export async function confirmBudgetPlan(base: string, plan: FinancialPlan, id?: string): Promise<FinancialPlan> {
  const response = await apiFetch(base, id ? `/planning/budget-plans/${id}` : "/planning/budget-plans", { method: id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile: plan.profile, choices: plan.budgetChoices ?? {}, budget_fingerprint: plan.budgetFingerprint, request_key: plan.confirmationKey }) });
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(typeof data.detail === "string" ? data.detail : "Could not confirm plan. Please try again."); }
  return response.json();
}
