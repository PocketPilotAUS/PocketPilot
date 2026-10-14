# CSV bank statement import

This first version adds Import bank statement to Transactions. It reads a small bank CSV, asks the configured Ollama service for transaction type/category suggestions, then shows a review. Nothing is written during preview. Only expenses selected and explicitly confirmed by the user are added to the existing transaction table. Income, incoming credits and transfers are not imported in this version.

## Supported files and setup

Use a UTF-8 CSV with English headers on the first row, at most 50 transaction rows and 128 KB. Comma, semicolon and tab delimiters are detected. Blank rows are ignored. Two layouts are supported:

```csv
Date,Description,Amount
01/10/2026,Restaurant lunch,-25.00
02/10/2026,Salary,5000.00
```

```csv
Date,Description,Debit,Credit,Currency
01/10/2026,Restaurant lunch,25.00,,AED
02/10/2026,Salary,,5000.00,AED
```

Common aliases include Transaction Date, Posting Date, Details, Narrative, Merchant, Transaction Amount, Withdrawal and Deposit. Balance is not treated as a transaction amount. Descriptions may contain quoted commas. Amounts use a decimal point and up to two decimal places; correctly grouped thousands such as `"1,250.50"` and parenthesized negative amounts are supported. Other currency symbols/units and decimal-comma exports need adaptation before importing. Bank-specific column mapping is a future enhancement.

Before choosing a file, the user must choose the actual statement currency (AED or CNY), date order (day first or month first), and the amount-sign convention for a single Amount column. Separate Debit/Credit columns ignore the sign choice and must have one positive nonzero value per row. ISO dates are also accepted. Future/invalid dates, wrong currency and invalid amounts are reported as skipped rows. If no valid rows remain, the CSV is rejected. Files above the row cap are rejected rather than silently truncated. Headers embedded after account summaries, PDF files, photos and spreadsheet workbooks are not supported yet.

Mobile now depends on Expo-compatible `expo-document-picker` and `expo-file-system`. Teammates should run `npm.cmd ci` inside Mobile and restart Metro. Both modules are available in the matching Expo Go SDK; existing custom development builds need rebuilding to include newly added native modules. No additional Python package, database table or migration is needed. Run the matching backend revision and restart a server that is not using auto-reload. The usual JWT signing secret is required; the existing OLLAMA_URL and qwen3:4b model power optional suggestions.

`docs/examples/statement-sample.csv` is synthetic test data, not a real bank statement. Use it with AED, DD/MM/YYYY and Spending is negative to try the flow without personal data.

## Parsing and AI behavior

`Backend/app/services/statement_import.py` deterministically parses dates, debit/credit direction and amounts. It normalizes CNY amounts into AED using the supplied reference rate. Financial values are not extracted or rewritten by AI.

`Backend/app/ai/statement.py` sends only row IDs, descriptions (limited to 150 characters) and debit/credit direction to the configured Ollama endpoint, with a category-constrained JSON schema. It uses qwen3:4b, thinking disabled, an output cap of 2200 tokens and a 25-second HTTP timeout. Descriptions are treated as untrusted data. This is one classification call per preview, not a call on every screen or transaction. Slow/unavailable/malformed AI output falls back to manual review; CSV import does not depend on a successful model response.

High-confidence suggested debit expenses start selected unless they may be duplicates. Low-confidence or missing suggestions require review. Incoming credits can never be confirmed as expenses. Transfer/card-repayment/cash-withdrawal indicators are guarded and start excluded. The user can explicitly reclassify a debit, edit its category, include or exclude it, and opt into a possible duplicate. Categories use the familiar expense labels and any provided current budget categories; custom category text is editable. Dates and amounts remain read-only in review. To correct their interpretation, restart preview with the right export/options or correct the CSV first.

## Duplicate handling and confirmation

Preview flags possible duplicates using the authenticated user's records with the same date and rounded AED amount, and identical rows within the CSV. Possible duplicates start unselected and require explicit inclusion. Confirmation skips exact matches on date, rounded amount and normalized description, including repeated confirmations. This does not use bank transaction reference IDs. Genuinely separate transactions with identical date, amount and description cannot both be imported automatically in this first version; add the extra one manually until reference-based matching is introduced.

`POST /transactions/import/preview` accepts CSV text, statement currency, date order, amount style, optional CNY rate and budget category suggestions. It returns parsed rows, errors, model availability and a signed 20-minute preview token. The token belongs to the authenticated account and fixes the parsed financial facts/rate. It cannot be used as an access token. The server does not store a preview session or the raw CSV.

`POST /transactions/import/confirm` accepts that preview token and selected row IDs/categories with explicit duplicate opt-in. It validates token ownership/expiry, selection uniqueness, category and debit direction before writing. A SQLite immediate transaction serializes confirmations, checks existing records in the selected date range and commits the batch atomically. Another user's data never participates in duplicate checking. Retrying after a lost response skips the exact records already saved. The response reports added and skipped counts.

The frontend deletes only the picker copy under the app cache, never the source bank file. CSV text and preview state are kept only for the active flow; the backend uses the raw text transiently and sends parsed descriptions to its configured Ollama service. Do not commit real statements into this repository. The model endpoint may be local or remote according to OLLAMA_URL; this feature does not move it to a new provider. Source-currency amounts are shown alongside the account's display-currency amounts. CNY conversion rate/date and provider attribution are displayed on the import review.

## Verification and next steps

Automated checks cover CSV formats/signs/dates/currency/limits, read-only preview, AI fallback, duplicate flags and retries, ownership, token tampering, credit rejection, atomic invalid selections and pinned CNY amounts. Mocked mobile checks cover required currency choice, file reading/cache cleanup, conservative row defaults, manual corrections, duplicate opt-in and confirmed selection. A live Ollama smoke check using two synthetic rows returned Food/expense for a restaurant debit and income for salary. Native document picking and real bank export layouts still need testing on a phone.

Next candidates after team review: bank-specific column mapping, larger paged batches, bank reference IDs, income/refund/transfer reconciliation, and PDF text extraction. OCR or a vision-capable model is a separate step for scanned statements and photos.
