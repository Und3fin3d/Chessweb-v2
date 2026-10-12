# Session identity fixes

Login and logout rotate the session ID. Each password login creates an independent, expiring `LoginToken` in the database. Flask-Login uses that token as its alternative ID. `Player.id` remains the numeric account ID used by games and friendships.

Logout deletes the current token. Copied remember cookies and other sessions restored from that token then fail authentication. Other independent password logins remain valid. Session storage rejects writes carrying a revoked or expired token. Each lookup uses a new database connection so a request's earlier transaction cannot supply a cached revocation result.

Remember-cookie restoration is restricted to HTTP requests. Restoration rotates the session ID and preserves `_fresh=False`. The browser uses the separate `authenticated` field for its login controls. Rendered session payloads exclude the login token. Existing sockets disconnect when their session ID changes or their login token is revoked.

Guest IDs come from the database's positive auto-increment sequence and enter game state as negative integers. This separates guests from positive account IDs. IDs are never returned to an in-memory pool. Guest allocation therefore survives application restarts and concurrent requests. Guest names still display `Anonymous-N`.

Identity changes and queue switches detach the previous game through the existing cleanup functions. Session preparation removes missing or unowned game references. A new process epoch also clears references to games from an earlier process. Idle stored sessions can retain old references until their next request; this change does not claim immediate cleanup of every stored session.

Mixed account/guest custom games do not update account statistics. Both seats must contain account IDs before results use account database records.

## Database and deployment effects

The existing `db.create_all()` startup creates the new `login_token` and `guest_identity` tables. No existing `player` column changes. Guest allocation rows must not be deleted or their sequence reset. Expired login tokens are removed when a new password login occurs.

Existing numeric Flask-Login IDs and remember cookies become invalid on deployment. Visitors must sign in again. Existing positive guest IDs are replaced on their next request. Ordinary logins expire after the configured session lifetime; remembered logins expire after the configured remember-cookie duration. These server deadlines do not extend when a session is refreshed.

The game registry remains process-local. This change does not make games work across multiple independent workers. Cookie signing, transport security, cryptographic randomness, database sequence allocation and transaction behaviour remain dependencies.

The integration was inspected against Flask-Login 0.6.3, Flask-Session 0.8.0 and Flask-SocketIO 5.6.1. `SessionLoginManager` and `SessionSocketIO` override internal extension hooks, so extension upgrades require checking those integrations. The approach follows Flask-Login's [alternative-token mechanism](https://flask-login.readthedocs.io/en/latest/#alternative-tokens) and Flask-Session's [session-ID regeneration guidance](https://flask-session.readthedocs.io/en/latest/security.html).

## Verification on 12 October 2026

`verification/lean/SessionFixes.lean` passed Lean 4.34.1 with warnings treated as errors. Its 16 theorems cover revocation, stale authenticated writes, token expiry, socket remember restoration, freshness, ID separation and game-reference repair. The file contains no admitted proofs. Printed dependencies are limited to standard Lean axioms.

```sh
lean -DwarningAsError=true verification/lean/SessionFixes.lean
```

These theorems check a manually transcribed model. SID rotation assumes a distinct generated SID. Guest uniqueness assumes the database issues distinct positive sequence values. Token revocation assumes the committed deletion is visible to later lookups. The proof does not establish Python-to-Lean refinement, cryptographic security, database correctness or deployed behaviour.

Direct replays against the PR source used isolated SQLite and filesystem session storage. They confirmed session-ID rotation, socket disconnection, remembered login remaining non-fresh, copied-cookie rejection after logout, rejection of stale authenticated saves, and bughouse-to-classic queue cleanup. They also confirmed that a move after game cleanup returns without an exception. The upstream application's database and secret settings were replaced only in the verification process.

The main checkout has pre-existing game changes that differ from GitHub's `main`. The equivalent fixes were also applied there. Its existing `test_bug.py` and `verification/e2e_live.py` passed. The end-to-end check used an isolated local server; its requests were routed to a free port without changing test source or assertions. A concurrent replay created 24 guests through eight workers and returned 24 distinct negative IDs with 24 successful HTTP responses.

The existing local `verification/check_sessions.py` failed before exploration because it accesses the removed `main.anon_free` pool. Its assumptions also require `_user_id` to be an account number, the guest name to contain the raw ID, and `_fresh` to equal authentication. Those assumptions no longer describe the implementation. No ordinary test was created or changed. This task does not report a passing bounded session search.

Python compilation and the Agentic complexity check passed for the PR's Python and JavaScript files. The complexity tool does not support Lean. The broader checkout retains unrelated pre-existing findings. Production was not deployed.
