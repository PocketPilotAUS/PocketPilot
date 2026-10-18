# PocketPilot developer documentation

These guides describe the current source on fix/ai-natural-language. Start with the root README for complete Windows setup; database/migration directories retain their existing layout. Historical handoff logs are retained as records, not current specifications.

| Topic | Guide |
| --- | --- |
| Setup, configuration, networking | [Development](development.md) |
| Architecture and navigation | [System architecture](system-architecture.md) |
| Implemented, partial and absent features | [Requirements and status](requirements.md) |
| SQLite relationships and migrations | [Database](database.md) |
| Routes and request schemas | [API reference](api-documentation.md) |
| Account and session behavior | [Account settings](account-settings.md), [token refresh](automatic-token-refresh.md) |
| Income, categories, Budget Tracker | [User budgets](user-budgets.md) |
| Debts and payment ledger | [Debts](debts.md), [payments](debt-payments.md) |
| Goals and contributions | [Savings](savings.md) |
| Guided and budget-backed plans | [Financial planning](financial-planning.md) |
| AI intent, proposals and confirmation | [AI Chat](budget-goal-chat.md) |
| Risk, adjustments and recovery | [Spending monitoring](spending-monitoring.md) |
| Calculations and safeguards | [Core algorithms](core-algorithms.md) |
| Statement import | [CSV import](statement-import.md) |
| Currency and preferences | [Currency display](currency-display.md) |
| Security | [Design](security-design.md), [assessment](security-self-assessment.md) |
| Validation | [Testing](testing.md) |

Historical records: [phase 2](phase-2-handoff-log.md), [phase 3](phase-3-handoff-log.md). Start installation from the [root README](../README.md).

Current confirmation safety uses separate transaction and Financial Plan registries. See [AI Chat](budget-goal-chat.md), [Financial Plans](financial-planning.md), and the required [review-table setup](database.md). The owner reports planned physical-device C1?C7 tests passed; [testing](testing.md) distinguishes that report from mocked and live automated evidence.
