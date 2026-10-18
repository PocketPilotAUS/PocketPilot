import type { FinancialPlan, PlanningProfile } from "./plans";
// AI Chat types (same shapes as the /ai/chat and /ai/proposals API)

export type Proposal = {
  id: string;
  kind: "expense" | "income";
  amount: string | number;
  category?: string;
  date?: string;
  year?: number;
  month?: number;
  status: "pending" | "saved" | "dismissed";
};

export type ChatMessage = {
  currency?: "AED" | "CNY";
  role: "user" | "assistant";
  content: string;
  proposal?: Proposal;
  plan?: FinancialPlan;
  planDeclined?: boolean;
  planningProfile?: PlanningProfile;
  goalPlanning?: boolean;
  budgetRequired?: boolean;
  budgetGoal?: BudgetGoal;
  debtState?: string;
  debtPhase?: string;
};

export type BudgetChoice = { category: string; target: number | null; fingerprint: string };
export type BudgetGoal = {
 ready: boolean; budget_fingerprint: string; income: number; planned_total: number; availableBefore: number; availableAfter: number; missing: string[];
 accepted: { category: string; target: number }[]; protected: string[];
 suggestions: { category: string; baseline: number; target: number; monthlyAmount: number; essential: boolean }[];
 requiredMonthly?: number; unfundedMonthly?: number; feasible?: boolean; progress_known?: boolean;
 scenarioUnfunded?: number; later_deadline?: string | null; scenario_deadline?: string | null; no_surplus?: boolean;
};
