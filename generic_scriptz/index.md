# generic_scriptz/

Generic SS13 interactions not tied to one job: power checks, consoles any
crew member may use, everyday machine habits. All parameterized by args;
job scripts in `job_scriptz/` compose these instead of rewriting them.

| Script | Args | Purpose |
| --- | --- | --- |
| `apc_read.py` | — | Find the nearest APC in view, walk adjacent, open its tgui and parse the **JSON state** (`powerCellStatus`, `externalPower`, `chargingStatus`, `totalLoad`). Verdict: `fine` (external on) / `low` (cell<40) / `dying` (no external). No APC in view → `ok:false`. The cheap between-jobs power check; verdict low/dying → `admin_scriptz/quickpower.py force:true`. |

Notes:
- Conventions proven tonight (apply everywhere):
  - `bot.goto` / `bot.open_machine` take `object_id` as an **int** — search
    text ids are strings; coerce. tgui window ids are strings (`tgui-window-N`).
  - `bot.goto` sets `failed: true` for "already there: no step taken" — treat
    that text as success before aborting.
  - Parse machine state from the tgui window's embedded JSON (`"key": value`
    in `sk.tgui_window` text), never the rendered paraphrase. When a key name
    could appear in `config` too (e.g. `locked`), slice the `"data": {` block
    first — `config.window.locked` false-matches.
  - `run_script {code: ...}` mangles backslash-escapes — anything regex-heavy
    goes in a script FILE, never inline code.
  - A probe script's `result` is the last **bare expression** — a trailing
    `RESULT = x` assignment yields null; end with `{"result": RESULT}`.
- **Finding rooms/machines without walking blind** (the two-step recipe):
  1. `sk.search({query, area: "<area name>"})` WITHOUT `in_view` sweeps
     everything the client remembers — includes things out of view ("last
     seen here Ns ago"). Area name must match the client's known areas.
  2. Never-seen rooms: admin verb `Jump To Area` (ListInputWindow,
     267 server-side areas — full list via `tgui_window path:"static_data.items"`,
     submit by unique substring). Then `search`/`survey_machines` in view.
  - `sk.explore({area})` lists reachable openings from the seen-map edge —
    side-room doors show as `openings:`/`doors:`.
  - **Open-a-machine robustly** (bit us 3× tonight): close ALL windows, click,
    then scan EVERY `tgui-window-N` id for a window whose `title:` matches the
    machine name — the target may open under a NEW id (a stale window or an
    admin panel from quickpower can hold tgui-window-1), and a stale window
    otherwise passes the OLD machine's data off as this one's (bit the mixer
    and both airmix reads with Waste to Filter's data). Verify title, else
    retry once. tgui_act on the found wid, not on tgui-window-1.
  - **Unpowered-area signature**: dark tiles + airlock doors staying dense +
    machine clicks opening NO window = the area's APC is dead (areas have
    their own APCs — the mixer in main Atmospherics went silent while the
    Pumping Room kept working). Fix = power (quickpower), not more clicking.
  - The game reuses ids of deleted things — an object id from an old search
    can route to a different machine later; re-search or expect_name-guard.
  - **Act-answer data_changes lines are UNQUOTED and TRUNCATE mid-key**:
    `- beaker.currentVolume: 0 -> 30` (no quotes around keys) and
    `... "currentV... -> null` (values cut with `...`, no closing brace).
    Parse `key: X -> Y` without quotes; never expect well-formed JSON in an
    act answer. Window state JSON (sk.tgui_window) IS quoted — different
    format, different parsers.
  - **Large window sections need `path:` reads**: tgui static_data lists too
    big for the normal dump (e.g. ChemMaster's `static_data.categories`,
    5229 chars) appear in the normal text only as a pointer — read them with
    `sk.tgui_window(id, path="static_data.categories")` (returns
    `items: N / value: |` + JSON).
  - **A machine click's `help:` line diagnoses area power**: "the room's APC
    (obj N "X APC") shows its equipment power off, and it is not charging:
    machines in <area> have no power" — a silent machine with a powered-looking
    room is answered by the click itself; don't re-click, recharge.
- Consoles shared by several jobs (records, comms, PDA apps) get written once
  here and referenced by the job indexes.
