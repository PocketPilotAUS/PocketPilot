# Automatic token refresh

Access JWTs retain the configured lifetime (30 minutes by default). Login now also issues an opaque refresh token for a fixed seven-day session. Refresh rotates that token without extending the session deadline. Only SHA-256 hashes of random 384-bit refresh tokens are stored. Consumed hashes are retained to detect replay and revoke the entire session, including its access tokens. Logout revokes the current device session; password changes invalidate all sessions through the existing account token version.

Run `Backend/migrate_refresh_sessions.py` using the backend virtual environment before signing in. The additive migration backs up SQLite and is safe to rerun; `init_db.py` includes both tables for new installations. Restart the backend, reload the app and sign in once to obtain a refresh token. Existing access-only logins cannot refresh.

The client refreshes on a 401 and retries the original request once. Concurrent calls share one refresh. Network/5xx failures retain stored credentials. Late responses cannot overwrite logout or a newer login. Native devices store the pair atomically in SecureStore with device-only accessibility; web keeps it in memory, so browser reload still requires login. There is no background polling or timer dependency. Fixed session expiry requires a new login after seven days.

Use HTTPS outside local development. Refresh tokens extend credential usefulness and require the same transport protection as passwords. Offline logout clears local credentials but cannot guarantee server revocation. A lost successful refresh response can require login on the next attempt: strict single-use replay detection deliberately fails closed rather than accepting the old token again. Expired session rows and their token hashes may be purged together after expiry; do not remove consumed tokens from still-active sessions.

Verification: backend pytest suite, `node --test tests/auth-refresh.cjs` from Mobile, and TypeScript checking. No lint script is currently configured.
