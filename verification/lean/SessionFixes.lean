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
  token : Nat
  guest : Option Int
  fresh : Bool
  game : Option Nat
  epoch : Nat
  deriving DecidableEq

def saveAllowed (grants : Grants) (state : Session) (now : Nat) : Bool :=
  (activeAccount grants state.token now).isSome

theorem revoked_stale_write_rejects (grants : Grants) (state : Session) (now : Nat) :
    saveAllowed (revoke grants state.token) state now = false := by
  simp [saveAllowed, revoked_login_rejects]

def restoreRemember (socket : Bool) (grants : Grants) (token now : Nat) : Option Nat :=
  if socket then none else activeAccount grants token now

theorem sockets_cannot_restore_remember (grants : Grants) (token now : Nat) :
    restoreRemember true grants token now = none := by
  rfl

theorem revoked_remember_rejects (grants : Grants) (token now : Nat) (socket : Bool) :
    restoreRemember socket (revoke grants token) token now = none := by
  simp [restoreRemember, revoked_login_rejects]

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

def repairGame (state : Session) (epoch : Nat) (present : Bool) : Session :=
  if state.epoch = epoch ∧ present then state else { state with game := none, epoch := epoch }

theorem restart_clears_game (state : Session) (epoch : Nat) (present : Bool)
    (changed : state.epoch ≠ epoch) :
    (repairGame state epoch present).game = none := by
  simp [repairGame, changed]

theorem deleted_game_clears_reference (state : Session) (epoch : Nat) :
    (repairGame state epoch false).game = none := by
  simp [repairGame]

#print axioms revoked_login_rejects
#print axioms revoked_stale_write_rejects
#print axioms revoked_remember_rejects
#print axioms sockets_cannot_restore_remember
#print axioms normalisation_preserves_freshness
#print axioms guest_account_disjoint
#print axioms distinct_sequence_distinct_guest
#print axioms restart_clears_game

end ChessWeb.SessionFixes
