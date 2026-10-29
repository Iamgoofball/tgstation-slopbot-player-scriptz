# job_scriptz/paramedic/

The rescue medic: triage the station from a handheld crew monitor, then move
patients on a roller bed — never dragged. Spawn kit (verified): EMT belt
(handheld crew monitor + roller bed + syringe + gauze + tourniquet + survival
box), medical backpack (bandages...), PDA, nitrile gloves, penlight, medical
headset, Paramedic ID (Medbay/Morgue/Maintenance/external airlocks — NOT
Genetics or most dept doors).

## Scripts

| Script | Args | What it does |
| --- | --- | --- |
| `paramedic_kit_check.py` | (none) | One-envelope kit audit. Belt+backpack contents via the `on "storage"` screen icons (the HUD clicks TOGGLE the views, so it unions the reads before+after each click — state-independent; needs `page_size>=200`: the storage decorations flood the screen listing and paginate smaller reads). Worn slots from inventory (`in slot` + `not shown on screen` for ears/gloves). Verdicts: no monitor / no roller bed / no PDA / no gloves / no ID. Read-only. |
| `paramedic_crew_monitor.py` | `monitor?`, `x?`, `y?`, `min_damage?`=20 | Handheld crew monitor triage (works anywhere — GLOB.crewmonitor is station-wide). Picks the monitor off the belt view into the empty active hand, clicks it AGAIN in hand (attack_self → GLOB.crewmonitor.show, sensor_device.dm:18), parses the CrewConsole window's data.sensors[] (life_status 0/1-2/3, health, oxy/tox/burn/brute, area), classifies DEAD/CRITICAL/WOUNDED(≥min_damage)/BROKEN(-50 garbage)/binary-only, closes the window, stows the monitor back with E. |
| `roller_bed_use.py` | `mode`: status/deploy/buckle/unbuckle/pull/unpull/fold/brakes, `bed`?, `patient`?, `x`?, `y`? | Drives the emergency roller bed end-to-end (bed.dm): deploy = click the folded item IN HAND (attack_self → deploy_bed at your feet; item consumed → NEW structure id); buckle = drag the patient onto the structure (icon emerg_up, dense); unbuckle = EMPTY-hand LMB on it; pull = ctrl-click (verified via the "stop pulling" HUD); fold = RIGHT-click (refused while buckled; item has a NEW id); brakes = ALT-click (anchored toggle, verified via examine; buckled patients can't alt-click themselves off). Status reads icon_state from the TILE (emerg_down/_up/emerg_folded). |

## Live notes (verified this round)

- **Screen pagination trap**: `sk.screen(page_size=160)` PAGINATES — the
  storage view's decoration objects (storage_cell/corner/rowjoin) flood the
  listing and kit items fall past the cut. Use `page_size=250` (full
  inventory+storage render ≈ 49 objects).
- **Deploy after fold**: folding puts the fresh item straight in your active
  hand — a plain click on it then DEPLOYS it again (attack_self). To stow:
  click the belt HUD **with the item in hand** (stores into the EMT belt;
  drag onto the HUD icon does nothing for it).
- The belt HUD click toggles the belt view with an EMPTY hand and stores the
  held item when a bed/gauze etc. is in hand.
- Buckle a corpse the same as a live patient (drag onto the bed; same-tile
  drag onto a bed is fine — beds are not dense, unlike DNA pods where
  same-tile drags hug).
- Towing: ctrl-click the bed → "stop pulling" HUD appears → walk; bed + all
  buckled mobs follow one tile behind.
- Crew monitor data this round: leftovers from previous bodies show as
  "Unknown"/old-job assignments — the monitor reads SUIT sensors, so the
  assignment is the job the SUIT was worn as, not the mob's current job.
- The monitor's E-stow and the belt view clicks leave the belt view open —
  harmless, but the next belt overlay read must expect the open view.
- Paramedic ID does NOT open Genetics — reach lab corpses via the admin
  Jump To Coordinate verb (NumberInputModal ×3: cx/cy/cz, submit with
  `params={"entry": N}`; re-scan windows between submits — the modal reuses
  one window id).
