# ADR-009: FastAPI Depends for Endpoint-Specific Security

**Status:** Accepted

**Context:** Security pre-conditions such as signature verification and rate limiting must run before endpoint logic, but different endpoints require different checks. `/webhook` requires HMAC verification; `/approve` does not receive a GitHub signature. A global middleware would apply the same check to every route, forcing conditional logic inside the middleware to exclude or adjust behaviour per route.

**Decision:** FastAPI's `Depends` system was chosen over `BaseHTTPMiddleware` for endpoint-specific security. Each security function is declared as an async dependency and injected only into the endpoints that need it via `Depends(...)`. Global concerns that genuinely apply to all routes — such as the request body size limit — remain in middleware.

**Consequences:** Security checks are co-located with the endpoints that require them, making the relationship explicit and easy to audit. Adding a new protected endpoint means adding `Depends(...)` to its signature rather than modifying a central middleware. The trade-off is that a developer can accidentally forget the `Depends` on a new endpoint; middleware would enforce the check automatically. For this reason, the body size limit (which must apply everywhere) stays as middleware while signature verification (which is webhook-specific) uses `Depends`.