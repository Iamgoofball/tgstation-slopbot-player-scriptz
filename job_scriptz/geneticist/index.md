# job_scriptz/geneticist/

The DNA jockey: read a subject's genome, discover its mutations, print
injectors. Genetics Lab (MetaStation) has THREE console/pod pairs — west
(console at 110,81 + pod at 110,80), centre (console at 114,82 + pod at
114,81) and east/main (console at 114,84 + pod at 114,85). Ids re-roll every
round: pass `console`/`scanner` args or let the scripts take the nearest
pair.

## Scripts

| Script | Args | What it does |
| --- | --- | --- |
| `genetics_lab_check.py` | `console?`, `scanner?`, `x?`, `y?` | One-envelope lab survey: pod icon_state (scanner / scanner_open / scanner_occupied / *_unpowered — read from the TILE, dark tiles included) + console envelope (isScannerConnected, scannerOpen/Locked, isViableSubject, subject name, injector/scramble ready, storage.occupant mutations with Discovered/Active/Name/ByondRef). Verdicts: not linked, unpowered, no viable occupant, locked bolts, N undiscovered, cooldowns. Read-only. |
| `dna_scanner_control.py` | `mode`: open/close/toggle/load/lock/unlock, `scanner?`, `console?`, `load`?: mob id | Pod door + bolts. open/close = EMPTY-HAND click on the pod (item in hand does NOT toggle); closing captures whoever stands on the pod tile, opening drops the occupant there. load = drag the mob onto the pod (any carbon, mouse_drop_receive); if the mob already stands ON the pod tile it closes via click instead (same-tile drags turn into hugs). lock/unlock = console `toggle_lock` (bolts: a locked pod can't be opened from inside without resisting). |
| `dna_injector_print.py` | `mutref`? or `alias`?, `source`?="occupant", `is_activator`?=0, `discover_all`?, `pickup`?, `console`? | Prints a mutator (applies the mutation) or activator (research/recycling) injector. `discover_all` runs the console's all_check_discovery first (verified: revealed Monkified on an all-unknown occupant). Alias substring-matches storage.occupant; refuse path (cooldown / anomalous mutation) detected via isInjectorReady staying 1 — no phantom pickup. The fresh injector lands on the console tile; `pickup` clicks it into the active hand. |

## Live notes (round-labeled observations, not durable truths)

- **Getting a subject**: monkey cubes expand into monkeys when SPRAYED with
  water (fire extinguisher with safety off, shower) — `water/expose_obj`
  calls `cube.Expand()`. Toilets/moisture traps do NOT work (their
  is_reagent_container branch runs first and swallows the cube).
- **Loading the pod**: drag the mob onto the pod (works with the pod OPEN,
  mob diagonal-adjacent). `open_machine` drops the released occupant back ON
  the pod tile, so open→close captures again with a plain click.
- **Pulling monkeys**: ctrl+click toggles pull; the pull HUD ("stop pulling",
  obj state `pull` vs `pull0`) is the only reliable read. Monkeys wander —
  park them immediately.
- **Dark pod tile**: the east pod sits in the dark; `sk.tile(x, y, all=True)`
  still reports remembered contents with current icon_state. The search
  index can lag a beat behind a state change — tile reads don't.
- **Console needs an empty active hand** to open; from INSIDE the pod the
  console UI cannot be opened.
- **print_injector cooldown** ≈ 1 minute (injector_ready guard, silent
  refusal — check isInjectorReady).
- Monkey subject verified: `isViableSubject 1`, subject "monkey (592)",
  8 occupant mutations, Monkified active (Type /datum/mutation/race).
