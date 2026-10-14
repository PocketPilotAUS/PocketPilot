# Debt tracking

Home > Debt opens a separate account-owned debt list. Total debt sums current outstanding principal, not the original borrowed amount or future interest. Add, edit and delete debts independently of transactions, budgets and planning profiles.

Required: readable debt name (1–80 characters), outstanding principal (0–1 billion AED, up to two decimals), annual fixed interest rate (0–100%, up to four decimals), remaining years plus extra months (0–11; combined 1–600 months). Zero balance represents a cleared debt. Optional original amount must be positive. Current balance may exceed the original principal: accrued interest or additional borrowing can cause this, so the page explains it instead of showing misleading progress.

All saved money is canonical AED. Input and display use the existing AED/CNY preference and rate; unchanged editor amounts preserve exact stored AED values. Rates and terms are never converted. Original minus outstanding is labeled “Principal reduced,” not total payments made, because interest payments are not recorded here.

Estimated monthly payment uses reducing-balance amortization: `P*r/(1-(1+r)^(-n))`, where `P` is current principal, `r` is annual percentage / 1200, and `n` is remaining months. Zero-interest payment is `P/n`. Estimated remaining interest is `payment*n-P`, calculated before rounding the payment. Assumes fixed nominal interest, monthly payments and no fees. Not suitable for flat-rate, interest-only or variable-rate schedules; these are estimates, not lender quotations. Balances and remaining terms stay as entered until edited; no automatic payoff, transaction recording, budget allocation or savings rollover.

## Backend setup

Existing installations: from Backend, run `./venv/Scripts/python.exe migrate_debts.py` (prefer stopping the server first). It creates a timestamped SQLite backup, adds only the `debts` table and owner index, and is idempotent. Fresh databases obtain the table through `init_db.py`. No existing financial records are rewritten. The API returns a helpful 503 if the table is absent. No new dependencies or environment variables.

Authenticated endpoints: GET/POST `/debts`, PUT/DELETE `/debts/{id}`. Ownership always comes from the verified token; another owner's IDs return 404. Decimal validation rejects non-finite values and sub-cent money. Responses include estimated payment and remaining interest.

## Verification

14 focused tests cover CRUD, owner isolation, authentication, invalid inputs, known amortization values, zero/small rates and backup/idempotent migration. Full backend suite: 370 passed. Mobile TypeScript passes. Lint cannot run because this project has no lint script. Phone layout remains to be reviewed in Expo Go.

Reference: [CFPB: loan amortization](https://www.consumerfinance.gov/ask-cfpb/what-is-amortization-and-how-could-it-affect-my-auto-loan-en-771/).
