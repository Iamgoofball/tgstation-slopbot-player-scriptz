# job_scriptz/scientist/

R&D: research the techweb, keep the lathes fed and printing. MetaStation lab
layout (verified): R&D Console at (125,104), department protolathe at
(125,102), circuit imprinter at (124,102), destructive analyzer at (124,104),
iron + glass sheet stacks and a wrench on the table at (122,102), flatpacker
at (122,104). The Experi-Scanner ("experimental destructive scanner", a tube)
lives in the Science Lobby at (116,111) — not the lab. BCI chamber at
(128,102) in the Experimentation Lab. Spawn kit (verified): science backpack,
labcoat, jumpsuit, sci headset, PDA, ID.

## Getting into the lab (the maze)

- From the Science Lobby the lab is SEALED for walking: the west shutters
  (x=119, y=102/104/106) hold full-tile windows (impassable even with the
  shutters open), the maintenance door at (124,113) needs maint access, and
  the north door (121,101) sits behind a firelock.
- Prying the Research Division firelock at (117,107) from the Central Primary
  Hallway only reaches the change room (117-118, 105-106, sink/shower) — the
  R&D shutters behind it are windowed too. Dead end.
- The walking route is long: Aft Primary Hallway → door (110,99) → Research
  Division corridor y≈99-100 → crowbar-pry the north firelock at (121,101).
  It cost ~20 tool calls to map and still failed on the unexplored tiles.
- **Practical entry: admin Jump To Coordinate (122,105,2)** (3 NumberInputModal
  submits, re-scan `tgui_windows(all=True)` between submits). Use it.

## Firelocks (verified on a Research Division firelock)

- Closed by a fire alarm; empty-hand click / bump does NOTHING ("you knock").
- Crowbar in the ACTIVE hand: LEFT-click = pry open temporarily (closes
  again), then move through immediately (arrow-key `sk.move` beats the
  planner, which re-routes through closed doors it remembers). RIGHT-click =
  "open permanently" per examine — one attempt only showed `door_closing`;
  the left-click pry + immediate walk-through is the verified method.
- A firelock tile can host TWO door objects (firelock + access door) — read
  the tile with `all=True` and match `door_open`.

## Scripts

| Script | Args | What it does |
| --- | --- | --- |
| `rd_lab_check.py` | `no_walk`? | One-envelope lab survey: R&D console (points, queue, sec protocols, locked, experiments count), department protolathe + circuit imprinter via their Fabricator tguis (silo materials, busy, onHold — walks to stale machines via known-index coords, area-name fallback), destructive analyzer examine, Experi-Scanner location, sheet stacks in view, BCI chamber. Verdicts: points banked → research now, lathes empty/on hold, scanner not in the lab, no sheets for the imprinter. |
| `rdconsole_research.py` | `mode`: status/research/enqueue/dequeue/lock, `console`?, `node`? | R&D Console (Techweb tgui) driver. status = points/per-tick/queue/protocols/lock; research = `researchNode {node_path}` verified by the console chat line "Successfully researched X." (a successful research also unlocks experiments); enqueue/dequeue verified via the ACT's `queue_nodes: list of N -> M`; lock = toggleLock (warns when left locked). Needs an EMPTY active hand to open. |
| `protolathe_print.py` | `mode`: status/list/build/insert/eject, `design`?, `amount`?, `wait`?, `sheet`?/`sheet_name`?, `pattern`?, `machine`? | Thin wrapper → `machines/fabricator_control.py` with the Science protolathe as the default machine (same driver runs the circuit imprinter and every department techfab — pass `machine: "circuit imprinter"`). See the machines index for the full arg set and facts. |

## Live notes (round-labeled observations, not durable truths)

- **The server runs AUTORESEARCH**: available techweb nodes get researched by
  the server itself (~30-40 points a minute observed) — the queue empties
  within a minute of an enqueue. Enqueue racing is futile; leave useful nodes
  queued and let the server work.
- **Points grow passively +1/sec** — NEVER verify research by the points
  delta. The chat line ("Successfully researched X." / "Node enqueue failed:
  ...") and the act's data_changes are the checks.
- researchNode spends points AT ACT TIME (Upgraded Parts: 80) and unlocks
  experiments (data_changes: experiments list grows, new
  `static_data.experiment_metadata.<id>` entries).
- **Enqueue only accepts AVAILABLE nodes** (prereqs researched, itself not).
  First attempt on an unavailable node is a SILENT no-op; a repeat says
  "Node enqueue failed: Either no techweb is found, node is already
  researched or is not available!". Dequeueing a non-queued node fails the
  same way. Queue growth shows as flat pairs (a node id + the researcher
  name) — ONE queued node moves the length by 2.
- Round-start-researched nodes can't be re-ensequeued either — adv_power,
  surgery, bio_scan, chem_synthesis all refused; holographics accepted
  (prereqs energy_manipulation + parts_upg, both researched by me) and the
  autoresearch then researched it from the queue.
- **Fabricator model**: `build {design_path, amount}`, `remove_mat {amount,
  ref}`; `data.materials[].{name, ref, amount}` come from the SHARED ORE
  SILO; `materialMaximum` 7500 is the fab's own store cap;
  `static_data.designs.*.path` (84 designs after a shift of research; 1
  sheet = 100 units, a 50-sheet stack = 5000).
- **Opening needs an EMPTY ACTIVE hand** (a held item attackbys); inserting
  needs the sheet IN the active hand + adjacency (dense machine tiles park
  `bot.goto` adjacent); the pickup moves you to the sheet's tile — walk BACK
  to the machine before the insert click (the driver does).
- **Prints eject onto the machine tile or a neighbor** — the fresh beaker
  landed on the protolathe tile beside the screwdriver; the 3x3
  `printed_nearby` scan lists everything there, match the design name.
- **search by obj id does NOT match the in-view page** — search ids against
  the known index (omit `in_view`), or search by name; the driver tries both.
- Experiments system (destructive analyzer + Experi-Scanner loop) is
  UNTESTED — the analyzer and scanner were only located, not driven. Next
  scientist round: analyzer insert → experiment selection → points.
- This round's lab state: silo 13993 iron + 5000 glass; screwdriver + beaker
  printed on the protolathe tile; researched: energy_manipulation, parts_upg,
  holographics (autoresearch).
