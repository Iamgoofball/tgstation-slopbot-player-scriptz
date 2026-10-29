# medical/

Patient care: scan, treat, revive. All returns are parsed dicts (numbers +
flags), never raw scan text — `verbose=true` opts into a raw tail.

| Script | Args | Purpose |
| --- | --- | --- |
| `analyze_patient.py` | `mob`, `expect_name`, `verbose?` | Analyzer scan → `{health, brute, burn, tox, oxy, blood, dead, bad_organs, dark}`. Auto-finds the analyzer (hand → X-swap; floor → pick up). |
| `inject_medipen.py` | `pen?`, `mob?` | Medipen into self (default) or target; verifies the inject message. Epipen **stops heart-rot**. Single-use; spent = "empty medipen". |
| `apply_medkit_item.py` | `item` (id or kind), `container?`, `mob`, `mob_name?` | Take one item from a container UI (alt-click opens it) or floor and apply to the mob; returns `ok`, stack `uses` left. Kinds: suture/mesh/gauze/ointment/bruise. |
| `inject_reagent.py` | `mob`, `container_query?`, `purge/draw/inject_clicks?` | Syringe delivery: purge preload into self (vendor syringes come preloaded), RMB-draw from a container, walk to the mob, LMB-inject. Fork: **LMB injects, RMB draws — no mode toggle**. |
| `treat_patient.py` | `mob`, `expect_name`, `medkit?`, `max_rounds?` | **One envelope**: scan → suture brute / mesh burn until clean or items out → re-scan → before/after deltas. |
| `defib_revive.py` | `mob`, `expect_name`, `mount?` | Gate (dead? brute/burn < 180? heart?) → paddles from mount → wield → combat off → shock → verify "Resuscitation successful" → re-scan. |
| `surgery.py` | `mob`, `expect_name`, `tool`, `op`, `drape?`, `wait?` | ONE radial-menu surgery op: ensure tool in active hand, (re-)drape, click patient, parse `menu_opened` from the click answer, click the op button at once, wait, verify via chat. See the surgery truths below. |

Surgery truths (hard-won, live-verified):

- **The radial lives in the click answer.** Click the draped patient with a
  surgical tool → the answer carries `menu_opened:` with `- obj <id> "<op>"`
  choices. Those ids are only good for that menu — click the chosen one
  *immediately* (same script, no gaps); menus close on movement/timeout and
  clicking the patient again TOGGLES the menu closed. `sk.screen(all=True)`
  does **not** show radial slices reliably.
- **Surgical drapes prep expires (~2-3 min)** — every other op then dies
  silently ("nothing to do with X!"). Re-drape before each op in a chain
  (`drape: true` in `surgery.py`). Drape click = "Prepare <zone> for surgery";
  the zone comes from the damage-zone doll (HUD `damage zone`, click the doll
  area — head is px 12-20 / py 23-30).
- **Tool → op map** (chest chain): drape → `make skin incision` (scalpel) →
  `retract skin` (screwdriver 2.25× if no retractor) → `clamp bleeders`
  (hemostat) → `saw bone` (circular saw; scalpel force 10 also passes) →
  `incise organs` (any sharp edge — NOT the saw) → organ repair ops.
- **`tend bruises` (hemostat) LOOPS until brute = 0** and blocks every other
  surgery while running (`OPERATION_LOOPING` + `can_loop`). Great: one click
  fully de-brutes a corpse. Bad: it eats clicks meant for other ops — wait it
  out or pick the explicit op from the radial.
- **Floating "he is dead!"** = the ACTIVE hand held a medical stack/medkit
  (wrong hand), not a surgery refusal. Always verify the active-hand line in
  `sk.inventory()` before corpse clicks; Q-drop / X-swap first.
- **Floating "already performing surgery!"** = an op is mid-`do_after`; wait
  (~the op's duration) instead of re-clicking.
- **Organ repair ops are one-shot per organ** (`TRAIT_ORGAN_OPERATED_ON` is
  added on *success*): after a successful "graft coronary bypass" the choice
  vanishes from the radial forever. Success sets organ damage to 60% of max,
  which clears the failing flag — that's what makes the heart defib-able.
- **Bypass requires the full chest state** (skin open + vessels clamped +
  organs incised + bone sawed) — a menu without "graft coronary bypass" means
  a state step is missing (usually `incise organs`).
- **Decayed corpses may be beyond repair**: organs rot past healing ("decayed
  for too long... probably won't work without repairs" on examine). Fallback:
  `remove heart` + implant a fresh donor heart (morgue trays preserve bodies;
  smart organ storage fridges are usually empty). The defib also refuses a
  Non-Functional **brain** → head chain (drape head zone → incise → retract →
  clamp → saw → incise → brain repair) is needed before revival.
- **Medkit/containers need an EMPTY active hand to open**; contents appear as
  a screen strip (gauze/mesh/cautery/drapes as clickable screen objects).
- Corpse surgery works on the dead for all the ops above
  (`OPERATION_NO_PATIENT_REQUIRED`); blood pools and scars remain but don't
  gate the defib — brute < 180 and heart/brain not failing do.

Stack values (fork source, `stacks/medical.dm`): suture **10 brute**,
medicated suture 15, regen mesh **10 burn** (+flesh regen 3), bruise pack 40
brute, ointment 5 burn; gauze = bleeding only. Stacks **refuse corpses**;
**gauze works on the dead**.

Gotchas
- Defib fails at brute/burn **≥ 180**; heart must be better than
  **Non-Functional** ("Severely Damaged" is fine). Revived at **-50 health** —
  keep treating after the ping.
- The defib shock **zaps the puller and breaks the pull** — never be pulling.
- Grand Surgery Theatre is dark (broken tube): analyzer reads "It's too dark
  in here to read!" there — treat in the Treatment Center instead.
- **Tox does NOT decay on its own** (fork source: `set_health` subtracts tox;
  nothing in `life.dm` heals it passively — live-verified: tox 7 sat still for
  20 min). Heal it with multiver/syriniver: NanoDrug Plus sells a **multiver
  bottle (10 cr with MD discount)**; delivery = vendor syringe (spaceacillin,
  5 cr) via `inject_reagent.py`. Health = maxHealth − oxy − tox − fire − brute.
- **X-swap frees NO hand** — it only switches which hand is active. To pick a
  floor item with both hands full you must **Q-drop the active item** first.
- The client **forgets mobs that leave view** (their ids too) — re-find by
  name via `search(all_things=True)`; `bot.goto(object_id=…)` can fail
  silently then, prefer `goto_tile` with coords.
