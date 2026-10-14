import { apiFetch } from "./apiClient";
import type { Currency } from "../preferences/currency";

export type StatementRow = {
  row_id: number; date: string; description: string; amount_aed: string;
  source_amount: string; source_currency: Currency; direction: "debit" | "credit";
  kind: "expense" | "income" | "transfer" | "review"; category: string; possible_duplicate: boolean;
};
export type StatementPreview = { preview_token: string; rows: StatementRow[]; errors: { row_id: number; message: string }[]; ai_available: boolean; categories: string[] };
export type StatementSelection = { row_id: number; category: string; include_possible_duplicate: boolean };

async function post<T>(base: string, path: string, body: object): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45000);
  try {
    const response = await apiFetch(base, `/transactions/import/${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: controller.signal });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Could not read this statement. Check the CSV format and try again.");
    return result;
  } finally { clearTimeout(timeout); }
}
export function previewStatement(base: string, body: { csv_text: string; currency: Currency; date_order: "DMY" | "MDY"; amount_style: "negative_debits" | "positive_debits"; aed_to_cny?: number; categories: string[] }) {
  return post<StatementPreview>(base, "preview", body);
}
export function confirmStatement(base: string, preview_token: string, selections: StatementSelection[]) {
  return post<{ added: number; skipped_duplicates: number }>(base, "confirm", { preview_token, selections });
}
