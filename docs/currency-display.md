# AED and Chinese yuan

Settings Currency offers AED and CNY. Selecting CNY converts all supported financial screens, including previous transaction history, monthly income, budget amounts, recurring schedules, chart labels and financial plans. It does not rewrite the database. Switching back shows the original AED amounts.

## Data and input units

The backend and database remain canonical AED. Mobile money inputs use the selected currency; saves divide CNY inputs by the cached AED-to-CNY rate and round to AED cents. Unchanged editor amounts preserve their original stored value when it corresponds to the displayed rounded draft. New conversions may differ by a displayed cent due to the two-decimal storage precision. Percentages, dates, household counts, month numbers and user descriptions are not converted. Saved amount targets remain budget targets, not transactions.

`Mobile/src/preferences/currency.ts` owns conversion helpers and currency-aware monetary UI text. `LocalizedNative.tsx` converts canonical AED amounts before localization, preserving the Mandarin/Arabic catalogs. User-entered text using `localize={false}` opts out. Already-converted draft summaries and chart numbers use dedicated helpers to avoid conversion twice. API responses and client calculation objects stay in AED, so ratios and totals use the existing consistent base units.

## Preference and rates

`PreferencesContext.tsx` stores one currency/rate object under `@pocketpilot_currency` through AsyncStorage. The UI waits for preference restoration before rendering financial forms. No currency table, database migration, new environment setting or native dependency is needed. Currency is device-local and is not synchronized to other devices.

`services/currencyService.ts` requests `https://open.er-api.com/v6/latest/AED` directly without authentication or financial data. It validates the base currency, CNY rate and update timestamps, has a 12-second timeout and reuses a cached rate until the provider's next update time. The service's public reference feed updates daily, not continuously. No paid account or key is configured.

The rate date and clickable Rates By Exchange Rate API attribution are displayed on financial screens and in Settings. All historical records use this same current/cached reference rate, not transaction-day exchange rates. These are approximate reference conversions, not bank quotes or settlement rates. An already selected CNY preference can display cached amounts offline, and an expired cache is marked Cached rate. Selecting CNY without a usable cached rate requires internet. If loading or saving fails, the previous preference remains selected. Refresh exchange rate reuses a still-current cache; once it expires, it fetches an updated rate.

Provider documentation and terms: https://www.exchangerate-api.com/docs/free and https://www.exchangerate-api.com/terms. Keep the required attribution when changing the UI or provider integration.

## AI chat

The updated backend accepts `currency: "AED" | "CNY"` and `aed_to_cny` on `/ai/chat`. CNY requires a finite positive validated rate. The mobile app includes its selected currency and cached rate, labels each user message's implicit units, and keeps older message units explicit when switching currencies. Previous user-entered chat text itself is preserved.

For CNY requests, the backend projects the authenticated user's financial context into CNY before sending it to Ollama. It asks for CNY replies and CNY action/planning money fields. It deterministically converts structured model drafts back to AED before existing validation, planning calculations and proposal creation. Returned structured proposals/profiles/plans remain AED. A chat action still requires user confirmation; conversion itself does not write a transaction or planning profile. Review-budget requests still suppress action and planning writes. Other currencies are rejected.

Deploy or run the matching frontend and backend revision together and restart an API server that is not using auto-reload. Older strict chat schemas do not accept the new request fields. Live model currency interpretation still needs a manual check; the automated tests mock model replies.

## Verification

The backend suite passed with 341 tests, including currency validation, immutable context projection, non-money fields, CNY proposal confirmation and planning draft normalization without persistence. Mobile typechecking and local component checks cover currency preference storage/failure, rate validation/cache/failure, localization, display conversion, budget drafts/review/save, expense and recurring saves, and planning money fields. The public AED endpoint was checked successfully. Native phone layout and a live Ollama CNY conversation remain manual review items.
