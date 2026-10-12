# Session identity fixes

Login and logout rotate the session ID. Each password login creates an independent, expiring `LoginToken` in the database. Flask-Login uses that token as its alternative ID. `Player.id` remains the numeric account ID used by games and friendships.

Logout deletes the current token. Copied remember cookies and other sessions restored from that token then fail authentication. Other independent password logins remain valid. Session storage rejects writes carrying a revoked or expired token. It also rejects writes to a session ID retired by rotation, including guest sessions, so a request or socket event that loaded the old session cannot recreate it. Each lookup uses a new database connection so a request's earlier transaction cannot supply a cached revocation result.

Remember-cookie restoration is restricted to HTTP requests. Restoration rotates the session ID and preserves `_fresh=False`. A failed restoration keeps the session's previous login token, if any, and deletes the remember cookie in that response. A guest's game reference therefore survives an unusable remember cookie. The browser uses the separate `authenticated` field for its login controls. Rendered session payloads exclude the login token.

Logout revokes its token before disconnecting sockets in that token's room. Login, registration, remember restoration and logout retire the old session ID before disconnecting sockets in that session's room. A connecting socket checks its token against the database, then checks process-local revocation and retirement records while holding the same lock as room entry and disconnection sweeps. It is therefore either reached by the sweep or refused before joining its account room. The server refuses an invalid connection and disconnects a socket whose event fails the session check. The shared client shows its reload dialog for both. Ordinary transport failures reconnect without it. Token expiry does not disconnect an idle socket; its next event fails the check and disconnects it.

Guest IDs come from the database's positive auto-increment sequence and enter game state as negative integers. This separates guests from positive account IDs. IDs are never returned to an in-memory pool. Guest allocation therefore survives application restarts and concurrent requests. Guest names still display `Anonymous-N`.

Identity changes and queue switches detach the previous game through the existing cleanup functions. Session preparation removes missing or unowned game references. A new process epoch also clears references to games from an earlier process. Idle stored sessions can retain old references until their next request; this change does not claim immediate cleanup of every stored session.

Mixed account/guest custom games do not update account statistics. Both seats must contain account IDs before results use account database records.

## Database and deployment effects

The existing `db.create_all()` startup creates the new `login_token` and `guest_identity` tables. No existing `player` column changes. Guest allocation rows must not be deleted or their sequence reset. Expired login tokens are removed when a new password login occurs.

Existing numeric Flask-Login IDs and remember cookies become invalid on deployment. Visitors must sign in again. The first HTTP request carrying such a cookie deletes it. Existing positive guest IDs are replaced on their next request. Ordinary logins expire after the configured session lifetime; remembered logins expire after the configured remember-cookie duration. These server deadlines do not extend when a session is refreshed.

The game registry, game epoch, retired session IDs and socket rooms remain process-local. This change does not make games or session retirement work across multiple independent workers. Separate workers would also hold different game epochs and repeatedly clear each other's game references. Cookie signing, transport security, cryptographic randomness, database sequence allocation and transaction behaviour remain dependencies.

The integration was inspected against Flask-Login 0.6.3, Flask-Session 0.8.0 and Flask-SocketIO 5.6.1. `SessionLoginManager` and `SessionSocketIO` override internal extension hooks, so extension upgrades require checking those integrations. The approach follows Flask-Login's [alternative-token mechanism](https://flask-login.readthedocs.io/en/latest/#alternative-tokens) and Flask-Session's [session-ID regeneration guidance](https://flask-session.readthedocs.io/en/latest/security.html).

## Operation ordering and atomicity

`SessionStore` uses one process-local `threading.Lock` for session retirement, backend saves, completed token revocation records, socket room entry and disconnection sweeps. A save of an ID either completes before rotation deletes it, or is refused afterwards. Retired IDs and revoked tokens remain in memory until the process exits. Their memory use grows with identity changes during that process. They do not expire while an old handler can still hold them.

Database lookups and revocation commits run outside the lock. After committing a revocation, `revoke_login` records the token under the lock before returning or sweeping its sockets. A save that passed its database check earlier is then refused. A save can finish between the database commit and that record; a later load still rejects its token. The operation is complete only after the record is added. Other stored sessions holding that token are reset to guests on their next HTTP request.

The connect handler only joins the account room. It must not perform database work or recursively acquire the session lock. There is no application disconnect handler. The current Socket.IO room and disconnect operations do not acquire database connections. A transport disconnect during room entry is handled as a refused connection. The supported deployment uses one worker with threads. Eventlet and gevent were not verified.

A restart clears the retirement and revocation records; the old process's in-flight handlers end with it. Overlapping old and new processes, such as a graceful reload, are not covered. The lock does not serialise ordinary handlers. Concurrent requests and events of one session still interleave, and the last accepted save wins. A refused save does not undo handler side effects: a board created by an event that loses to a rotation can stay in the registry without a session reference. A request that opens an old ID after its deletion receives a new session; if that response arrives after the rotating response, the browser can keep the new guest session's cookie instead of the rotated one.

Checks inside established events are point-in-time checks. A revocation or rotation during a handler takes effect at its save and at the room sweep. This change does not cancel code already executing inside that handler.

## Verification on 12 October 2026

`verification/lean/SessionFixes.lean` states 26 theorems. They cover revocation, stale authenticated and retired-ID writes, guest saves, token expiry, remember restoration on HTTP and sockets, failed-restoration side effects, freshness, ID separation, game-reference repair and owned-game preservation. Lean 4.34.1 compiled the file with warnings treated as errors. The file contains no admitted proofs.

```sh
lean -DwarningAsError=true verification/lean/SessionFixes.lean
```

These theorems check a manually transcribed model. Session tokens are optional; a session without a token may be saved unless its ID is retired. `saveAllowed` is one step: the implementation makes its retired-ID part atomic with rotation and checks completed process-local revocations under the same lock. Database commits and lookups are separate operations, as described above. `rememberRequest` models one HTTP request whose session token did not authenticate and whose remember cookie is not marked for clearing; `none` stands for a cookie that fails decoding. Its `owned` argument is the result of `owns_current_game()` at that point. The model assumes an existing negative guest ID, omits guest allocation, and represents rotation separately through `rotate` and `retire`. Time maps as `now = ⌊time()⌋`. SID rotation assumes a distinct generated SID. Guest uniqueness assumes the database issues distinct positive sequence values. Token revocation assumes the committed deletion is visible to later lookups. The model does not represent handler interleavings, socket rooms or the operation ordering described above. The proof does not establish Python-to-Lean refinement, cryptographic security, database correctness or deployed behaviour.

Direct replays against the PR source used isolated SQLite and filesystem session storage. They confirmed session-ID rotation, socket disconnection, remembered login remaining non-fresh, copied-cookie rejection after logout, rejection of stale authenticated saves, and bughouse-to-classic queue cleanup. They also confirmed that a move after game cleanup returns without an exception. The upstream application's database and secret settings were replaced only in the verification process.

The main checkout has pre-existing game changes that differ from GitHub's `main`. The equivalent fixes were also applied there. Its existing `test_bug.py` and `verification/e2e_live.py` passed. The end-to-end check used an isolated local server; its requests were routed to a free port without changing test source or assertions. A concurrent replay created 24 guests through eight workers and returned 24 distinct negative IDs with 24 successful HTTP responses.

The existing local `verification/check_sessions.py` failed before exploration because it accesses the removed `main.anon_free` pool. Its assumptions also require `_user_id` to be an account number, the guest name to contain the raw ID, and `_fresh` to equal authentication. Those assumptions no longer describe the implementation. No ordinary test was created or changed. This task does not report a passing bounded session search.

Python compilation and the Agentic complexity check passed for the PR's Python and JavaScript files. The complexity tool does not support Lean. The broader checkout retains unrelated pre-existing findings. Production was not deployed.

## Computer browser verification

The PR source ran locally in Helium through the Computer tool, with isolated SQLite data, dummy accounts and separate test cookie names. Browser actions confirmed login and logout SID rotation, remember-only restoration with `_fresh=False`, rejection of copied cookies after logout, distinct guest identities, and bughouse-to-classic queue switching. The two registered players reached the same classic game. Logout in another tab preserved the opponent's independent login.

The browser exposed two additional session problems. An old tab could show an indefinite pairing spinner after its socket disconnected. All three socket clients now use one shared connection helper that blocks the stale page with a reload action. Logout also removed the classic game without notifying its opponent. Classic departure notification and room closure now belong to the shared game cleanup path, which the Home handler also uses. Browser replays confirmed the reload action, the opponent departure notice and the return Home.

The browser replay also covered the failed-remember-cookie regression. A guest queued with a revoked remember cookie, paired with another guest, reached `/game`, and retained the same game after reload. The HTTP response cleared the remember cookie. Remember-only restoration retained the account with `_fresh=False`. Both authenticated `GET /register` in the browser and direct `POST /register` returned home.

Blocking only the Socket.IO transport left the page without a session-expiry dialog. Removing the test session cookie and allowing reconnection caused explicit server rejection and displayed one reload dialog. Reload created a usable guest session. Logout in another tab also displayed the recovery dialog. The ordinary browser flow reported no JavaScript warnings or errors before the deliberate transport failure.

Direct storage operations confirmed that rotation removed the old guest record, a delayed save did not recreate it, and the new session record remained. A delayed authenticated save after logout was refused and its old record remained absent. These checks exercised ordered operations; they were not a concurrent stress test. The existing `test_bug.py` and `verification/e2e_live.py` were rerun successfully against the checkout and its isolated server after the final code changes. Werkzeug logged HTTP 400 messages during some WebSocket teardown operations in the latter run; all check assertions passed.

Full classic move verification remains blocked by an existing upstream issue: the initiation handler emits names and returns without the initial board update. Both players therefore see an empty board and `00:00` clocks. The same handler exists in the PR base. This session-focused change leaves it unchanged. The browser run did not verify a complete four-player bughouse game or a mobile viewport. Production was not tested.
