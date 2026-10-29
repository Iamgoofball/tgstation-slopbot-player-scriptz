# job_scriptz/chemist/

The chemist's routines. Machines: the **Pharmacy** has two workstations —
south (dispenser @103,101 / chamber @102,99 / ChemMaster @103,99) and a
north-east set; the Chemistry lab has a third set. Find machines by NAME
(dispenser / reaction chamber / ChemMaster) — ids change every round and the
scripts auto-survey the nearest machine in view.

| Script | Args | Purpose |
| --- | --- | --- |
| `chem_lab_check.py` | `dispenser?`, `chamber?`, `master?`, `reactions_wait?`=3 | ONE-envelope survey of a workstation: dispenser energy/amount/beaker, chamber temp/power/buffers/activeReactions (+quality after a wait), ChemMaster beaker/buffer/printing. Verdicts: energy <20%, chamber OFF with reactions pending, purity <0.6 (buffer the pH), ChemMaster isTransfering=0 (transfers back DESTROY), buffers <5u. |
| `chem_dispense.py` | `reagents` [names], `amount`?, `dispenser?`, `beaker?`, `remove_all?`, `eject_after?` | Drive the dispenser: inserts a beaker (hand → floor-search), sets amount (must be a transferAmount: 5/10/15/20/25/30/50/100), dispenses each reagent, verifies every step from the act answers. GUARD: refuses Water with Potassium in the beaker and vice versa (instant explosion). |
| `chem_heater.py` | `temp`?, `power`?, `insert`?, `eject`?, `ph`? {direction, units 1-10}, `watch`?, `chamber?` | Drive the reaction chamber: insert/eject beaker, target temp (0-1000), power toggle, pH adjust via disp_vol + one buffer press, watch a reaction's temp/quality. Flags targets above known overheat limits (Aiuri 315, Synthflesh 325, Multiver 410, Inacusiate 500, Oculine 600). |
| `chem_master_print.py` | `transfer` [{reagent, amount}], `container`? {category, match/index}, `item_count`?, `name`?, `pill_duration`?, `eject_beaker`?, `master?` | Print labelled medicine: move reagents beaker→buffer (ref matched from contents), select a container style (static_data.categories: tubes 30u / pills 50u ×24 / patches 40u; match on icon_state like "bandaid"), create N → answers the Name TextInputModal → waits out 0.75 s/item → lists the prints on the tile. Swaps in a hand beaker when the slot holds a stale empty one. |

Fork truths learned here:

- **ChemDispenser**: `data.displayedUnits/maxUnits` (energy, ~1u cost per
  1u dispensed), `data.amount` (per-press), `data.beaker {currentVolume, pH,
  contents[]}`, `data.chemicals[]` (25 dispensables, each with pH). Acts:
  `amount {target}`, `dispense {reagent: "Water"}`, `remove {amount}` (a
  transferAmount), `insert`/`eject`. hasBeakerInHand flag mirrors your hand.
- **ChemHeater**: `data {targetTemp, currentTemp, isActive, acidicBufferVol,
  basicBufferVol, dispenseVolume, activeReactions[]}`. Acts: `temperature
  {target}`, `power`, `insert`, `eject`, `disp_vol {target: 1-10}`, then ONE
  `basicBuffer {target: 1}` / `acidBuffer {target: 1}` press injects
  dispenseVolume units (the press's own `target` is ignored beyond 1 —
  verified: basicBuffer target:5 injected 1u). pH math: 1u basic buffer on a
  30u beaker = +1.0 pH (30 ÷ volume).
- **ChemMaster**: `data.beaker.contents[].ref` = `/datum/reagent/...` paths
  for `transfer {reagentRef, amount, target}`; `buffer` caps at 100u;
  `isTransfering` 0 means transfers BACK to the beaker DESTROY. Containers
  from `static_data.categories` (read with `tgui_window path:` — the
  categories are NOT in the normal window text): tubes/pills/patches, each
  container {ref, name, icon_state, volume}; `selectContainer {ref}`;
  `create {itemCount}` opens a **TextInputModal "Name"** (max 42 chars) —
  submit `entry`, then printing runs 0.75 s per item (`isPrinting`/
  `printingTotal` in data), prints land on the machine's tile.
- **The master grabs a hand beaker on click** (insert-on-click) — so DON'T
  empty the hand before opening it; but a held NON-beaker = use-on-machine
  (opens nothing). A stale EMPTY beaker in the slot (vol 0, contents [])
  satisfies the "inserted" check but starves the transfers — the script
  ejects + swaps in the hand beaker in that case.
- **Act answers (`data_changes`) lines are UNQUOTED and TRUNCATE mid-key**:
  `- beaker.currentVolume: 0 -> 30` and `... "currentV... -> null` — parse
  `beaker\.currentVolume: X -> Y` without quotes and never expect a closing
  brace on ejected-beaker values.
- **Power death signature for a lab**: `sk.click` on a machine answers
  `note: nothing visible happened` AND a `help:` line naming the area's APC
  ("Pharmacy APC shows its equipment power off, and it is not charging").
  The whole Pharmacy set went silent mid-testing when its SMES ran dry —
  quickpower revived all three machines at once.
- Beaker accounting is the hidden hazard: between the dispenser, chamber,
  master and your hands there are 3 beakers (2 large 1 small in the
  Pharmacy); scripts must re-locate their beaker every run (hand → slot →
  floor search), never assume.
- Test prints (tubes/pills of Nitrogen) were left labelled "(test)"/"(final)"
  on the ChemMaster tile — scoop into a pill bottle before real work.
