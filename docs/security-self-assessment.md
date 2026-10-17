# Security self-assessment

This source review is not an independent penetration test or production certification. Tests cover authentication, ownership, invalid proposals, replay and stale snapshots, but cannot prove every model response or deployment secure.

Remaining limitations:

- Development HTTP/CORS need deployment hardening; TLS, secret rotation, backups and monitoring need operational ownership.
- No supplied rate limiting, password recovery, email verification or production deployment pipeline.
- SQLite and backups contain sensitive records without application-level encryption. Never commit them or real exports.
- Ollama receives scoped financial context. A remote URL changes the privacy boundary; use a trusted host.
- Model answers can be incorrect or follow hostile instructions. Server write gates do not verify every informational sentence.
- The public exchange-rate service receives no financial ledger; conversion uses current/cached rather than historical rates.
- Strict refresh replay rules can require login after a lost successful response. Offline logout cannot guarantee remote revocation.

Inspect exact staging content for keys, tokens, environment files, databases/journals, exports, backups and personal LAN addresses. See [testing](testing.md).
