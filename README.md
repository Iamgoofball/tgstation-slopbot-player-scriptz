# tgstation-slopbot-player-scriptz

Reusable `run_script` Python components for driving a live tgstation session through
the **seeker** MCP tools. Every script here is generic (parameterized by `args`),
small, and composed of steps that verify their own outcome. Round-specific IDs,
areas and names are **arguments, never hard-coded**.

Run from the agent side like:

```
run_script {script: "E:/byond_agent_test/tgstation-slopbot-player-scriptz/medical/analyze_patient.py",
            args: {"patient": 2892}, timeout_s: 120}
```

(`script` takes an absolute path; if the runner rejects it, run the file's text as
`code` instead — every script here is self-contained.)

## 1. THE SAFETY WATCHDOG — MANDATORY (engine delam cost us Lennox Fields)

**Every script now self-checks at start**: a 4-line header at the top of every
script loads `common/watch_prelude.py` and calls `precheck()` — chat + status
are read BEFORE anything else, and the script aborts (SystemExit) on danger
(delam, countdown, blast, flood, fire, shock, attack, ghost/crit/dead status).
**`common/check.py` and `common/watch_prelude.py` are the only files without
it.** Mid-script checks still use the embedded `watch()` between steps; the
agent must still read the returned digest and re-check with `common/check.py`
between run_script envelopes.

**Every script that does more than one world-affecting step MUST check chat and
status between steps, and ABORT (raise `SystemExit`) the moment anything bad
appears.** "Bad" includes: supermatter delamination/integrity warnings, any
countdown, explosions/fires, alerts, someone attacking you, gas flooding,
shock/electrocution, or your own status showing damage/crit/dead. Reading chat
and status is CHEAP (`read_chat(wait_s=1)` + `sk.status()`); dying or losing a
round is not. The agent must also READ the script's returned watchdog line and
STOP the session-level plan when danger is found — do not fire the next script
while the last one screamed.

Canonical snippet — paste into every multi-step script and call `watch()`
between steps (and once at the end before returning):

```python
DANGER = (r"delaminat|integrity|countdown|blast|explod|detonat|flood|fire|"
          r"electroc|shock|attack|griff|hurt|wound|husk|bomb|causality|"
          r"radiation (burn|poison)|warning|emergency|verrorarily|toxin")
def watch(tag=""):
    ch = re.sub(r"<[^>]+>", " ", sk.read_chat(wait_s=1).text or "")
    hits = re.findall(r"[^\[]{0,60}(?:%s)[^\n]{0,60}" % DANGER, ch, re.I)
    st = (sk.status().text or "")
    crit = re.search(r"\[(ghost|crit|dead|unconscious)\]", st, re.I) or "brute" in st or "burn" in st[:400]
    if hits or crit:
        raise SystemExit("ABORT danger %s: %s | status: %s"
                         % (tag, hits[-2:], st[:100]))
```

Rules attached to it:
1. `watch()` runs between EVERY step of a loop (per machine id, per spot, per
   emitter), not once at the end.
2. On abort, the script's error tells the agent what happened — the agent reads
   it and changes plan (flee, fix source, call for help) before ANY further
   scripts.
3. Big irreversible actions (turning emitters ON, opening valves, enabling
   siphons, wrenching into ports) get a `watch()` IMMEDIATELY after and a
   status+CIMS-style re-verify before continuing to the next thing.
4. Single-step scripts (reads) don't need it; anything that writes to the world
   does.
5. **Between run_script envelopes the AGENT must read the returned
   chat/status digest and glance at `sk.read_chat` on its own before firing
   the next script** — the watchdog inside scripts catches what happens
   DURING a script; the agent owns everything between scripts.

### Speech check is built into run_script itself (seeker-mcp)

Every `run_script` envelope now carries a **speech check from the wrapper**:
the runner snapshots chat before AND after each run and appends an explicit
`── Speech (since last run — READ THIS) ──` text section (and
`structuredContent.speech = {between, during, needs_response}`) listing
everything anyone said since the previous envelope — parsed into
`{who, text, channel, mine}`. `needs_response` flags questions/imperatives/
mentions of our name. This means speech that arrived BETWEEN envelopes (the
classic blind spot where the before-digest used to swallow it) can never be
lost. The agent MUST read that section on every envelope and answer
`needs_response` lines before continuing work.

### View census is built into precheck/postcheck (common/watch_prelude.py)

Speech isn't the only blind signal: **dangers that never reach the chat log**
(fires, hostile mobs, hull breaches, plasma) are caught by a cheap **ASCII
view census** in `_view_census()` — one `sk.look()` (the MCP's text map;
falls back to `search(query="", in_view=True)`) per check. Every
precheck/postcheck/watch now returns (and pre/post/watch ABORT on)
`view.threats` — objects in view matching `VIEW_THREAT` (fire-not-alarm,
plasma, singulo, blob, xenomorph, breach, tesla, ...) — plus `view.areas`
(sorted area names in view), `view.mobs` (other mobs nearby), and
`view.overlay` (what Dream Seeker draws OVER the map: hurt/damage overlays,
blindfolds — a brute-damage overlay in the census is a prompt to self-treat).
The area list is also the fastest way to *navigate*: if an area name shows up
in the census (e.g. a docked "Emergency Shuttle"), `bot.goto(area=...)`
reaches it in one call — this is how the round-end shuttle was finally
boarded after name-searches kept missing its misnamed ("Departure Lounge
Airlock") doors.

---

## 1. How scripts run

- `seeker-mcp`'s `run_script` executes Python (stdlib only, **no pip**) locally against
  the shared game session. Tool calls and script calls cross the same tunnel/WS.
- The runner injects globals:
  - `args` — dict passed via `args: {...}` (never assume keys exist: `opts = args or {}`)
  - `sk` — the raw tool client (`sk.click`, `sk.drag`, `sk.search`, `sk.read_chat`, ...)
  - `bot` — high-level helpers (`bot.goto`, `bot.goto_area`, `bot.click_thing`, `bot.find`, `bot.open_machine`, `bot.window_state`, `bot.read_new_chat`)
- `import re`, `time` work; so does anything else in stdlib. **No pip installs.**
- `print(...)` → shows up in the envelope's `logs`; the final expression or an
  explicit `return`-style dict → `result`. **The result must be JSON-safe**
  (str / int / float / bool / None / list / dict). Tool answers are answer objects
  with `.text` — truncate with `[:N]` before returning.
- Envelope: `{ok, result, logs, error, elapsed_ms, digest}`. If `error` is set, the
  script raised — treat the whole run as failed, not as a partial success.

## 1.5 Cost discipline (a full defib sequence once cost ~$1 of context)

1. **Return numbers, not narratives.** A script's default return is a *small* dict
   (≤ ~300 chars): booleans, counts, parsed values. Raw evidence only behind
   `args: {"verbose": true}`. Never return a whole scan report, chat dump, or
   click answer.
2. **Batch micro-steps inside one script.** `drop → take → swap → click → verify`
   is ONE `run_script` envelope, not five tool round-trips. Every round-trip pays
   for the whole envelope again.
3. **Run files, don't inline code.** `run_script {script: "path", args: {...}}`
   makes the per-call output one line; inlining 30-line Python per step is the
   expensive way to repeat boilerplate.
4. **Read the index/README before experimenting.** The fork truths below cost
   real money to derive; re-reading them costs pennies. Never re-derive an
   established truth by trial and error in-game — that's what burned the dollar.
5. **Keep `print` under ~10 short lines.** Logs ride along on every envelope.
6. **Slice every tool text** (`[:200]`-style), keep `page_size` small, and grep
   game source with narrow patterns — never pour whole `.dm` files into context.
7. **Don't re-verify what a prior step in the same script already verified.**
   One truth per step; capture it once, return it compactly.

## 2. Best practices (learned the hard way — keep following them)

1. **One script = one concept.** Walk somewhere, flip a switch, apply one medkit
   item. Orchestration (analyze → treat → re-scan) lives either in a small
   "flow" script or in the agent chaining several `run_script` calls.
2. **Verify after every world-changing action.** A "clicked" line in the answer
   does NOT mean the game did anything. After a move: re-search the mob. After a
   take: re-check `sk.inventory()`. After a drag: re-check the tile.
3. **Chat is ground truth.** The game says what it did: `You grab X passively!`,
   `Resuscitation successful.`, `It's too dark in here to read!`. Always
   `sk.read_chat()` after a medical/interaction step and match on those lines.
   Balloon alerts often do NOT appear in chat — don't rely on them.
4. **Fail loudly.** End with `{"ok": False, "stage": "what step", "detail": ...}`
   instead of returning garbage and letting the caller guess.
5. **Parameterize everything.** IDs, area names, coordinates, thresholds — all
   from `args` with sane defaults and explicit errors when missing.
6. **Idempotency.** Re-running should not make a mess: unbuckle only if buckled,
   take only with a free hand, load a defib only if the mount is empty.
7. **Time-budget every loop.** Never `while True`. Poll with a max-iteration
   count and a small `time.sleep` between checks; report how many rounds it took.
8. **Handle client memory eviction.** Things that leave the view can be *forgotten
   entirely* (`Error: no obj or mob NNN known`). Before acting on an ID, search it
   into view (walking toward its last known tile); after a long walk, re-search
   the thing you were following — pulls can also break silently.
9. **The client is not a mind reader about adjacency.** Reach is one tile (plus
   diagonal quirks and windows blocking clicks). Walk next to the target with
   `bot.goto(object_id=..., adjacent=True)` before interacting.
10. **Keep the active-hand discipline.** Most "nothing happened" mysteries were an
    item sitting in the active hand eating the click. Check `sk.inventory()`'
    `active_hand` line before acting; drop (`Q`) or swap (`X`) as the step needs.
    **Q is dangerous**: it drops whatever is active — it once dropped the PDA
    mid-flow. Know exactly what's in the active hand (read inventory first);
    prefer stowing in the backpack over dropping.
11. **Combat mode off for care actions.** With combat on, clicks harm instead of
    help (defib harm-zaps, punches). The HUD button `toggle combat mode` shows
    `state=combat_off` when safe — check it in scripts that could hurt someone.
12. **Map memory dies with the MCP process.** After a wrapper reboot the loaded
    map is gone; long walks fail with "no known path". Re-run `setup/load_map.py`.
13. **`digest` is unreliable.** The envelope `digest` may be `[]` even when the
    script moved the mob — do your own before/after capture, don't trust it.
14. **Duplicate tiny helpers, don't import.** A 10-line `parse_thing()` repeated
    in a few files beats a shared module the runner can't resolve. Keep helpers
    that small.

## 2.5 tgui semantics traps (source-verified, cost real damage)

Read the `.dm`/`.tsx` source before trusting an action's meaning — all of
these bit us in one session (`tgstation/code/modules/atmospherics/machinery/
air_alarm/_air_alarm.dm`, `tgui/.../AirAlarm/screens/Home.tsx`):

- **`excheck` is XOR, not a setter**: `params {val: 1}` CLEARS the external
  pressure bound; `val: 0` is a silent no-op. (`pressure_checks ^
  ATMOS_EXTERNAL_BOUND`.)
- **Scrubber polarity**: `scrubbing {val: 1}` = scrub MODE (only removes
  *selected* gases — select none and it removes nothing); **siphon is
  `val: 0`** (`set_scrubbing(true)` = scrub). We set "siphoning" that was
  actually scrub-mode and O2 climbed unchecked → near-delam.
- **`external: 0` with the check enabled = the vent NEVER pumps** (target
  below atmospheric minimum), not "no limit". This one setting starved the
  chamber of the whole N2 supply for an hour.
- **Rendered React buttons don't appear in facts**: the alarm's "Vent
  Controls" button is a client-side `setScreen('vents')` — it shows in no
  `actions:` list. Rule: **"not in my facts" ≠ "doesn't exist"** — when a
  human sees UI I can't, read the `.tsx` source.
- **Action lists in facts are truncated**. Re-read with a bigger slice
  before concluding an action is absent.
- **Stale window reuse**: clicking a machine may reuse an already-open tgui
  window (we read an APC window as "the SMES", charge 0). Close stale
  windows first and re-verify `interface:` after EVERY open.
- **`expect_name` must match the real full name** ("power storage unit",
  not "SMES"). Prompt/Pull matching is name-only — isolate by standing so
  only the target is in `oview(1)`, then verify the `Pull obj <id>` line.
- **Toggles are not idempotent.** Read state first, act only if it differs
  (`toggle_machine.py`, `ui_batch set_states`). An interrupted call = state
  unknown = verify before re-acting (a re-click toggles BACK — sent energy
  to 928 mid-excursion).

## 3. Fork truths (this server's control cheatsheet)

Verified against this fork's code / live session — scripts rely on these:

| Input | Effect |
| --- | --- |
| **Ctrl+click** a mob | pull/grab it (`"You grab X passively!"`) — plain clicks only shove/inspect |
| **Drag mob → mob** | opens the StripMenu (not a pull!) |
| **Drag mob → obj** (operating table, stasis unit) | buckle/place it on that thing |
| **Drag worn item → turf** | for bags: dumps their *contents* on the floor (bag stays worn) |
| **Alt+click** a container you hold | opens its storage UI (plain click = use-in-hand, often nothing) |
| **Click item in open storage UI** | item moves into an empty hand (that hand becomes active) |
| **Q** | drop the active hand's item |
| **X** | swap hands |
| Click **HUD slot** with item in active hand | try to equip to that slot ("too big!" when it can't / occupied) |
| Click **HUD slot** with empty hand | take/equip what's in the slot into the empty hand (not always removal) |
| **RMB** on a surgery tray | opens its *specific-tool* storage UI (LMB grabs a random tool) |
| Click a **vending machine** with an *item* in the active hand | "does not accept X!" — open it with an empty active hand |
| `tgui_act {action: "vend", params: {ref, premium?}}` | buys; the item vends into a free hand, else drops on the floor |

Medical truths (from the game code, not the wiki):

- Defib refuses at **brute ≥ 180 or burn ≥ 180** ("Tissue damage too severe") and
  only fails on a heart flagged **Non-Functional** ("Severely Damaged" still shocks).
- Medical stacks (sutures, mesh, bruise packs) **refuse corpses**; **gauze works on
  the dead**. Synthflesh gel (NanoDrug Plus, 350 cr) works on the dead and heals
  75 brute + 75 burn per spray.
- A revived body comes back at **-50 health (deep crit)** with extra suffocation —
  keep treating after the ping.
- Sutures/mesh **auto-repeat** across hurt limbs per click (≈1 s per application,
  10 brute per suture use). Stack heals per use: suture 10 brute, medicated
  suture 15, regen mesh 10 burn (+flesh regen), bruise pack 40 brute, ointment
  5 burn (source: `stacks/medical.dm`).
- **Tox does not decay on its own** (live-verified 20 min at 7); treat with
  multiver/syriniver from NanoDrug Plus (bottle 10 cr w/ MD discount) delivered
  by a vendor syringe. **X-swap frees no hand** — Q-drop to pick floor items up.
  The client **forgets mobs that leave view** (ids too) — re-find by name with
  `search(all_things=True)`; prefer `goto_tile` coords over `goto(object_id)`.
- Syringes (this fork): **LMB = inject, RMB = draw** — no mode toggle. Vendor
  syringes come preloaded (spaceacillin/convermol, 5 cr): purge into self by
  clicking yourself, then RMB-draw the medicine you actually want.

Surgery truths (source-verified + live):

- **Radial menus are answer-only artifacts.** A click that opens one returns
  `menu_opened:` with its choices as `- obj <id> "name"` lines *in that
  answer*; `sk.screen(all=True)` won't list them afterwards. Click the choice
  id immediately, from the same script. Clicking the same target again
  toggles the menu closed ("menu_closed:"). Stale menu ids do nothing.
- **Surgery needs drapes prep, and it expires (~2-3 min)** — silent
  "nothing to do with X!" failures follow. Re-drape per op in a chain. Zone is
  chosen on the damage-zone doll (HUD `damage zone`; head ≈ px 12-20, py 23-30).
- **Chest chain**: drape → incise skin (scalpel) → retract skin (screwdriver
  works, 2.25×) → clamp bleeders (hemostat) → saw bone (circular saw) →
  incise organs (sharp edge, not the saw) → organ ops (bypass = hemostat, 9 s).
- **`tend bruises` loops to brute 0** and blocks all other surgery meanwhile
  — one click fully de-brutes a corpse, but never leaves it running when you
  want a different op from the radial.
- **Organ repairs are one-shot per organ** (trait set on success); success sets
  organ damage to 60% of max and clears the failing flag — that's the defib
  gate. Rot-darkened organs may be unrepairable; then `remove heart` + donor
  implant (morgue trays hold preserved bodies; smart organ storages are empty).
- **"he is dead!" balloon = wrong item in the active hand** (medkit/stack ate
  the click), **"already performing surgery!" = wait it out**. The defib needs
  brute/burn < 180 AND heart AND brain not Non-Functional (head chain for the
  brain).

Supermatter / engine truths (this round, live + source):

- **Ground-truth ranking**: CIMS delta (two reads over time) > click echoes >
  icon states > chat warnings > assumptions. Emitter icons look identical
  on/off; only the CIMS energy delta proves what's running.
- **CIMS lives in the NtOS computer** (SMES room), NOT the PDA — PDAs die
  (battery) and the program dies with them. `PC_runprogram {name: "ntcims"}`
  from next to the console (2 tiles = view-only but reads work, 3-5 disabled).
  Empty active hand required to open it. Scripts: `engineering/cims_console.py`
  (single read), `engineering/cims_watch.py` (two reads + trend).
- **One emitter = stable equilibrium** on pure cold N2: temp ~60-80 K, energy
  ~300-1000 oscillating, integrity 100. Three emitters on a chamber with 14%
  O2 → temp 1622 K, integrity → 74.6%. **Never ignite above 10% O2.**
- **Excursion playbook (worked, 74.6% → 100%)**: integrity falling + O2 > 10%
  + temp > limit → (1) kill ALL beams first (waste scales with energy),
  (2) scrubbers to SIPHON (`scrubbing val: 0`!), (3) feed cold N2, (4) wait —
  Low Temperature Healing kicks in near ~100 K and integrity rises by itself.
- **Pump map (this fork's engine, by NAME)**: External Gas to Loop ×2, Gas to
  Cold Loop + Cold Loop to Gas, **Mix to Gas AND Gas to Mix (both needed —
  the Gas to Mix pump was found OFF once)**, Gas to Chamber + Gas to Filter,
  SW filter, column filters (the N2-only one feeds the chamber), TCUs ×2
  @73.15 K; bypasses + Atmos-to-Loop OFF. Canister port valve: `valve` action
  toggles, `pressure` sets kPa (4500). Chamber air alarm: vents ext-limit
  cleared (`excheck val:1`) + external 101 kPa; scrubbers widenet ON, siphon
  only after CIMS gates (>8 mol, >90% N2).
- **Crystal radio warnings lag** and Poly the parrot fakes delam alarms —
  trust the CIMS, announce via `:e` only on real trends.

## 4. Script conventions

Every script in this repo:

- Starts with a docstring: one-line purpose + a `Run:` example line.
- `opts = args or {}`; every option read via `opts.get("name", default)`; required
  options raise a clear `ValueError` (shows up in the envelope's `error`).
- Truncates every tool `.text` before returning (`[:300]` style).
- Returns a dict with at least `{"ok": bool, ...}` plus the evidence (positions,
  matched chat lines, before/after).
- Prints progress (`print(f"step: ...")`) so `logs` reads like a narration.
- Sleeps in short steps and caps loops.

## 5. Library map

| Folder | Purpose |
| --- | --- |
| `setup/` | Session bootstrap: load the map, snapshot the session state |
| `common/check.py` | **ONE-CALL situational check**: recent chat + your status + what's around you (+ danger words). Run between actions, before new areas, whenever anything surprises you — this is how you notice attacks, delams, floods and instructions BEFORE they cost you. Also parses **`heard`** (everything anyone said on radio or locally: who/verb/text/channel/mine) and **`needs_response`** (someone addressed you, your job, or asked a question — answer on the radio before the next action). |
| `lifecycle/` | Ghost out, respawn (admin override), join the round as a job |
| `movement/` | Walk to areas/tiles, haul a pulled mob somewhere and place it |
| `inventory/` | Hands & containers: drop, open, take, equip to HUD slots, **quick_equip** (E — stores into containers when the slot is occupied, never swaps!), toggle worn-slot display |
| `machines/` | Vendor purchases, surgery-tray tool grabs |
| `medical/` | Analyze, treat, medipen, bed placement, defib revival, radial-menu surgery, heal-to-full flows |
| `engineering/` | Supermatter engine loop setup (omni pumps/filters, freezers, air alarm), SMES, emitters, NT CIMS reads via PDA or the NtOS console (`cims_console.py`/`cims_watch.py` — PDA-independent), state-checked toggles (`toggle_machine.py`, `ui_batch set_states`), canister seating (pull.py/wrench.py), **delam_response.py emergency playbook**. See its index.md for this fork's omni-device truths and tgui polarity traps. |

Each folder has its own `index.md` listing the scripts, their arguments and when
to reach for them.

## 6. Composing flows (example: the medbay revival)

What worked live, as a chain of these scripts / inline snippets:

1. `movement/pull_mob_to.py` — grab the body (Ctrl+click), haul it, drop it on the
   stasis unit or operating table.
2. `medical/inject_medipen.py` — epinephrine medipen stops the heart-rot clock.
3. `medical/analyze_patient.py` — read the damage table; decide the threshold:
   brute ≥ 180 ⇒ synthflesh from the vendor (`machines/vend_buy.py`) before
   anything else.
4. `medical/defib_revive.py` — mount/paddles/wield/shock, verify the ping.
5. `medical/treat_patient.py` — gauze the bleeding limb, chain sutures across
   limbs, mesh if needed, re-analyze until ≥ target %.

Notes for the flow: the Grand Surgery Theatre can be **dark** (broken light tube)
— the health analyzer reads `"It's too dark in here to read!"`; treat in a lit
room instead of fighting the fixture. After a defib the paddles snap back into
the mount by themselves; the patient may be pulled one more time or walk on their
own once conscious.

### Corpse revival (surgery route, when gel/defib gates fail)

1. Drape (`surgery.py {op: any, tool: "surgical drapes", drape: true}`) — redo
   per op, the prep expires in minutes.
2. `tend bruises` with the hemostat **once and let it loop** — it grinds brute
   to 0 by itself and unblocks the defib tissue gate.
3. Chest chain via `surgery.py`: incise → retract (screwdriver) → clamp → saw
   → incise organs → `graft coronary bypass` (one-shot; makes the heart
   defib-able).
4. If the heart is rot-darkened and bypass is absent from the radial:
   `remove heart`, then a donor heart from a morgue-tray body + implant.
5. Head chain (zone = head on the doll) for the brain repair — the defib
   refuses a Non-Functional brain too.
6. `defib_revive.py`, then `treat_patient.py` — they wake at -50 health.
7. Post-revival cleanup: `mend skin incision` (cautery) per opened zone.

## 7. Adding a new script — checklist

- [ ] Generic? Could a future round reuse it with different args?
- [ ] Docstring with a `Run:` example using the real arg names?
- [ ] Every world-changing step verified (search / inventory / chat)?
- [ ] Truncated texts, JSON-safe return, `"ok"` field?
- [ ] Loops capped; sleeps short; no infinite waits?
- [ ] Fork truths it depends on documented in its index.md?
- [ ] Added to its folder's `index.md` (name, args, purpose, gotchas)?
