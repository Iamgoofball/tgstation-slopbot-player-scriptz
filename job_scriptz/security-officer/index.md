# job_scriptz/security-officer/

The security wing: gear up, survey the brig, drive the records console and the
cell door timers. MetaStation wing layout: brig corridor
y=166-169 (x=95-116), cells south of it (interiors y=161-164), Brig Control
x=105-110, Security Office x=116-125, Security Locker Room (Gear Room)
x=110-114 y=174-178. Spawn kit already covers armor vest, helmet, jackboots,
security bowman headset, uniform, security gloves, mindshield, disabler (suit
storage), cuffs + flash (pockets). McGriff the pug lives in Brig Control.

## Getting into the wing

- Walking from Arrivals is often NOT viable (observed this round: the
  arrivals pocket firelock-sealed, the west Central Primary Hallway
  firelocked AND dark - broken lights, e.g. (121,115) under 5%, and the
  move tool refuses unlit tiles). Practical entry: **admin Jump To
  Coordinate** - (111,177,2) = the Security Locker Room, (122,115,2) = the
  Central Primary Hallway.
- Once inside, the wing is WALKABLE end to end (no firelocks): Security
  Locker Room -> Brig -> Brig Control -> Security Office; department doors
  bump open with security access (`sk.move`/`walk_to`) - but Brig Control
  itself needs ARMORY access (warden/HoS IDs); a plain officer ID is
  stopped at the corridor.
- The wing's own fire-alarm hazard: none found; the firelocks that matter are
  outside the wing (Central Primary Hallway x=118).
- The department techfab (Security) at (118,169) is DENSE and blocks the
  console row - approach the Security Office consoles from y=170.

## Gear-up (fork truths, live-verified the hard way)

- **E hotkey = quick-equip** the active-hand item. NEVER click a HELD item's
  id to wear it: the driver resolves it to the item's stale floor position,
  and the click lands on whatever is there now - it stuffed my belt and HUD
  glasses into the open locker.
- Belt wear needs the belt slot EMPTY first (no auto-swap on this fork):
  click the worn PDA (belt slots are always-visible HUD icons - id clicks on
  those resolve fine), store it by clicking the worn BACKPACK id, then wear
  the belt with E.
- Hidden worn slots (head/eyes/suit/ears/...) have no on-screen icon until
  the inventory HUD is EXPANDED: click the HUD "toggle" button (find its obj
  id in the inventory note `click the HUD button "toggle" (obj NNNN)`).
  The seclite -> helmet attach ONLY works through the expanded slot icon
  (clicking the mob's sprite hits the chest, not the head overlay).
- Locker: 1st click = UNLOCK, 2nd = OPEN; contents render as a "menu obj ..."
  list on the locker's tile line - click a listed obj id to take it.
  Clicking the locker WITH a held item = the item goes INTO the locker:
  empty both hands before every locker click.
- Shift+E draws the belt's FIRST item (if the PDA sits in the belt slot it
  draws the PDA). Z toggles the baton; the examine text does NOT say "turned
  on" - check the icon_state `stunbaton_active` (or the charge line).
- Keep the spawn security gloves ON (25% faster cuffing); the locker's
  enhanced retrieval gloves go to the backpack as spares. Leave the spare
  vest/helmet/headsets in the locker (locker stock).

## The brig (map coords; find every machine by NAME - ids re-roll)

- Cell door timers are WALL DISPLAYS named "Cell N": "Cell 2" at (101,165),
  "Cell 3" at (103,165). A cell DOOR also answers to "Cell 3" (at 103,164) -
  pass an explicit id or the script skips dense matches. Cell lockers:
  "Cell 1/2/3 locker" at (97/100/103,162); beds at y=162; "Brig Shutters"
  at (103,161).
- Flasher buttons: "Brig Entrance Flasher" + "Holding Cell Flasher" at
  (113,165), a second pair in Brig Control (107,164); portable flashers in
  the Gear Room.
- Holding Cell (east, through the windoor): cuffs rack, prisoner jumpsuits,
  orange shoes, straight jacket/muzzle/blindfold, bed.
- Brig Control: security records console at (108,163), security camera
  console at (108,162), prisoner management console at (108,165), warden's
  locker at (105,165), lockdown buttons "Brig Lockdown Control" / "Prison
  Wing Lockdown" / "Cell Window Control" at (105,164).
- Security Office: security records console at (121,169), security camera
  console at (120,169), department techfab (Security) at (118,169), fax at
  (123,177).
- Records consoles are EVERYWHERE (find them by name): Detective's Office,
  HoS office, Security Posts (Cargo Bay / Medbay / Science), Customs, HoP
  office.
- Beepsky patrols but may wander far (once found stale in the Departure
  Lounge) - check him at shift start.

## Records console (tgui "SecurityRecords")

- Open with an EMPTY ACTIVE hand. State does NOT render in `tgui_windows` -
  read it with `sk.tgui_window(id, path=...)`: `data.records` (fields
  name,rank,wanted_status,crew_ref -> one JSON line per record),
  `data.available_statuses` (None/Suspected/Arrest/Incarcerated/Parole/
  Discharged), `data.authenticated`.
- Valid actions (server introspection - send a bogus action and the tool
  lists them): add_crime, delete_record, edit_crime, edit_field,
  invalidate_crime, login, logout, print_record, purge_records, set_wanted,
  view_record. There is NO set_note on this fork - notes go through
  edit_field (untested).
- Writes verify via the act's data_changes, keyed by dotted path + name:
  `records.N.wanted_status (name): "None" -> "Suspected"`;
  invalidate -> `citations.0.valid (name): "1" -> "0"` + `voider: null ->
  <name>`; logout -> `authenticated: 1 -> 0`.
- add_crime {crew_ref, name, details, fine}: fine 0 = CRIME (sets Arrest -
  Beepsky arrests on sight); fine > 0 = CITATION (no status change). Arrest
  needs at least one crime on the record first. Only the author or armory
  access can edit/invalidate a crime.
- Crew refs: one record per body; several same-name records exist -> pass
  rank= to disambiguate (the current body's rank + crew_ref come from its
  crew-list row).
- Verified live on my own record: login, list, set_wanted Suspected -> None,
  add_crime (citation fine 100) + invalidate_crime (both voided), logout.
  NEVER touch delete_record / purge_records; add_crime with fine 0 untested
  on purpose.

## Cell door timer (tgui "BrigTimer")

- The window dump carries no state - ALL verification comes from the act's
  data_changes: preset -> `minutes: 0 -> 2`; start -> `timing: 0 -> 1` (+
  the cell door's leftsecureopen -> leftsecureclosing); stop -> `timing:
  1 -> 0` (door reopens, no radio message); time -> `seconds/minutes`.
- preset short/medium/long = 2/3/5 min; time adjust 600/100 = +-1 min/10 s;
  max 15 min. `flash` fires the cell flasher.
- `cycle` (safe round-trip on an empty cell) refuses when ANY mob - even a
  hauberoach - is in the 3x6 zone south of the timer, unless force=true.

## Live notes (round-labeled observations, not durable truths)

- A session can go IDLE mid-shift (the connection drops, not the round):
  reconnect = `disconnect` -> `connect {name: "TheAdministrator"}` ->
  `setup/load_map.py`; the body is reclaimed where it stood (map rev resets
  per session).
- Bodies from earlier shifts (aghost respawn quirk) can stand alive in the
  halls - leave them where they stand.
- Vermin (hauberoaches) frequent the cell zone around (102,162) on some
  rounds - they trip the timer's occupancy guard.
- The secoff gear-up was assembled manually after several item-loss fumbles;
  `security_gear_up.py` encodes the fixed sequence and its re-run (skip)
  path is verified.

## Scripts

| Script | Args | What it does |
| --- | --- | --- |
| `security_gear_up.py` | `locker`?, `x`?, `y`?, `say`? | Locker -> full kit: free the belt slot (PDA -> backpack), wear the security belt + HUDSunglasses (E hotkey), attach the seclite via the expanded HUD slot icon, stash the retrieval gloves, close the locker (empty hands), draw + turn on the baton (icon check). Re-run safe: worn steps skipped (verified). |
| `brig_check.py` | `no_walk`?, `x`?/`y`?, `say`? | One-envelope security wing survey: cell timers/lockers, flasher buttons, holding cell, Brig Control + Security Office consoles, techfab (Security), Beepsky's staleness, mobs in the wing (prisoners?). Walk anchor = a cell timer found by NAME (stand in the corridor 3 tiles north - never inside staff-only Brig Control); args x/y fallback. |
| `sec_records_control.py` | `mode`: status/list/login/logout/set_wanted/add_crime/invalidate_crime/edit_field, `console`?, `crew`?+`rank`?/`crew_ref`?, `status`?, `crime`?, `details`?, `fine`?, `crime_ref`?, `field`?, `value`? | Records console driver (see "Records console" above for the truths). list = JSON rows via tgui_window. |
| `brig_timer_control.py` | `mode`: status/preset/time/start/stop/flash/cycle, `timer`?/`name`?, `preset`?, `adjust`?, `force`? | Cell door timer driver; cycle = guarded empty-cell round-trip (stop -> preset -> start -> flash -> stop), verified via act data_changes. |
