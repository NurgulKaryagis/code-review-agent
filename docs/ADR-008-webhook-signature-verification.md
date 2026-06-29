# ADR-008: HMAC-SHA256 Webhook Signature Verification

**Status:** Accepted

**Context:** GitHub delivers webhook events from its own servers, but the `/webhook` endpoint is publicly reachable. Without verification, any party can send a crafted payload that mimics a GitHub PR event, triggering unintended code analysis and patch operations. GitHub signs every request with a shared secret using HMAC-SHA256 and sends the signature in the `X-Hub-Signature-256` header.

**Decision:** Incoming webhook requests are verified against the `X-Hub-Signature-256` header using `hmac.new` + `hmac.compare_digest`. Plain string equality (`==`) was rejected in favour of `hmac.compare_digest` because `==` short-circuits on the first differing byte, leaking timing information that an attacker can use to recover the secret one byte at a time (timing attack). `compare_digest` always takes the same amount of time regardless of how many bytes match. Verification is skipped when `WEBHOOK_SECRET` is not set, preserving a smooth local development experience.

**Consequences:** Requests with a missing or invalid signature are rejected with HTTP 401 before any agent logic runs. Deployment requires `WEBHOOK_SECRET` to be set in the environment and must match the secret configured in the GitHub webhook settings. Timing attacks against the shared secret are mitigated. Local development without a configured secret continues to work unchanged.