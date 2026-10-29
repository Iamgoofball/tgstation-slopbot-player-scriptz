# job_scriptz/coroner/

The morgue keeper: store the dead, autopsy them, keep the medical records
honest. Spawn kit (verified this round): coroner scrubs + labcoat + cap +
gloves + shoes, sterile mask, service medical headset, coroner backpack, PDA,
Coroner ID, clipboard, dropper. **Nothing surgical spawns on the mob** — no
drapes, no medkit, no tools. This round's tools were scrounged (scalpel +
retractor from the Robotics Lab supply table, captain's bedsheet from the
Captain's Quarters, autopsy scanner from the Morgue) and every non-worn item
was returned after testing.

## Scripts

| Script | Args | What it does |
| --- | --- | --- |
| `morgue_check.py` | `ids`?, `trays`?, `bags`? | READ-ONLY survey of every morgue unit in view (auto-discovers; skips airlocks/alarms via the `morgue0-4` state match + "secure morgue" name). Per unit: state → meaning (morgue0 OPEN / morgue1 empty / morgue2 occupied dead / morgue3 non-carbon / morgue4 REVIVABLE — do not autopsy), occupant parsed from the auto-label name, beeper read via examine. `trays`: open "morgue tray" objects; `bags`: body bags. |
| `morgue_tray_control.py` | `mode`: status/open/close/beep/beep_on/beep_off/open_bag/close_bag/bag_body, `id`?, `bag`?, `body`? | One-unit driver. open/close = EMPTY-hand click toggles the tray (open spawns a "morgue tray" NORTH of the unit — verified morgue0 + tray id; close retracts, and everything on that tile rides back inside — occupant round-trip verified). beeper = ALT-click toggle, read back via examine ("The speaker is enabled/disabled"), beep_on/beep_off no-op when already set. bag modes = empty-hand click toggles the bag; bag_body closes an open bag over the corpse lying on it (the close ZIPS the body inside — verified by tile read, no drag needed). |
| `autopsy_workflow.py` | `patient`, `aid`?, `scalpel`?, `retractor`?, `scanner`?, `expect_name`? | Full autopsy chain on one exposed corpse: prep chest (drapes OR bedsheet) → incise (scalpel ~1.6s) → retract skin (retractor ~2.4s) → autopsy (scanner ~10s) → report paper spawns in the active hand, report text read from the PaperSheet tgui. Tool ids auto-found from the view pile; patient must be lying + dead + bag-opened first (morgue_tray_control). Guards: catatonic (alive) refused, name mismatch flagged, "ANALYZING CADAVER" = chain not ready detected. |
| `medical_records.py` | `action`: read/add_note/cause/physical/mental/blood, `laptop`?, `name`?, `value`? | MedicalRecords tgui on the morgue's medical laptop (empty-hand click). read = name→crew_ref map of every record. Edits carry crew_ref + are verified via the window's data_changes: add_note (content), set_cause_of_death (cause), set_physical_status / set_mental_status (status strings), set_blood_type ("A+"). Window closed after. |

## Live notes (round-labeled observations, not durable truths)

- **Morgue states** (morgue.dm `update_icon_state`): morgue0 = tray out
  (OPEN), morgue1 = closed empty, morgue2 = closed occupied (dead),
  morgue3 = occupied non-carbon, morgue4 = occupied REVIVABLE (defib first,
  never autopsy). The occupant rides in the unit NAME ("morgue - (Name -
  Species)") — while stored, the label persists (examine shows it even with
  the bag zipped).
- **Secure morgues** (3 units at ~104,81-82) spawn with their beepers
  DISABLED (all other units default enabled) and are INVISIBLE until the east
  door is opened — they simply don't render/search while walled off. Not a
  script bug.
- **Tray geometry**: open spawns the "morgue tray" on the tile NORTH of the
  unit (dense, state=morguet); close retracts it and the corpse + bag ride
  back inside. Re-open returns body + bag to the tray tile. Close the BAG
  before retracting so the corpse is inside it.
- **Body bags**: a deployed bag is a closet structure (bodybag.dm). Close-click
  (empty hand) zips a body LYING ON it inside — no drag needed. The
  `bodybag_open` overlay appears only in TILE reads, never in `sk.search`
  lines — bag_body verifies via `sk.tile(..., all=True)` and excludes
  remembered "last seen" mob lines. Labeled bag names persist
  ("body bag - Leia Weinstein - Human").
- **Surgery aid** (surgery_aid.dm): drapes OR a bedsheet works; the aid item
  is NOT consumed — prep is a `surgery_prepped` status effect listing aid
  names (examine: "surgical drapes adorning his chest"). Clicking the SAME
  zone again CLEARS it ("surgery cleared") — the script re-clicks once to
  re-apply. Prep is per-zone; a standing patient that moves much strips it.
- **Autopsy chain gotchas**: the retract-skin step is the one people forget —
  skip it and the scanner's cadaver healthscan ("ANALYZING CADAVER") preempts
  instead of the autopsy op. A single available op auto-runs (no radial).
  Chat-success check ("You succeed") runs BEFORE the re-click probe, because
  SURGERY_SKIN_CUT persists after retract (ORs, never clears) and the probe
  would re-run the op. "nothing to do with X!" = that step is already done;
  "not lying down!" = patient standing; "operation site is obstructed!" =
  clothes on.
- **One autopsy per corpse**: dissected corpses get TRAIT_DISSECTED — further
  scanner clicks just healthscan.
- **Records limits**: ui_act values pass `reject_bad_name` strict (letters/
  numbers/spaces only); a record keeps max 2 notes (oldest cut); setting a
  physical status other than Deceased CLEARS cause_of_death. Records list
  only GLOB.manifest.general — round-start corpses dead 1397 days are NOT in
  records (the paper autopsy report is their record).
- **Laptop click needs an EMPTY active hand** (item-in-hand = attackby, not
  open). Both scripts upgrade the hand: X-swap first, then Q-drop (drops
  recorded in the verdict for tidy-up).
- **Jump To Coordinate while carrying items is fine** (bedsheet round-trip:
  picked up at the Morgue, jumped to the Captain's Quarters, dropped there).
- **sk.search matches NAMES only**, never numeric ids — to find a known id,
  scan the full in-view list (`query=""`) and match the id in the line.
- This round's morgue end-state: two corpses stored (morgue2) in labeled
  closed bags, one Vampire corpse untouched (morgue3); all trays retracted;
  an empty unit's beeper restored enabled; autopsy reports on the desk tile
  (99,82); tools returned to Robotics Lab (117,92).
