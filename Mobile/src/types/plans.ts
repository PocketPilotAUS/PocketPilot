// Shape for structured financial plans, ready for when plans can be saved.
// The app has no plan storage yet, so no plans exist and none are invented.

export type PlanSpendingCut = {
  category: string;
  monthlyAmount: number; // AED per month
};

export type FinancialPlan = {
  id: string;
  title: string;
  kind: "savings" | "debt" | "spending";
  targetAmount: number; // AED
  savedAmount: number; // AED recorded towards the target
  deadline: string | null; // YYYY-MM-DD
  monthlyContribution: number | null; // AED per month
  spendingCuts: PlanSpendingCut[];
};
