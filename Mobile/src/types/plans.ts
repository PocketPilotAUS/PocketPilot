
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
  savedAmount: number;
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
};
