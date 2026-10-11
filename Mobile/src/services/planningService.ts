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
