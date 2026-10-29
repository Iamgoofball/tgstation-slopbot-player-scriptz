# job_scriptz/warden/

The Warden runs the Brig, the Prison Wing and the prisoners, and guards the
Armory. Station: MetaStation. The desk is **Brig Control** (x=105-108,
y=160-166); the wing layout truths are in `security-officer/index.md` (cells
y=161-165, flashers, holding cell, records consoles everywhere). Reuse:
`security-officer/sec_records_control.py` (records), `security-officer/
brig_timer_control.py` (cell timers), `chief-medical-officer/crew_monitor.py`
(the Brig Control crew monitoring console - same console type, pass its id +
x/y from a live name search).

## The warden's kit (live-verified)

- Spawn: security backpack, PDA (BELT slot), Warden ID (armory+brig+security
  access), cuffs (left pocket), flash (right pocket), disabler (suit
  storage), HUDSunglasses, armored jacket + hat + security suit, bowman
  headset, security gloves (microchip cuffing), mindshield.
- **Warden's locker at (105,165) Brig Control** (dense): Type 5 laser gun,
  box of flashbangs, box of spare zipties, security door remote, loaded
  security belt (pepperspray/cuffs/flashbang/flash/stunbaton), compact
  combat shotgun, holobarrier projector, bandolier, seclite, garment bag,
  radio headset, jumbo dog bone (McGriff's - leave it). NO Kaza Ruk gloves
  on this fork (searched: nothing in view, bag contents not revealed) - the
  wiki's special-moves gloves don't exist here.
- What I carry: laser → **suit storage** (a gun is TOO BIG for the
  backpack: clicking a storage item with a held gun *uses the gun on the
  item* - floating text "too big!"; the disabler that spawn-drove there
  moved to the backpack), flashbang box + ziptie box + door remote +
  disabler → backpack. The loaded belt stays locker stock (my PDA occupies
  the belt slot; the baton lives in that belt when needed).

## Gear-up fork truths (all learned the hard way)

- **Clicks beyond 1 tile are silently ignored** ("nothing visible
  happened"): the locker is DENSE, walk ADJACENT (bot.goto parks next to
  dense tiles) before every click. I burned 3 clicks from 2 tiles away.
- Two adjacent empty-hand clicks = unlock + open; the contents then spill
  onto the locker's tile line as `- obj NNNN` entries (this locker: no
  "menu obj" prefix, unlike the secoff locker's menu lines).
- **Verify pickups via STATUS `active_hand:`** (sleep ~0.9 s before the
  read): the inventory tool can RACE a fresh click and report stale empty
  hands - my first batch thought 4 pickups failed while 3 of them were
  in-hand no-ops because the hand was already full.
- **A click with a FULL hand = in-hand USE of what you hold** - for a
  laser gun that is a fire risk. Empty the hand (store/drop) before every
  next pickup click.
- The warden's garment bag: in-hand click toggles a "Switch gathering mode"
  HUD button (pickup mode), NOT an open-contents UI; examine does not list
  contents. Put it back by clicking the open locker with the bag held
  (the held-item click = store-into-locker truth).
- A closed locker SWALLOWS anyone standing on its tile (I reconnected
  inside it after an idle gap: dark impaired view, name rendered "").
  Recovery: click the locker (opens from inside), step off the tile.

## Brig Control desk (map coords; find every machine by NAME - ids re-roll)

- Prisoner management console (108,165), security records console (108,163),
  security camera console (108,162), crew monitoring console (106,162),
  warden's locker (105,165), lockdown button grid: Cell Window Control /
  **Brig Lockdown Control** / Prison Wing Lockdown (at 105,164ish; a Labor
  Camp Shuttle Lockdown button also exists elsewhere), Warden Desk Shutters
  (107,161).
- The security camera console opens a **CameraConsole** tgui when clicked
  ADJACENT (actions `start_tracking`, `switch_camera {camera}`; ~260
  camera refs in static_data.cameras). Detection gotcha: scan ALL
  tgui-window blocks for the interface name - matching only the first
  window block made me misdiagnose the console as dead for an hour.
- PrisonerManagement tgui: actions `eject_id, handle_implant
  {implant_action, implant_ref}, insert_id, login, logout, reset_id,
  set_id_goal`; data = `{authorized, inserted_id, implants}`. Login
  verified (`authorized: 0 -> 1`). set_id_goal = the labor-camp point
  goal (always set it for labor-camp prisoners). insert_id needs the
  prisoner's ID in your ACTIVE hand.
- Lockdown cycle verified on the Brig Lockdown Control button: the desk
  shutters flip open -> closed -> open, state restored. The cycle's
  people-guard includes vermin and McGriff the pug by design (a lockdown
  that traps the medibot is still a lockdown) - it refuses until force=true.
- Do NOT click the lockdown button while holding an item: same held-item
  in-hand use risk. Empty hand (the script enforces it).
- **Access: Brig Control doors need armory access** (warden/HoS IDs).
  A secoff/detective ID is stopped at the corridor - the desk scripts are
  warden-role tools; run them as the warden.

## Live notes (round-labeled observations, not durable truths)

- Session IDLE mid-shift (30 min without tool calls) drops the connection:
  reconnect = `disconnect` -> `connect {name: "TheAdministrator"}` ->
  `setup/load_map.py`. This round the body had ended up INSIDE the closed
  locker (see recovery above).
- The `_my_name()` prelude helper can misfire after a reconnect (the
  status name line rendered "" once) - mob filters should exclude by the
  `you: mob NNNN` id from status, not by name (both scripts fixed).
- `sk.search` NEVER matches bare obj ids (a bare id query found nothing;
  the same object resolved instantly via its name "Lockdown") - search by
  name, filter by id.
- `run_script` is SINGLE-SESSION: two scripts fired in parallel = the
  second is refused ("A script is running"). Always sequential.
- Radio check-in `:s` "Warden on shift. Brig and Armory under watch."

## Scripts

| Script | Args | What it does |
| --- | --- | --- |
| `warden_gear_up.py` | `locker`?, `x`?, `y`?, `bp`?, `say`? | Warden's locker -> shift kit: unlock+open (adjacent!), take laser/flashbangs/zipties/door remote into the backpack (active_hand-verified, re-run safe: skips owned items), close + relock. |
| `brig_control_check.py` | `no_walk`?, `x`?/`y`?, `say`? | One-envelope desk survey: walk anchor derived from a console found by NAME (args x/y fallback), prisoner management console opened + logged + data dumped (`{authorized, inserted_id, implants}`), records/camera/crew-monitor consoles located, lockdown buttons enumerated by NAME search (found 4 this round, incl. Labor Camp Shuttle), desk shutters + warden's locker states, mobs in the wing (vermin classified, prisoners flagged). |
| `prisoner_console_control.py` | `mode`: status/insert_id/eject_id/reset_id/set_id_goal/handle_implant, `console`?, `goal`?, `implant_action`?, `implant_ref`? | PrisonerManagement tgui driver: login + data dump verified; insert_id (ID in active hand), set_id_goal (labor camp), implant handling. Write paths coded, not live-tested (no prisoner ID this round). |
| `lockdown_control.py` | `mode`: status/toggle/cycle, `button`?, `force`? | Lockdown button driver: cycle = toggle on (shutters verified closed), toggle off (verified open) - state restored. People-guard refuses with mobs near the brig front unless force. |
