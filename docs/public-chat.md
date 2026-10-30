# Public chat without a shared access token

`ZENITH_PUBLIC_CHAT=1` enables guest chat and normal account sign-in without
asking visitors for the server API key. Keep the independent strong
`ZENITH_API_TOKEN` and Cloudflare `ZENITH_ORIGIN_SECRET` private and configured.
The origin remains authenticated; this setting does not remove owner login,
MFA, capability grants, or tool scope checks. The default is disabled, preserving
existing private-server and native Bearer API behavior.

The browser opens `/` and receives an automatic host-only, HttpOnly, SameSite
guest cookie (Secure over HTTPS). API clients can bootstrap the same session
with `GET /api/account`. Guest identities are signed separately from server
access grants and cannot be used as those grants. Guest chat/history/ordinary
skills are isolated by browser identity; guests cannot read legacy anonymous
or account-owned conversations, save memories, approve training examples, or
execute administrative workflows. Account registration/login needs no shared
token. Passwords and owner privileges retain their existing protection.

Guest cookies expire after seven days. Losing/clearing one loses access to that
guest history; signing in starts account-owned conversations and does not claim
earlier guest or legacy history. Use an account for persistent memories and
saved conversation navigation. Logout creates a fresh guest identity.

The public model service admits up to 20 chat requests per minute per client
address, with at most 1,024 active limiter entries and the existing single-model
generation lock. Cloudflare supplies the authenticated client address through
the origin wrapper; untrusted forwarded headers do not grant authority. These
single-process limits are not a distributed abuse-prevention service.

Validation includes public/private mode tests, guest/account isolation,
signature expiry/tampering, CSRF, restricted tools, rate limits, and real Chromium
chat/reload/account-registration workflows. Browser tests use a labeled fixture;
real hosted inference must be checked separately after deployment.

Rollback: unset `ZENITH_PUBLIC_CHAT` or set it to `0` and redeploy the same
checkpoint and volume. The private server-access prompt returns. No weights,
tokenizer, approval receipts, or database schemas are migrated or overwritten.
