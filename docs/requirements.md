# Feature status and known limitations

Status reflects implemented code, not a product roadmap promise.

| Area | Status and scope |
| --- | --- |
| Accounts | Implemented: registration/login, profile/password changes, rotating refresh, logout; no password recovery or email verification |
| Monthly budgeting | Implemented: saved monthly income, custom category targets, Budget Tracker, legacy percentage plans |
| Expenses | Implemented: add/list/delete, spending summary/comparison, CSV preview/import; no generic editing endpoint |
| Recurring expenses | Implemented: create/edit/stop and due-entry synchronization; no background push reminders |
| Debts | Implemented: installment estimates, balances, manual/automatic local payment entries; no bank execution |
| Savings | Implemented: saved plans/goals, manual contributions, completed-month snapshots; not a bank balance |
| Financial Plans | Implemented: guided forms, AI drafts, previews, acceptance, adjustment, rejection and fingerprints |
| Monitoring | Implemented: deterministic risk levels, AI adjustment/recovery proposals and validated target changes |
| AI Chat | Implemented: semantic interpretation, grounded expense/income proposals, saved-debt advice, affordability, follow-ups and topic switching; validation remains conservative |
| Currency/language/theme | Implemented preferences and AED/CNY conversion; localization is partial and rates are not historical transaction rates |
| Statement import | Implemented bounded UTF-8 CSV expense import; no PDF/OCR or automatic income import |
| Deployment hardening | Partial: authentication and scoping exist; no supplied rate limiting, production operations or independent security audit |

AI output is probabilistic. Server gates reject unsupported or insufficiently evidenced recording actions, but broad natural-language understanding is not guaranteed. Ambiguous amounts/categories require clarification. AI cannot edit an existing transaction or record a savings contribution through the income/expense proposal interface; use the dedicated screens.

A plan allocation is not a contribution, a debt installment estimate is not a paid transaction, and a confirmed monthly savings snapshot is not a live bank balance. Recurring/automatic debt entries synchronize on application requests, not continuously. There are no shared accounts, bank connections, real payment transfers or push notifications implemented.

The legacy planning test expecting rejection of an unknown category conflicts with implemented custom-category support. See [testing](testing.md). Historical logs contain earlier milestones and are not evidence that an absent feature is complete. Future functionality listed as absent here is not a delivery commitment.


Current safety behavior includes multiple independent transaction proposals, generic-acknowledgment handling, immediate explicit cancellation, persisted plan rejection/expiry, current-chat status references and stale/idempotent/concurrent acceptance checks. Completed plan acceptance does not fabricate deposits, income or debt payments. The project owner reports physical-device C1?C7 tests passed; automated/live model evidence is described separately in [testing](testing.md).

No configurable per-account timezone is implemented; relative financial dates use server UAE UTC+4. Income add/replace operations update a month-specific total, not a separate income ledger or recurring salary schedule. The welcome screen retains only the transparent logo, title, turquoise subtitle and smaller centered button.
