# Monthly income, categories and Budget Tracker

The Budget Tracker saves monthly income and category targets through `/budget/income` and `/budget/setup`; summaries come from `/budget/monthly`. Records are user- and year/month-specific. New accounts must enter their own income/budget rather than inheriting a fabricated default. Version-2 setup supports named custom categories with case-insensitive uniqueness. Legacy percentage plans remain supported through `/budget/plan`.

Home, Spending and Financial Plans consume the saved budget. Targets represent allocations, not actual expenses. Transactions provide actual spending; allocations can exceed income and leave no available savings. Derived Debt allocations are calculated from obligations rather than independently editable duplicate entries.

Debt inclusion is explicit in the summary service. Home and budget-backed AI goal generation/preview/accept use debt-aware snapshots. Other services may use the non-derived summary and account for actual debt payments or outstanding obligations separately; enabling debt everywhere would double-count in those flows.

Budget-backed planning fingerprints include the effective month, income and normalized category targets, including derived debt. Income, targets, obligations or a month rollover can invalidate an old draft. Actual spending alone is not part of that budget fingerprint; monitoring has its own broader state validation. See [planning](financial-planning.md) and [monitoring](spending-monitoring.md).

## UI and persistence details

Open Budget Tracker from Home/Spending. Select category tiles, enter monthly amounts, or add a custom category; review total allocations and remaining income before saving. Setup accepts 1-50 categories, printable names up to 40 characters, nonnegative two-decimal amounts and income in one transaction. Names are unique ignoring case.

Version-2 category amounts occupy the existing budget JSON field; this is not a new database table. Historical transaction categories are not renamed when a target label changes. Matching is case-insensitive; unmatched costs remain in totals and appear unbudgeted. Budgets are month-specific and are not automatically copied into a new month.

Review my budget with AI sends a specific review period and saved facts. That mode suppresses action/profiling writes; an explanation alone does not change the budget. Explicit monitoring-adjustment acceptance is a separate workflow.

## Income receipts and planning headroom

AI receipts explicitly add to the selected month's saved income total; replacing that total is a separate reviewed operation. Receipts do not establish recurring salary or a separate transaction ledger. Income lookup creates no recording state. Hypothetical income changes stay read-only and distinguish one-time from recurring scenarios.

For a budget-backed savings plan, effective headroom before savings is income minus effective targets plus accepted proposed cuts. Remaining after monthly savings subtracts the proposed contribution once. Debt-aware summaries replace a canonical Debt target with the derived obligation, rather than adding the same obligation twice; arbitrary expense labels/duplicate manually entered payments cannot always be semantically deduplicated. Actual transactions and paid debt are distinct from these planned figures.
