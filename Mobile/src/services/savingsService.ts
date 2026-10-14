import { apiFetch } from "./apiClient";
export type SavingsMonth = { year: number; month: number; income: number; spent: number; extra_debt_payments: number; saved: number; leftover: number };
export type ManualSavings = { id: number; label: string; amount: number };
export type SavingsOverview = { year: number; month: number; income: number | null; spent: number; can_confirm: boolean; total_saved: number; manual_total: number; manual_entries: ManualSavings[]; history: SavingsMonth[] };
async function request<T>(base: string, path: string, method = "GET", body?: object): Promise<T> {
  const response = await apiFetch(base, path, { method, ...(body ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}) });
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(typeof data.detail === "string" ? data.detail : "Could not load or confirm savings. Please try again."); }
  return response.status === 204 ? undefined as T : response.json();
}
export const loadSavings = (base: string, year: number, month: number) => request<SavingsOverview>(base, `/savings?year=${year}&month=${month}`);
export const confirmSavings = (base: string, body: { year: number; month: number; extra_debt_payments: number; expected_income: number; expected_spent: number }) => request<SavingsMonth>(base, "/savings/confirm", "PUT", body);
export const saveManualSavings = (base: string, body: { label: string; amount: number; request_key?: string }, id?: number) => request<ManualSavings>(base, id == null ? "/savings/manual" : `/savings/manual/${id}`, id == null ? "POST" : "PUT", body);
export const deleteManualSavings = (base: string, id: number) => request<void>(base, `/savings/manual/${id}`, "DELETE");
