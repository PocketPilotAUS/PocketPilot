# User-created monthly budgets

Home shows Create your budget until the current user saves a budget for the displayed month. Recording income alone does not create allocations. Setup uses the same category icons and tile styling as Add Expense. Tapping a tile opens a monthly amount editor; Add to budget includes it and marks the tile with a check. Existing categories can be edited or removed. Add my own category collects a custom name and monthly amount, then makes that category available as a tile. There are no default selections or spending targets in the new flow.

Users enter monthly income and usual monthly amounts, review the total and available income or shortfall, then save. Saved amounts are targets, not paid expense records or savings transfers. A budget can exceed income; the review and tracker explicitly show the shortfall.

PUT `/budget/setup?year=YYYY&month=MM` accepts `income` and 1–50 `categories`, each with `name` and `amount`. Names are trimmed, printable, at most 40 characters and unique ignoring case. Amounts are nonnegative AED with at most two decimal places. Income and budget save in one database transaction.

The existing `budget_plans.percentages` JSON field stores a version 2 payload containing user category amounts. No schema migration is required. Explicitly saved older percentage budgets remain readable and can be edited through the amount form. No budget is generated when a saved row is absent.

Transaction categories match configured categories ignoring case. Unmatched costs are shown separately and remain included in total spending. Custom budget categories are available in Add Expense. Changing a budget's category name does not rename historical transactions, so existing expenses may appear as unbudgeted.

Review my budget with AI opens Chat and sends a request with `review_budget: {year, month}`. The backend reads that user's saved budget and recorded spending. The model is instructed to review affordability and missing costs and give advice. Expense/income proposals and financial-plan extraction are disabled for review requests. Budget changes require the user to edit, review and save them manually.

Budgets apply to one calendar month. A new month requires a new setup; budgets are not automatically copied. The form preserves the current month's saved amounts while editing. AI review requires a configured Ollama service and still needs live quality checks.
