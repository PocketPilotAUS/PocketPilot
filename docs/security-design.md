# Security design

Passwords use Argon2 hashes. HS256 JWTs require a private sufficiently long secret and validated expiry. Authentication checks account token version and session revocation. Opaque refresh tokens are stored as SHA-256 hashes and rotate once; replay revokes the family. Password changes invalidate all sessions. See [refresh](automatic-token-refresh.md).

Financial queries, AI context and mutations are user-scoped. Proposal confirmation/dismissal enforce ownership. Read-only intent cannot create proposals solely from model output; recording requires evidence validation and explicit confirmation. AI has no direct database tool.

Distinct budget/monitoring fingerprints validate reviewed snapshots. Locks and idempotency keys protect relevant mutations. CSV previews are signed, owner-bound and time-limited; input size and row count are bounded.

Native credentials use SecureStore; web credentials remain in memory. Use HTTPS outside local development. SQLite data has no application-level encryption; host access and backup security remain operational responsibilities. See [assessment](security-self-assessment.md).
