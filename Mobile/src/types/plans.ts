
export const PLAN_CATEGORIES = [
  "Rent",
  "Food",
  "Transport",
  "Bills",
  "Debt payments",
  "Entertainment",
  "Shopping",
  "Subscriptions",
  "Other",
] as const;

export type PlanningProfile = {
  income: number | string | null;
  other_income: number | string | null;
  household_size: number | null;
  goal: string | null;
  goal_kind: "savings" | "debt" | "spending" | null;
  target_amount: number | string | null;
  current_amount: number | string | null;
  deadline: string | null;

  // Your savings planning feature
  preferred_monthly_savings?: number | string | null;

  // Karim's budget-goal planning feature
  monthly_contribution?: number | string | null;

  typical_months: string[];
  expenses: Record<string, number | string | null>;
  protected_categories: string[];
};

export type FinancialPlan = {
  // Karim's budget-goal confirmation fields
  budgetGoalSource?: boolean;
  confirmationKey?: string;
  draftFingerprint?: string;
  budgetFingerprint?: string;
  budgetChoices?: {
    protected: string[];
    targets: Record<string, number>;
    fingerprint?: string;
  };

  id?: string;
  ready: boolean;
  title: string;
  kind: string;
  profile: PlanningProfile;

  income: number;
  baselineSpending: number;
  availableBefore: number;
  availableAfter: number;

  requiredMonthly: number;
  monthlyContribution: number;
  unfundedMonthly: number;
  feasible: boolean;

  targetAmount: number;
  // Saved plans: entered starting amount plus savings assigned to the goal
  savedAmount: number;
  enteredSavedAmount?: number;
  contributedAmount?: number;
  deadline: string | null;
  months: number | null;

  allocations: {
    category: string;
    baseline: number;
    target: number;
    source: string;
  }[];

  spendingCuts: {
    category: string;
    monthlyAmount: number;
    reason: string;
  }[];

  historyComparisons: {
    category: string;
    historicalMonthly: number;
    plannedMonthly: number;
    difference: number;
  }[];

  historyAdvice: string[];
  warnings: string[];
  assumptions: string[];

  // Your preferred savings and deadline calculations
  preferredMonthlySavings?: number | null;
  fundingTarget?: number;
  contributionAffordable?: boolean;
  estimatedMonthsAtPreferred?: number | null;
};

export type PlanningContext = {
  profile: Partial<PlanningProfile>;
  current_income: number | null;
  past_months: Record<string, Record<string, number>>;
  recurring_obligations: Record<string, number>;
  saved_budget?: {
    year: number;
    month: number;
    income: number | null;
    expenses: Record<string, number>;
  } | null;
};
// GET /planning/status — this month's verified spending and goal risk
export type SpendingCategoryStatus = { category: string; budget: number; spent: number; upcoming: number; minimum: number; remaining: number;
  // Expected end-of-month spending and how it was estimated
  forecast: number; method: "fixed" | "pace" | "history" | "pace+history" | "budget" | "adjusted" };
export type SpendingStatus = {
  year: number;
  month: number;
  days_left: number;
  level: 0 | 1 | 2 | 3;
  income: number | null;
  income_missing: boolean;
  has_budget: boolean;
  recorded_spending: number;
  debt_paid: number;
  upcoming_bills: { category: string; amount: number; date: string }[];
  unpaid_debt_due: number;
  committed: number;
  projected_spending: number;
  available_committed: number | null;
  available_projected: number | null;
  required_contributions: number;
  shortfall: number;
  goals: { id: string; title: string; monthlyContribution: number }[];
  over_budget: { category: string; budget: number; spent: number; over: number }[];
  categories: SpendingCategoryStatus[];
  forecast_confidence: "low" | "moderate" | "high";
  history_months: number;
  // Level 2 reasons; buffer = what can still be spent before goal savings become unaffordable
  risk_reasons: ("projection" | "low_buffer")[];
  buffer: number | null;
  still_needed: number | null;
  daily_allowance: number | null;
  fingerprint: string;
  adjustments: { request_key: string; accepted_on: string; changes: { category: string; current: number; proposed: number; limit?: number; avoided?: number }[] }[];
};

// POST /planning/adjustments/proposal — validated, never applied until accepted.
// Limits are month-end spending caps; "avoided" is projected future spending the
// user can avoid by keeping to a limit, never money already saved.
export type SpendingLimit = { category: string; budget: number; spent: number; upcoming: number; forecast: number; limit: number;
  remaining_allowance: number; avoided: number; budget_after: number; reason: string };
// catch_up: same deadline, higher monthly amount later; extend: later deadline (plan_monthly is what the plan editor will calculate)
export type PlanOption = { kind: "catch_up" | "extend"; this_month: number; monthly: number; deadline: string; months?: number; plan_monthly?: number };
export type PlanSuggestion = { monthly?: number; deadline?: string };
export type AdjustmentProposal = {
  // advice: level 1, goal affordable (tips only); adjust: level 2; recovery: level 3
  mode: "advice" | "adjust" | "recovery";
  tips: string[];
  affordability: { income?: number | null; expected_spending?: number; left_after_spending?: number; required_contributions?: number; left_after_savings?: number };
  fingerprint: string;
  level: number;
  days_left: number;
  changes: SpendingLimit[];
  notes: string[];
  covers: boolean;
  required_contributions: number;
  forecast_confidence: "low" | "moderate" | "high";
  forecast_reliable?: boolean;
  assumption?: string;
  options: PlanOption[];
  current_shortfall?: number;
  forecast_shortfall?: number;
  potential_reduction?: number;
  remaining_shortfall?: number;
  max_this_month?: number;
  // Low-buffer warnings: budget still needed this month minus what can be spent
  spending_gap?: number | null;
  risk_reasons?: ("projection" | "low_buffer")[];
  buffer?: number | null;
  still_needed?: number | null;
  daily_allowance?: number | null;
};
