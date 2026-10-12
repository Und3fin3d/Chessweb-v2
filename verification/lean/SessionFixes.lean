import Std

namespace ChessWeb.SessionFixes

structure Grant where
  account : Nat
  expires : Nat
  deriving DecidableEq

abbrev Grants := Nat → Option Grant

def activeAccount (grants : Grants) (token now : Nat) : Option Nat :=
  match grants token with
  | none => none
  | some grant => if now < grant.expires then some grant.account else none

def revoke (grants : Grants) (token : Nat) : Grants :=
  fun other => if other = token then none else grants other

theorem revoked_login_rejects (grants : Grants) (token now : Nat) :
    activeAccount (revoke grants token) token now = none := by
  simp [activeAccount, revoke]

theorem revocation_preserves_other_login (grants : Grants) (token other now : Nat)
    (different : other ≠ token) :
    activeAccount (revoke grants token) other now = activeAccount grants other now := by
  simp [activeAccount, revoke, different]

theorem expired_login_rejects (grants : Grants) (token now : Nat) (grant : Grant)
    (stored : grants token = some grant) (expired : grant.expires ≤ now) :
    activeAccount grants token now = none := by
  simp [activeAccount, stored, Nat.not_lt.mpr expired]

structure Session where
  sid : Nat
  token : Option Nat
  guest : Option Int
  fresh : Bool
  game : Option Nat
  epoch : Nat
  deriving DecidableEq

abbrev Retired := Nat → Bool

def retire (retired : Retired) (sid : Nat) : Retired :=
  fun other => if other = sid then true else retired other

def tokenLive (grants : Grants) (token : Option Nat) (now : Nat) : Bool :=
  match token with
  | none => true
  | some token => (activeAccount grants token now).isSome

def saveAllowed (grants : Grants) (retired : Retired) (state : Session) (now : Nat) : Bool :=
  !retired state.sid && tokenLive grants state.token now

theorem revoked_stale_write_rejects (grants : Grants) (retired : Retired) (state : Session)
    (token now : Nat) (held : state.token = some token) :
    saveAllowed (revoke grants token) retired state now = false := by
  simp [saveAllowed, tokenLive, held, revoked_login_rejects]

theorem guest_save_allowed (grants : Grants) (retired : Retired) (state : Session) (now : Nat)
    (guest : state.token = none) (current : retired state.sid = false) :
    saveAllowed grants retired state now = true := by
  simp [saveAllowed, tokenLive, guest, current]

theorem retired_save_rejects (grants : Grants) (retired : Retired) (state : Session) (now : Nat) :
    saveAllowed grants (retire retired state.sid) state now = false := by
  simp [saveAllowed, retire]

def restoreRemember (socket : Bool) (grants : Grants) (token now : Nat) : Option Nat :=
  if socket then none else activeAccount grants token now

theorem sockets_cannot_restore_remember (grants : Grants) (token now : Nat) :
    restoreRemember true grants token now = none := by
  rfl

theorem revoked_remember_rejects (grants : Grants) (token now : Nat) (socket : Bool) :
    restoreRemember socket (revoke grants token) token now = none := by
  simp [restoreRemember, revoked_login_rejects]

structure Outcome where
  session : Session
  account : Option Nat
  clearCookie : Bool

def rememberAttempt (socket : Bool) (grants : Grants) (state : Session) (cookie : Option Nat)
    (now : Nat) : Outcome :=
  match socket, cookie with
  | true, _ => ⟨state, none, false⟩
  | false, none => ⟨state, none, true⟩
  | false, some token =>
    match activeAccount grants token now with
    | some account => ⟨{ state with token := some token, fresh := false }, some account, false⟩
    | none => ⟨{ state with fresh := false }, none, true⟩

theorem remember_attempt_matches_restore (socket : Bool) (grants : Grants) (state : Session)
    (token now : Nat) :
    (rememberAttempt socket grants state (some token) now).account =
      restoreRemember socket grants token now := by
  cases socket with
  | true => rfl
  | false =>
    cases active : activeAccount grants token now <;>
      simp [rememberAttempt, restoreRemember, active]

theorem sockets_leave_remember_state (grants : Grants) (state : Session) (cookie : Option Nat)
    (now : Nat) :
    rememberAttempt true grants state cookie now = Outcome.mk state none false := by
  cases cookie <;> rfl

def accountSession (state : Session) : Session :=
  { state with guest := none }

theorem account_identity_exclusive (state : Session) :
    (accountSession state).guest = none := by
  rfl

theorem normalisation_preserves_freshness (state : Session) :
    (accountSession state).fresh = state.fresh := by
  rfl

theorem remembered_login_stays_nonfresh (state : Session) (remembered : state.fresh = false) :
    (accountSession state).fresh = false := by
  exact remembered

def rotate (state : Session) (newSid : Nat) : Session :=
  { state with sid := newSid }

theorem rotated_session_rejects_old_sid (state : Session) (newSid : Nat)
    (freshSid : newSid ≠ state.sid) :
    (rotate state newSid).sid ≠ state.sid := by
  exact freshSid

theorem stale_save_after_rotation_rejects (grants : Grants) (retired : Retired)
    (state stale : Session) (now : Nat) (same : stale.sid = state.sid) :
    saveAllowed grants (retire retired state.sid) stale now = false := by
  simp [saveAllowed, retire, same]

theorem rotated_session_saves (grants : Grants) (retired : Retired) (state : Session)
    (newSid now : Nat) (freshSid : newSid ≠ state.sid) (unused : retired newSid = false) :
    saveAllowed grants (retire retired state.sid) (rotate state newSid) now =
      tokenLive grants state.token now := by
  simp [saveAllowed, retire, rotate, freshSid, unused]

def guestId (sequence : Nat) : Int := -((sequence : Int) + 1)

theorem guest_ids_are_negative (sequence : Nat) : guestId sequence < 0 := by
  unfold guestId
  omega

theorem guest_account_disjoint (sequence account : Nat) :
    guestId sequence ≠ (account : Int) := by
  unfold guestId
  omega

theorem distinct_sequence_distinct_guest (first second : Nat) (different : first ≠ second) :
    guestId first ≠ guestId second := by
  unfold guestId
  omega

theorem next_guest_differs (sequence : Nat) : guestId (sequence + 1) ≠ guestId sequence := by
  apply distinct_sequence_distinct_guest
  omega

def repairGame (state : Session) (epoch : Nat) (owned : Bool) : Session :=
  { state with game := if state.epoch = epoch ∧ owned then state.game else none, epoch := epoch }

theorem restart_clears_game (state : Session) (epoch : Nat) (owned : Bool)
    (changed : state.epoch ≠ epoch) :
    (repairGame state epoch owned).game = none := by
  simp [repairGame, changed]

theorem deleted_game_clears_reference (state : Session) (epoch : Nat) :
    (repairGame state epoch false).game = none := by
  simp [repairGame]

theorem owned_game_preserved (state : Session) (epoch : Nat) (current : state.epoch = epoch) :
    (repairGame state epoch true).game = state.game := by
  simp [repairGame, current]

def normaliseGuest (state : Session) (epoch : Nat) (owned : Bool) : Session :=
  repairGame
    { state with token := none, fresh := false,
                 game := if state.token.isSome then none else state.game }
    epoch owned

def rememberRequest (grants : Grants) (state : Session) (cookie : Option Nat) (now epoch : Nat)
    (owned : Bool) : Outcome :=
  let attempt := rememberAttempt false grants state cookie now
  match attempt.account with
  | some _ => { attempt with session := accountSession { attempt.session with game := none } }
  | none => { attempt with session := normaliseGuest attempt.session epoch owned }

theorem failed_remember_keeps_guest_game (grants : Grants) (state : Session)
    (token now epoch : Nat) (guest : state.token = none)
    (rejected : activeAccount grants token now = none) (current : state.epoch = epoch) :
    (rememberRequest grants state (some token) now epoch true).session.game = state.game ∧
      (rememberRequest grants state (some token) now epoch true).clearCookie = true := by
  simp [rememberRequest, rememberAttempt, normaliseGuest, repairGame, guest, rejected, current]

theorem failed_remember_drops_account_game (grants : Grants) (state : Session)
    (token old now epoch : Nat) (owned : Bool) (held : state.token = some old)
    (rejected : activeAccount grants token now = none) :
    (rememberRequest grants state (some token) now epoch owned).session.game = none := by
  simp [rememberRequest, rememberAttempt, normaliseGuest, repairGame, held, rejected]

theorem valid_remember_stays_nonfresh (grants : Grants) (state : Session)
    (token now epoch account : Nat) (owned : Bool)
    (active : activeAccount grants token now = some account) :
    (rememberRequest grants state (some token) now epoch owned).account = some account ∧
      (rememberRequest grants state (some token) now epoch owned).session.token = some token ∧
      (rememberRequest grants state (some token) now epoch owned).session.fresh = false ∧
      (rememberRequest grants state (some token) now epoch owned).clearCookie = false := by
  simp [rememberRequest, rememberAttempt, accountSession, active]

#print axioms revoked_login_rejects
#print axioms revoked_stale_write_rejects
#print axioms guest_save_allowed
#print axioms retired_save_rejects
#print axioms revoked_remember_rejects
#print axioms sockets_cannot_restore_remember
#print axioms remember_attempt_matches_restore
#print axioms normalisation_preserves_freshness
#print axioms stale_save_after_rotation_rejects
#print axioms rotated_session_saves
#print axioms guest_account_disjoint
#print axioms distinct_sequence_distinct_guest
#print axioms restart_clears_game
#print axioms owned_game_preserved
#print axioms failed_remember_keeps_guest_game
#print axioms failed_remember_drops_account_game
#print axioms valid_remember_stays_nonfresh

end ChessWeb.SessionFixes
