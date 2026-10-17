# Account settings

Open the gear button on Home. Personal details supports name, email and an optional contact phone number. Phone numbers accept spaces, parentheses and hyphens, and are stored as 7 to 15 digits with an optional leading plus. This feature does not verify ownership of email or phone by OTP.

Settings now opens a menu with Personal Details, Language, Currency and Preferences. Each row opens its own section; Back returns to the menu. Personal Details keeps the profile/password API behavior described below and confirms discarding unsaved changes.

Language offers 21 widely spoken languages with search by English or native name. Mandarin and Arabic have local UI catalogs covering forms, dashboard, transactions, planning, placeholders and alerts. Arabic uses right-to-left layout. Other languages currently translate menu headings and bottom navigation only. Language selection is saved per device through AsyncStorage. New AI chat and insights requests include the selected language, so Ollama is instructed to answer in it; existing conversations and user-entered descriptions/goals are preserved. Backend-controlled proposal, clarification and pending-plan text currently remains English. Live model output still needs language-quality review.

Currency offers AED and Chinese yuan (CNY). Original financial records remain in AED. Selecting CNY converts history, income, budgets, plans and financial display amounts using a dated reference rate; new form amounts are entered in CNY and normalized to AED before saving. The choice and rate are device-local. See [currency display](currency-display.md) for rates, rounding, offline behavior and the chat request contract.

Preferences provides light/dark appearance. It applies across the app and is saved per device. The old dashboard theme toggle has been removed.

Email changes require the current password and reject an email already used by another account. The account ID stays the same, preserving ownership of financial records. The next login uses the updated email.

Password changes require the current password and a different new password of 8 to 128 characters. The frontend also requires confirmation. Passwords use the existing Argon2 hashing. Changing a password increments the account's token version, invalidating previously issued tokens on all devices, then returns the current device to login.

API routes:

- GET `/auth/me` includes nullable `phone`.
- PATCH `/auth/me` accepts `name`, `email`, `phone`, and optional `current_password` required for email changes.
- POST `/auth/password` accepts `current_password` and `new_password`, returning 204 on success.

For a fresh database, `python init_db.py` registers the new `account_settings` table with the other models. For an existing database missing this table, inspect and back up first (see [database maintenance](database.md)), stop the backend and run from Backend:

```powershell
.\venv\Scripts\python.exe migrate_account_settings.py
```

The migration backs up the SQLite database before adding the settings table and can be repeated. It does not change existing user or financial tables. Settings tests use isolated databases.
