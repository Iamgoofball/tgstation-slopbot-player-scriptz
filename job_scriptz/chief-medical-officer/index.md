# job_scriptz/chief-medical-officer/

The CMO's routines. Consoles: crew monitoring console in **Paramedic
Dispatch** (85,107 this round; Bridge has another) — medbay central is at
~89,111.

| Script | Args | Purpose |
| --- | --- | --- |
| `crew_monitor.py` | `console?`, `x?`, `y?`, `min_damage?`=20 | ONE-envelope triage from the CrewConsole: parses `data.sensors[]` and classifies DEAD (`life_status` 3), CRITICAL (life_status 1-2 or health < 0), WOUNDED (any damage ≥ min), BROKEN sensors (health -50 garbage, code crew.dm:249), binary-only (no damage fields = suit sensors not on vitals → announce). Verdict per casualty + counts. |
| `sensor_announce.py` | `channel?`=common, `extra?` | The CMO bare-minimum #1: suit-sensors reminder on the radio (`sk.say(text, channel="radio", radio=...)` → `;` prefix). |
| `cryo_check.py` | `cells?`, `start?`, `x?`, `y?` | Bare-minimum #2: every cryo cell in view — on/open/temp/occupant/beaker. `start: true` closes the pod (`door`) then flips `power`. Verdicts: OFF, no beaker, WARM (>150 K = pipe gas gone), OCCUPIED, "refuses to run: connector has no cryogenic gas". |

Fork truths learned here:

- **CrewConsole**: `data.sensors[]` entries = `{ref [mob_N], name, ijob,
  assignment, life_status, oxydam/toxdam/burndam/brutedam, health, area}`.
  `life_status` = mob.stat: 0 conscious, 1-2 unconscious/crit, 3 DEAD.
  Damage fields only with vitals sensors; `area` only with tracking. Broken
  sensors produce RANDOM garbage with health -50 (never treat that as real).
  Old/deleted bodies keep a sensor entry (my previous-round body showed as a
  second "me" — life_status 0 forever).
- **The console click needs an EMPTY ACTIVE hand** — the CMO spawns holding a
  surgical medkit; a hand-item click "uses" it on the console and opens
  NOTHING (cost me 2 debug cycles). Swap X first.
- **Cryo cannot be started without coolant gas**: `power` flips
  isOperating 0→1, then the machine self-shuts ("Cryogenics report:
  Insufficient cryogenic gas, shutting down. Auto ejecting") and reopens the
  pod. The AAS line repeats every attempt. Setup order: fill the connector
  gas from the atmos loop FIRST, then beaker (cryoxadone), then power.
- **Cryo power button is DISABLED while the pod door is open** — send `door`
  (closes) before `power`. Verify acts by their `data_changes` answers, not
  by an immediate re-read (races the server).
- **Cryogenics area APC**: cell 100% + externalPower 2 + breaker on =
  powered, but the ROOM can still be dark (`light-nopower` light switch was
  a cached pre-quickpower state — re-check live before diagnosing).
- Getting into Cryogenics on foot: the door "Paramedic Dispatch Room"
  (84,109 area) is the only known path; it stays dense when the area is
  unpowered. Admin: `Jump To Coordinate` (81,110,2) lands inside.
