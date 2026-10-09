# Mobile Authentication Integration: Handoff

**For:** Mahmoud and Karim (mobile)
**From:** Khaled (backend authentication, branch `feature/khaled`)

## Summary

The mobile app is now connected to backend authentication. The old demo login (accounts stored on the phone in AsyncStorage) has been replaced:

- Sign-up and sign-in call the FastAPI backend (`/auth/register`, `/auth/login`, `/auth/me`).
- The login token (JWT) is stored with `expo-secure-store` (iOS Keychain / Android Keystore), never in AsyncStorage.
- Every transaction and spending request sends `Authorization: Bearer <token>`.
- Each user only sees, adds, deletes and summarises their own transactions.
- Expired or invalid sessions return the user to the sign-in screen with a "Session expired" message.

**The UI is unchanged.** No styles, components, theme or navigation were changed. The only visible text changes:

| Screen | Before | After |
|---|---|---|
| Login, Register (footer) | "Demo authentication only. Use fictional credentials." | "Development build. Use test credentials only." |
| Register (password placeholder) | "At least 6 characters" | "At least 8 characters" |

## What you need to do

1. **Review** the changes on `feature/khaled` (files listed below), especially `App.tsx` and the transaction screens.
2. **Install the new dependency** after pulling:

   ```bash
   cd Mobile
   npm install
   ```

   `expo-secure-store` is included in Expo Go, so Expo Go keeps working without a development build.
3. **Set up the backend** (once per computer; full steps in the main [README](../README.md)):
   - Create `Backend/.env` from `Backend/.env.example` and generate your own `JWT_SECRET_KEY`.
   - If you already have a `Backend/pocketpilot.db`: stop the server and run `python migrate_add_users.py` (it backs up first). Otherwise run `python init_db.py`.
4. **Set `API_BASE_URL`** in `Mobile/App.tsx` to your computer's LAN address, as before.
5. **Create a new account in the app.** Old demo accounts are not transferred (they only existed on the phone), and transactions created before the migration stay hidden from every account.
6. **Run the manual test checklist** (section 5) on a real phone.

## 1. Files changed

| File | Change |
|---|---|
| `src/services/tokenStorage.ts` | **New.** Saves, reads and clears the token with SecureStore. On web (no SecureStore) the token is kept in memory only. |
| `src/services/apiClient.ts` | **New.** `apiFetch()` adds the Bearer token to protected requests. On HTTP 401 it clears the token, notifies `App`, and throws `SessionExpiredError`. |
| `src/services/authService.ts` | **Rewritten.** `register`, `login`, `restoreSession`, `logout` call the backend. The `DemoUser` type is now `AuthUser`. |
| `App.tsx` | Restores the session from the saved token on start-up; returns to sign-in when a session expires; dashboard summary uses `apiFetch`; passes `apiBaseUrl` to the Login and Register screens. |
| `src/screens/LoginScreen.tsx`, `RegisterScreen.tsx` | New `apiBaseUrl` prop; text changes above. Form logic and layout unchanged. |
| `src/screens/AddTransactionScreen.tsx` | Uses `apiFetch`; checks the backend's maximum amount (AED 1,000,000,000); separates server errors from connection errors. |
| `src/screens/TransactionHistoryScreen.tsx` | Uses `apiFetch` for loading and deleting. A 404 on delete (already deleted elsewhere) removes the item instead of showing an error. |
| `package.json`, `package-lock.json`, `app.json` | Adds `expo-secure-store ~57.0.4` and its config plugin (added automatically by `npx expo install`). |

## 2. How it works

### Sign-up and sign-in

- **Register** (`authService.register`) checks the input in the app first, using the backend's rules, then calls `POST /auth/register`. The backend does not return a token when registering, so the app signs in straight afterwards. The user lands on the dashboard as before.
- **Login** (`authService.login`) calls `POST /auth/login`, then loads the profile with `GET /auth/me` before saving the token.
- Error messages:

| Situation | Message |
|---|---|
| Wrong password or unknown email | "Incorrect email or password." (the same for both, on purpose) |
| Email already registered | "An account with this email already exists." |
| Backend unreachable | "Could not connect to PocketPilot backend. Check that FastAPI is running." |
| Backend misconfigured (HTTP 503) | "PocketPilot is temporarily unavailable. Please try again later." |
| Account created, but the automatic sign-in failed | "Your account was created, but signing in failed. Please sign in." |

### Validation rules (same as the backend)

| Field | Rule |
|---|---|
| Name | 1–100 characters after trimming |
| Email | `^[^\s@]+@[^\s@]+\.[^\s@]+$`, up to 254 characters; trimmed and lowercased |
| Password | **8–128 characters** (was 6), never trimmed |

Invalid input is rejected in the app without contacting the backend. The backend checks again regardless.

### Token storage

- Key `pocketpilot_access_token` in SecureStore, with `keychainAccessible: WHEN_UNLOCKED_THIS_DEVICE_ONLY`, so the token is not included in device backups or restored onto another phone.
- The password is never stored.
- The old demo keys `@pocketpilot_demo_accounts` (which held **plain-text passwords**) and `@pocketpilot_demo_session` are deleted on every app start and logout. No other AsyncStorage data is touched.
- **Web:** SecureStore does not support web, so the token is kept in memory only (not `localStorage`). Users sign in again after reloading the page.

### Sending the token

Use `apiFetch` for every protected request. It works like `fetch`, but takes the API base URL and a path:

```ts
import { apiFetch, SessionExpiredError } from "../services/apiClient";

try {
  const response = await apiFetch(apiBaseUrl, "/transactions/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ amount, category, description, date }),
  });
  // ...check response.ok as usual
} catch (error) {
  // App already returned to sign-in; don't show another error
  if (error instanceof SessionExpiredError) return;
  // ...connection error handling as usual
}
```

**When adding new screens that call the API** (e.g. recommendations), use `apiFetch` and the same `SessionExpiredError` check. Only send the fields the backend expects: unknown fields (including `user_id`) are rejected with HTTP 422. The owner is always taken from the token.

### Sessions

| Event | Behaviour |
|---|---|
| App start, valid token | `GET /auth/me` succeeds → dashboard |
| App start, expired or invalid token | Token removed → welcome screen |
| App start, no token | Welcome screen |
| App start, backend unreachable (8-second limit) | Token kept → dashboard with the usual connection error; the next request either works or returns to sign-in |
| Any request gets HTTP 401 | Token removed → sign-in screen with "Session expired" alert (shown once, even if several requests fail together) |
| Log out | Token removed → welcome screen |

A dashboard summary that is still loading when the user leaves the dashboard (for example, logs out) is discarded, so one user's totals can never appear for the next user on the same phone.

Tokens last 30 minutes by default (`ACCESS_TOKEN_EXPIRE_MINUTES` in `Backend/.env`, up to 1440). There are no refresh tokens yet, so the user signs in again after that.

## 3. Checks already run

- **TypeScript:** `npx tsc --noEmit` passes with no errors.
- **Expo Doctor:** `npx expo-doctor` reports 21/21 checks passed.
- **Lint:** the project has no ESLint setup yet, and running `npx expo lint` for the first time would add one, so I ran it on a temporary copy. The changed files have **no lint errors**. Their 3 warnings were already there (a duplicate `ThemeContext` import and the unused `currentUser` state in `App.tsx`). Separately, `src/components/AnimatedWelcome.tsx` already has 10 `react-hooks/refs` errors, which I did not change.
- **Service tests against the real backend:** the real `authService`, `apiClient` and `tokenStorage` code was bundled with in-memory stand-ins for SecureStore, AsyncStorage and Platform, and run against a real FastAPI server. **38/38 checks passed**, covering:
  - removal of the old demo data
  - app-side validation
  - sign-up with automatic sign-in
  - duplicate emails
  - token storage options
  - session restore
  - the same message for a wrong password and an unknown email
  - logout
  - two users with separate data
  - deleting another user's transaction (404, not a logout)
  - invalid tokens
  - the backend being unreachable
  - a real token expiring after 1 minute
  - a sign-in failure straight after a successful sign-up

  This test lives outside the repository. The Mobile project has no JavaScript test framework yet.

## 4. Device testing so far

Khaled tested the app in **Expo Go on an iPhone** against a local backend. These worked:

- sign-up
- login
- logout
- adding, viewing and deleting transactions
- separation between two accounts

**Not yet tested on a device:**

- session expiry
- starting the app while the backend is stopped
- the "Session expired" alert
- Android

These, and the full checklist below, still need to be checked before release.

## 5. Manual test checklist (Expo Go on a phone)

**Registration and login**

- [ ] Register a new account → lands on the dashboard (signed in automatically)
- [ ] Register the same email again, including different capitalisation (`Alice@Example.com`) → "already exists" message
- [ ] Register with a 7-character password → blocked in the app with the 8-character message
- [ ] Register with an invalid email, blank name, or mismatched passwords → clear message
- [ ] Log in with a wrong password, and with an unknown email → the same "Incorrect email or password." message
- [ ] Log in with different email capitalisation → works
- [ ] Stop the backend and try to log in → connection message, no crash

**Session handling**

- [ ] Close and reopen the app → still signed in
- [ ] Log out → welcome screen; reopening the app shows the welcome screen
- [ ] Token expiry: set `ACCESS_TOKEN_EXPIRE_MINUTES=1` in `Backend/.env`, restart the backend, log in, wait over a minute, then open History → one "Session expired" alert and the sign-in screen, with no endless loading
- [ ] Change `JWT_SECRET_KEY` and restart the backend → app returns to sign-in on the next request
- [ ] Start the app while the backend is stopped (with a saved session) → dashboard shows the connection error within about 8 seconds; start the backend and reopen the dashboard → data loads

**Data isolation (two accounts)**

- [ ] User A adds transactions; log out; user B sees an empty history and a zero dashboard
- [ ] User B adds different transactions; log back in as A → A sees only A's data and the correct totals
- [ ] Delete a transaction as A → B's data unchanged
- [ ] Transactions from before the migration don't appear for any account

**Existing features (regression)**

- [ ] Add a transaction with each category, a custom category, with and without a description
- [ ] Amount validation: empty, 0, negative, and above 1,000,000,000 are blocked
- [ ] History lists newest first and deletes with the confirmation dialog
- [ ] Dashboard total and category breakdown are correct
- [ ] Theme toggle and all navigation (Welcome, Login, Register, Dashboard, Add, History, Back buttons) still work

## 6. Known limitations

- **Plain HTTP during development:** passwords and tokens travel unencrypted on the local network. Use only test accounts and made-up data. Production needs HTTPS.
- **No refresh tokens:** users sign in again when the token expires (30 minutes by default).
- **No password reset, password change, email verification or server-side logout** yet. Logging out removes the token from the phone; an already-copied token stays valid until it expires.
- **`API_BASE_URL` is still hard-coded** in `App.tsx`, as before.
- **The dashboard doesn't show the user's name yet.** `currentUser` (`id`, `name`, `email`, `created_at`) is available in `App.tsx` if you want to add it.

Backend API details: [api-documentation.md](api-documentation.md). Questions about the backend side: contact Khaled.
