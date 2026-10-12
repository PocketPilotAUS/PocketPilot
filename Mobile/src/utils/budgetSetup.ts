export type BudgetCategoryDraft = { name: string; amount: string };
export function validateBudgetSetup(income: string, categories: BudgetCategoryDraft[]): string | null {
  const money = (value: string) => /^\d+(\.\d{1,2})?$/.test(value.trim()) && Number(value) <= 1000000000;
  if (!money(income)) return "Enter your monthly income, or 0 if you have none.";
  if (!categories.length || categories.length > 50) return "Add between 1 and 50 budget categories.";
  const names = new Set<string>();
  for (const row of categories) {
    const name = row.name.trim();
    if (!name || name.length > 40 || /[\x00-\x1f\x7f]/.test(name)) return "Each category needs a name of 1 to 40 characters.";
    if (names.has(name.toLocaleLowerCase())) return "Each category must have a different name.";
    names.add(name.toLocaleLowerCase());
    if (!money(row.amount)) return "Enter an amount for every category, or remove categories you do not need.";
  }
  return null;
}
