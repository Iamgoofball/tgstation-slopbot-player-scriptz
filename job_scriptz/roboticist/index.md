# job_scriptz/roboticist/

Build and maintain cyborgs, bots and mechs in the Robotics Lab + Mech Bay
(MetaStation: fabs at (110,95) + (110,93), borg chargers at (110,103) +
(110,105), mech bay power ports at (114,103)/(114,105), cell chargers,
mech bay power control console at (114,102)/(114,106)). Spawn kit (verified):
science backpack, toolbelt (tools), Roboticist ID, PDA. The lab tables hold
the supplies: iron/glass/plasteel sheet stacks, 4 flashes, toolboxes,
multitool, welding helmet + goggles, roboticist spraycan, Robotics for
Dummies, Ripley exosuit boards, spare MMIs (3 empty at (118,95)), a bare
cyborg endoskeleton, a cyborg reclassification board.

## Scripts

| Script | Args | What it does |
| --- | --- | --- |
| `robotics_lab_check.py` | `fabs`?, `no_walk`? | One-envelope lab + Mech Bay survey. Walks room-to-room as needed (known-index coords → goto, falling back to the loaded map's area names when the path is blocked): both exosuit fabricators via their tgui (materials from the shared ORE SILO, queue, processing), recharging stations (occupied?), cell chargers, mech bay power control console (`recharge_port.mech`), plus endoskeletons/MMIs/mechs in view. Verdicts: fab empty → load metal, queue running, no mech docked, no shell on standby. |
| `exofab_control.py` | `mode`: status/list/build/insert/clear_queue/del/stop, `fab`?, `design`?, `now`?, `wait`?, `sheet`?/`sheet_name`?, `pattern`?/`category`?, `index`? | Fabricator driver. status = materials/queue read; list = designs (path/name/cost/time, filterable); build = resolve design by name-or-path → `build {designs, now}`, verifies the queue + iron deduction, `wait: true` polls to completion and lists the printed parts near the fab; insert = grab the sheet (id or name), walk adjacent, click the fab, verify via the ore-silo chat line AND/OR material growth in the window; clear_queue/del/stop manage the queue. |
| `shell_check.py` | `ids`?, `kind`? | Read-only audit of endoskeletons, MMIs (brain state via icon_state: `mmi_off` empty / `mmi_alive` / `mmi_dead`), finished cyborgs (charge %), mechs (beacon/DNA-lock lines) and reclassification boards in view. Verdicts: empty/dead-brain MMI must not be shelled, mech missing beacon/DNA lock, borg low charge. |

## Live notes (verified this round)

- **Materials live in the ORE SILO**, not the fab: inserting a sheet stack
  says "50 iron sheets were added to the ore silo" and every fab's window
  shows the same silo amounts (both fabs read iron identical). A "sheet"
  item is a 50-sheet stack = 5000 units (SHEET_MATERIAL_AMOUNT = 100).
- **Opening the fab tgui needs an EMPTY active hand** — a held item
  attackbys instead (with sheets that inserts them). All scripts X-swap
  then Q-drop to free the hand and record the drops.
- **Insert needs adjacency** (5 tiles away does nothing); a dense fab tile
  is fine as a `bot.goto` target — the tool parks on a neighboring tile
  ("taken by obj ...: next to it"). Same for the power console.
- **build** deducts the cost AT QUEUE TIME (Cyborg Head 250 iron:
  5000 → 4750) and the answer's data_changes show queue + processing;
  `constructionTime` is deciseconds (borg head ~33s). Prints eject onto the
  fab tile or a NEIGHBOR (heads + arm landed at (111,95) for the fab at
  (110,95)) — scan the 3x3 for the fresh part.
- **Queue timing traps**: stop_queue does not visibly pause a running job
  (the print finished anyway); clear_queue on an already-empty queue
  answers "unchanged" — read the queue right before and after, and treat
  "empty after" as success.
- **Design model**: `static_data.designs` is keyed by `/datum/design/*`
  path with name/cost/categories/constructionTime; `build {designs}` takes
  the PATH (resolve name → path first — the script does).
- **MMI brain state is the icon_state** (organic.dm): mmi_off = empty,
  mmi_alive = brain inside and alive, mmi_dead = brain inside and dead.
  The examine text says NOTHING about the brain — never trust it.
- **Mech detection traps**: "mechanical toolbox" matches a naive "mech"
  search, and Ripley circuit boards match "Ripley" — filter names
  `(Ripley|Odysseus|Gygax|Durand|Phazon)` MINUS `board|module|console|control`.
- **Room-to-room walking**: known-index lines ("left the view; last seen")
  still carry coords — use them for `bot.goto`; when the path is unknown
  ("no known path": tiles unseen or a firelock blocks), fall back to the
  loaded map: `search {kind: "area"}` → `- area "Robotics Lab" at ...`
  → `sk.walk_to(area=...)` (regex needs re.I — names are capitalized).
- This round's lab state: silo loaded to 14000 iron; printed parts (2
  robotic heads + robotic left arm) near the fab; pre-existing arms on the
  parts table; 3 empty MMIs + endoskeleton + reclassification board in
  place; both chargers empty; no mech docked.
