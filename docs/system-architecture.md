# System architecture

```mermaid
flowchart LR
  Phone[Expo mobile UI] --> API[FastAPI authenticated routes]
  API --> Services[Validation and financial services]
  Services --> DB[(SQLite)]
  Services --> Ollama[Local Ollama]
  Phone --> FX[Public AED exchange-rate feed]
```

[Mobile/App.tsx](../Mobile/App.tsx) owns screen-state navigation and supplies the API base URL. Welcome, Login and Register precede Home. Main tabs expose Home, Transactions, AI Chat, Financial Plans and Insights; dashboard links open Budget Tracker, Spending, Debt, Savings and Settings. This navigation uses component state rather than Expo Router.

Screens and components live in `Mobile/src/screens` and `Mobile/src/components`; styles and theme hooks supply the shared appearance. Theme preferences persist locally and default to dark. Language menus have broader coverage than translated financial content; English, Arabic and Mandarin have the main catalogs. Authentication screens share the PocketPilot palette and form conventions.

[app/main.py](../Backend/app/main.py) registers routers, authentication dependencies and expense/spending endpoints. Routers delegate calculations to services and persist SQLAlchemy models. Pydantic schemas constrain requests. Financial data is scoped to the authenticated user; AI receives a user-specific summary rather than unrestricted database access.

Backend services own canonical AED values, budget/debt calculations, proposal validation, recurring synchronization, planning fingerprints and write locks. The model proposes structured output; it never directly executes SQL or financial actions. Read-only questions suppress actions server-side. Transaction proposals and plan drafts are distinct response types.

The chat session hook manages conversation and goal context. Sending chat and accepting a plan have separate loading states. A plan is marked saved only after its acceptance request succeeds; an older draft remains in history when a later transaction is proposed. Mobile rendering defensively prevents plan controls and transaction controls on one assistant response.

SQLite is a single-file development database. Some GET-driven summaries synchronize due recurring expenses or automatic debt payment entries. This is local ledger synchronization, not a scheduler or bank payment. See [relationships](database.md), [AI state transitions](budget-goal-chat.md) and [API routes](api-documentation.md).
