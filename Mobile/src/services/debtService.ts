import { apiFetch } from "./apiClient";
export type DebtInput = { name: string; balance: number; annual_rate: number; remaining_months: number; original_principal: number | null };
export type Debt = DebtInput & { id: number; estimated_monthly_payment: number; estimated_remaining_interest: number };
async function request(base: string, path: string, method = "GET", body?: DebtInput) {
  const response = await apiFetch(base, path, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === "string" ? data.detail : "Could not save or load debts. Check your inputs and try again.");
  }
  return response.status === 204 ? undefined : response.json();
}
export const loadDebts = (base: string): Promise<Debt[]> => request(base, "/debts");
export const saveDebt = (base: string, body: DebtInput, id?: number): Promise<Debt> => request(base, id == null ? "/debts" : `/debts/${id}`, id == null ? "POST" : "PUT", body);
export const removeDebt = (base: string, id: number): Promise<void> => request(base, `/debts/${id}`, "DELETE");
