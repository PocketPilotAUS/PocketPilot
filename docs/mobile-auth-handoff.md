# Mobile Handoff: Connecting the App to Backend Authentication

**For:** Mahmoud and Karim (mobile)
**From:** Khaled (backend authentication, branch `feature/khaled`)

## Summary

The backend now has real user accounts. Every transaction, spending and recommendation endpoint requires a login token, and each user only sees their own data.

**What this means for the app:**

1. Until the app sends a token, every financial request returns **HTTP 401**. The dashboard, history and add-transaction screens will stop working against the new backend.
2. The demo login in `Mobile/src/services/authService.ts` must be replaced with calls to the backend.
3. **Transaction request and response bodies are unchanged.** The only change for those screens is adding an `Authorization` header and handling 401.

The backend and mobile changes should be merged together, so the app is never pointed at a backend it cannot log in to.

## What needs to change

| File | Change |
|---|---|
| `src/services/authService.ts` | Replace the demo AsyncStorage accounts with `POST /auth/register`, `POST /auth/login`, `GET /auth/me`; store the token in SecureStore |
| `App.tsx` | Restore the session from the stored token on start-up; send the token for `/spending/summary`; return to login on 401 |
| `src/screens/AddTransactionScreen.tsx` | Add the `Authorization` header to `POST /transactions/` |
| `src/screens/TransactionHistoryScreen.tsx` | Add the `Authorization` header to `GET /transactions/` and `DELETE /transactions/{id}` |
| `src/screens/RegisterScreen.tsx`, `LoginScreen.tsx` | Align validation and error messages (see below) |

Follow `Mobile/AGENTS.md`: install packages with `npx expo install`, keep styles in `src/styles/`, and keep the current screen-state navigation.

## 1. API calls

Full reference: [api-documentation.md](api-documentation.md).

### Register

```http
POST /auth/register
Content-Type: application/json

{"name": "Alice Smith", "email": "alice@example.com", "password": "correct-horse-1"}
```

| Status | Meaning | Suggested message |
|---|---|---|
| 201 | Account created. Body: `{"id", "name", "email", "created_at"}` | Then log in automatically (below) |
| 409 | Email already registered | "An account with this email already exists." |
| 422 | Invalid field (`detail[].loc[1]` names the field) | Show the field's rule (see section 5) |

Registering **does not return a token**. To keep the current "register then go to dashboard" behaviour, call login straight after a successful registration with the same email and password.

### Log in

```http
POST /auth/login
Content-Type: application/json

{"email": "alice@example.com", "password": "correct-horse-1"}
```

Successful response (200):

```json
{"access_token": "eyJhbGciOi...", "token_type": "bearer", "expires_in": 1800}
```

A wrong email or password returns 401 with `{"detail": "Incorrect email or password."}`. Show exactly that message. The backend deliberately does not say which part was wrong.

### Current user

```http
GET /auth/me
Authorization: Bearer <access_token>
```

Returns `{"id", "name", "email", "created_at"}`. Use this to restore the session on app start and to get the user's name for the dashboard. Note that `id` is now a **number**, whereas `DemoUser.id` is currently a string.

## 2. Storing the token securely

- **Store the token with `expo-secure-store`, not AsyncStorage.** AsyncStorage is unencrypted. SecureStore uses the iOS Keychain and Android Keystore, and is included in Expo Go (SDK 57).

  ```bash
  npx expo install expo-secure-store
  ```

- **Never store the password.** Once the backend handles login, remove the `@pocketpilot_demo_accounts` key. It currently holds **plain-text passwords** in AsyncStorage. Delete it (and `@pocketpilot_demo_session`) once on start-up so existing test devices are cleaned up.
- SecureStore does not support **web**. If the web build must work, keep the token in memory only there (the user logs in again after a reload), rather than falling back to `localStorage`.

Example (adapt to the existing code style):

```ts
import * as SecureStore from "expo-secure-store";

const TOKEN_KEY = "pocketpilot_access_token";

export async function saveToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function clearToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}
```

`WHEN_UNLOCKED_THIS_DEVICE_ONLY` keeps the token out of device backups. A copied token should not log someone in on another phone.

## 3. Sending the token

Every request except register and login needs this header:

```http
Authorization: Bearer <access_token>
```

A single helper keeps this consistent:

```ts
export class UnauthorizedError extends Error {}

export async function apiFetch(
  apiBaseUrl: string,
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getToken();

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers: {
      ...(options.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (response.status === 401) {
    await clearToken();
    throw new UnauthorizedError("Session expired");
  }

  return response;
}
```

The transaction bodies stay exactly as they are today:

```ts
await apiFetch(apiBaseUrl, "/transactions/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ amount, category, description, date }),
});
```

**Only send `amount`, `category`, `description` and `date`.** Any extra field (including `user_id`) is rejected with 422. The owner is always taken from the token.

## 4. Expired tokens and 401 responses

- Tokens expire after `expires_in` seconds (30 minutes by default). There are no refresh tokens yet, so the user logs in again.
- On **any 401** from a protected endpoint: clear the token, reset `currentUser`, and show the login screen with a message such as "Your session has expired. Please log in again." Do not show the current "Check that FastAPI is running" message for 401; that should stay for network errors only.
- **On app start:** if a token is stored, call `GET /auth/me`. A 200 restores the session (go to the dashboard); a 401 means the token expired (clear it and show welcome/login). This replaces `getCurrentUser()` reading AsyncStorage.
- **Logout:** clear the token from SecureStore. There is no logout endpoint; the old token simply expires.
- **404 on delete** means the transaction no longer exists (for example, it was deleted on another device). Refresh the list.
- **503** means a server problem (for example, the backend's `JWT_SECRET_KEY` is not set). Show a generic "Service unavailable" message.

## 5. Validation rules to match the backend

The backend is the source of truth, but matching its rules in the app gives users instant feedback.

| Field | Backend rule | Current app rule | Change |
|---|---|---|---|
| Password | **8–128** characters, kept exactly as typed | at least 6 | Change minimum to 8, add maximum 128, and show the rule under the field |
| Email | `^[^\s@]+@[^\s@]+\.[^\s@]+$`, max 254, trimmed and lowercased | same regex, trimmed and lowercased | Add the 254 maximum |
| Name | 1–100 characters after trimming | non-empty after trimming | Add the 100 maximum |

- Don't trim passwords: `" pass word "` is a different password from `"pass word"`.
- Login only checks that fields are non-empty; don't apply the registration rules there.

## 6. Development setup

Each developer running the backend needs to:

1. Create `Backend/.env` from `Backend/.env.example` and generate a `JWT_SECRET_KEY`. Never commit or share it.
2. If you already have a `Backend/pocketpilot.db`, **stop the server and run `python migrate_add_users.py`** once (it backs up first).
3. Transactions you created before this change become **unowned and hidden**. That is expected. Register a new test account and add new test data.

Full instructions are in the main [README](../README.md).

## 7. Mobile testing checklist

**Registration and login**

- [ ] Register a new account → lands on the dashboard (register, then automatic login)
- [ ] Register the same email again, including different capitalisation (`Alice@Example.com`) → "already exists" message
- [ ] Register with a 7-character password → blocked in the app, and the backend returns 422 if sent
- [ ] Register with an invalid email or blank name → clear message
- [ ] Log in with a wrong password, and with an unknown email → the same "Incorrect email or password." message
- [ ] Log in with different email capitalisation → works

**Session handling**

- [ ] Close and reopen the app → still logged in (token restored, `/auth/me` succeeds)
- [ ] Log out → token removed; reopening the app shows the welcome screen
- [ ] Token expiry: set `ACCESS_TOKEN_EXPIRE_MINUTES=1` in `Backend/.env`, restart the backend, log in, wait over a minute, then open history → "session expired" and returned to login, with no crash and no endless loading
- [ ] Changing `JWT_SECRET_KEY` and restarting the backend → app returns to login on the next request

**Data isolation (use two accounts)**

- [ ] User A adds transactions; log out; user B sees an empty history and a zero dashboard
- [ ] User B adds different transactions; log back in as A → A sees only A's data, and the totals are correct
- [ ] Delete a transaction as A → B's data is unchanged
- [ ] Transactions created before the migration do not appear for any account

**Existing features (regression)**

- [ ] Add a transaction with each category, a custom category, with and without a description
- [ ] History lists and deletes correctly, including the confirmation dialog
- [ ] Dashboard total and category breakdown are correct
- [ ] Theme toggle and navigation still work

**Security checks**

- [ ] After the update, `@pocketpilot_demo_accounts` no longer exists in AsyncStorage
- [ ] Passwords and tokens are not printed with `console.log` or shown in error alerts
- [ ] `npx tsc --noEmit` and `npx expo lint` pass

## 8. Things that are not available yet

- Token refresh: users log in again every 30 minutes by default. If that is too frequent for testing, change `ACCESS_TOKEN_EXPIRE_MINUTES` (up to 1440) in your local `.env`.
- Password reset, password change, email verification, and a logout endpoint.
- HTTPS. During development the API is plain HTTP on the local network, so use only test accounts and made-up data.

Questions about the backend side: contact Khaled.
