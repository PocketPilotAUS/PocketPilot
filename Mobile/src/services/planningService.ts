import { apiFetch } from "./apiClient";
import type { AdjustmentProposal, FinancialPlan, PlanningContext, PlanningProfile, SpendingStatus } from "../types/plans";
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

export async function confirmBudgetPlan(base: string, plan: FinancialPlan, id?: string, applyToBudget?: boolean): Promise<FinancialPlan> {
  if (!id) return acceptReviewedPlan(base, plan, applyToBudget);
  if (plan.debtGoalSource) {
    const response = await apiFetch(base, id ? `/planning/debt-plans/${id}` : "/planning/debt-plans", { method: id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token: plan.debtConfirmation, apply_to_budget: applyToBudget }) });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Could not confirm debt plan. Please review it again.");
    return data;
  }
  const response = await apiFetch(base, id ? `/planning/budget-plans/${id}` : "/planning/budget-plans", { method: id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile: plan.profile, choices: plan.budgetChoices ?? {}, budget_fingerprint: plan.budgetFingerprint, request_key: plan.confirmationKey }) });
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(typeof data.detail === "string" ? data.detail : "Could not confirm plan. Please try again."); }
  return response.json();
}

// Spending monitoring and AI budget adjustments (current month)
async function send<T>(base: string, path: string, body: object): Promise<T> {
  const response = await apiFetch(base, `/planning${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again."); }
  return response.json();
}
export const getSpendingStatus = (base: string) => planningRequest<SpendingStatus>(base, "/status");
export const proposeAdjustment = (base: string, instructions?: string, planId?: string) =>
  send<AdjustmentProposal>(base, "/adjustments/proposal", { ...(instructions ? { instructions } : {}), ...(planId ? { plan_id: planId } : {}) });
export const acceptAdjustment = (base: string, proposal: AdjustmentProposal, requestKey: string) =>
  send<SpendingStatus>(base, "/adjustments/accept", { fingerprint: proposal.fingerprint, request_key: requestKey, changes: proposal.changes.map(change => ({ category: change.category, limit: change.limit })) });


export async function acceptReviewedPlan(base: string, plan: FinancialPlan, applyToBudget?: boolean, planId?: string): Promise<FinancialPlan> {
  if (!plan.reviewId) throw new Error("Refresh this Financial Plan before accepting it.");
  const response = await apiFetch(base, "/planning/reviews/" + plan.reviewId + "/accept", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ apply_to_budget: applyToBudget, plan_id: planId }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Could not accept this Financial Plan.");
  return data;
}

export async function rejectReviewedPlan(base: string, plan: FinancialPlan): Promise<{ status: string }> {
  if (!plan.reviewId) throw new Error("Refresh this Financial Plan before rejecting it.");
  const response = await apiFetch(base, "/planning/reviews/" + plan.reviewId + "/reject", { method: "POST" });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Could not reject this Financial Plan.");
  return data;
}
