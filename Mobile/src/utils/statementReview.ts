import type { StatementRow } from "../services/statementService";
export type ReviewedStatementRow = StatementRow & { selected: boolean; reviewed: boolean; issues: string[] };
export function prepareStatementRow(row: StatementRow): ReviewedStatementRow {
  const issues: string[] = [];
  if (row.possible_duplicate) issues.push("Possible duplicate. Include only if this is a separate expense.");
  if (row.direction === "debit" && row.kind === "review") issues.push("Check whether this is an expense, a transfer or something to skip.");
  if (row.direction === "debit" && row.kind === "expense" && !row.category.trim()) issues.push("Choose an expense category.");
  return { ...row, issues, reviewed: false, selected: row.direction === "debit" && row.kind === "expense" && issues.length === 0 };
}
export function needsStatementReview(row: ReviewedStatementRow): boolean { return !row.reviewed && row.issues.length > 0; }
export function includedStatementRows(rows: ReviewedStatementRow[]): ReviewedStatementRow[] {
  return rows.filter(row => row.selected && row.direction === "debit" && row.kind === "expense" && !needsStatementReview(row));
}
export function groupStatementRows(rows: ReviewedStatementRow[]): { date: string; rows: ReviewedStatementRow[] }[] {
  const groups = new Map<string, ReviewedStatementRow[]>();
  for (const row of [...rows].sort((a, b) => b.date.localeCompare(a.date) || a.row_id - b.row_id)) groups.set(row.date, [...(groups.get(row.date) ?? []), row]);
  return [...groups].map(([date, items]) => ({ date, rows: items }));
}
