# job_scriptz/station-engineer/

The Station Engineer's own routines. The deep engine/power tools live in
`engineering/` (cims, delam, emitters, SMES, APC, air alarms) — these are the
job-level compositions on top of them.

| Script | Args | Purpose |
| --- | --- | --- |
| `shift_start_report.py` | `smes_ids?`, `computer?`, `x?`, `y?` (all optional — auto-surveys in view) | ONE envelope: every SMES in view (charge %, output), AmpCheck via the NtOS console (supply/demand + 5 lowest areas of 149), NT CIMS (integrity/energy/temp), then verdict lines (`engine COLD/RUNNING` keyed on CIMS energy, `crystal healthy/DAMAGED`, `SMES LOW`, `areas draining`). Stand in/near the SMES room (Power Monitoring door at ~155,149, units 152–154,148). |

Gotchas learned here:
- The NtOS console remembers its last program: a program window (e.g.
  NtosSupermatter) has NO programs list — send `PC_exit` up to 3× to get back
  to NtosMain before running ampcheck/ntcims.
- CIMS energy 0 + temp 293 K = engine never started (this round's baseline);
  AmpCheck `supply` is the grid feed (SMES output), NOT the engine — engine
  state = CIMS energy.
- quickpower (Secrets) recharges SMES **and** every APC cell station-wide
  (28%→100% within a minute). SMES drain ~2%/min at 200 kW output each with
  the engine cold — measured tonight: ~20 min from full to EMPTY (one SMES
  hit 0% and its areas died: dark rooms, dense doors, silent machines).
  Re-run quickpower at least every ~15 min, or whenever shift_start_report
  shows SMES under ~40%.
- **After an MCP reconnect the client forgets everything** (map, ids, mob
  memory): `setup/load_map.py`, then walk/search to re-discover ids. Admin
  fast-travel: verb `Jump To Coordinate` = 3× NumberInputModal submits
  (cx, cy, cz) in RAW tool coordinates (tool x/y exactly as look/status
  reports them, z 2 = station) — verified landing tile-exact.
