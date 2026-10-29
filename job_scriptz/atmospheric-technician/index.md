# job_scriptz/atmospheric-technician/

The atmos tech's routines. Consoles: all three sit in **Atmospherics Gas
Storage** — atmos monitoring @155,127, station alert @155,126, atmospheric
alert @161,126 (ids change every round; the shift check auto-surveys them
in view).

| Script | Args | Purpose |
| --- | --- | --- |
| `atmos_shift_check.py` | `monitoring?`, `station_alert?`, `atmos_alert?`, `x?`, `y?` (optional ids; auto-survey otherwise) | ONE envelope over the three consoles: distro/waste gasmix (pressure, temp, %O2 via per-chamber slice), StationAlertConsole `alarms[]` (Atmosphere/Fire/Power), AtmosAlertConsole `priority[]`/`minor[]`. Verdicts: distro 101±10 kPa + 19–23 %O2, waste <5 kPa, alarm zones listed. |
| `air_alarm_mode.py` | `alarm`, `mode?`, `vent_pressure?`, `vent_power?`, `scrub_power?`, `panic?`, `lock_after?` | State-checked air alarm control. Modes (prefix `/datum/air_alarm_mode/`): filtering, contaminated, draught, refill, cycle, siphon, panic_siphon, off, flood, vent_siphon. Verified: vent_pressure 202 set + restored to 101.325 via filtering mode. |
| `loop_pumps_audit.py` | `fix?`, `distro_pressure?`=101 | Walks Pumping Room + mixer spots, reads every pump/mixer tgui, verdicts vs spec: Air to Distro ON@101, Waste to Filter ON, Distro to Waste OFF, Distro Staging to Distro OFF, omni air mixer ON 79/21@4500. Airmix pumps report-only. `fix: true` corrects deviations (verified: power OFF→ON round-trip). |

Fork truths learned here:

- **AirAlarm (air alarm tgui)**: `locked` in the DATA block (not
  config.window.locked). Vents/scrubbers lists only appear when UNLOCKED —
  unlock = RMB-click the alarm with the ID WORN (same as APC). Actions:
  `mode {mode: full path string}`, `power/direction/excheck/scrubbing/
  widenet/set_external_pressure {ref, ...}` where ref = the `refID` string
  (`[0x...]`) from `data.vents[]`/`data.scrubbers[]`. Current mode:
  `data.selectedModePath`. Vent JSON field order: power BEFORE external.
- **HAZARD — `reset_external_pressure` UNBINDS the vent**: external → 5066
  (max flow), the room overpressurizes (saw 113→114 kPa while testing). To
  restore the bound default, re-apply a MODE (filtering sets 101.325 +
  extdefault 1) or `set_external_pressure {ref, value: 101.325}`.
- **Mode change re-applies the mode's vent bounds**: draught sets vent 202,
  filtering resets to 101.325 + restores scrubbing. The mode apply is the
  cleanest "reset this room" action.
- **AtmosControlConsole** (station atmospherics monitoring): chambers
  distro/waste, actions `adjust_input/adjust_output/toggle_input/
  toggle_output {chamber, rate?}`. In the gasmix JSON **temperature comes
  BEFORE pressure** — parse per-chamber slices, not global regexes (a global
  pressure regex grabs the OTHER chamber's value).
- **StationAlertConsole**: `data.alarms[]` = category blocks (Atmosphere,
  Fire, Power) each with `alerts[]` zones. **AtmosAlertConsole**: only action
  `clear {zone}`; `data.priority[]`/`data.minor[]`.
- **AtmosPump** window: `{on, pressure, max_pressure}`, actions `power`,
  `pressure {pressure}`, `rate {rate}`. **AtmosMixer**: `{on, set_pressure,
  max_pressure, node1_concentration, node2_concentration}` (FLAT keys, not
  nested), actions `node1/node2 {concentration}`, `power`, `pressure`.
- **Unpowered-area signature**: dark corridor tiles + airlock doors that
  stay dense + machine clicks that open NO window = the area's APC is dead.
  Saw it in main Atmospherics (mixer went silent while Pumping Room kept
  working — different areas, different APCs). Fix = power (quickpower
  recharges APC cells station-wide), not more clicking.
- **Pipe-access corridors** (row of "Inner Pipe Access" doors along y=111)
  are unlit/unpowered side rooms: the airmix pumps (O2 167,110 / N2 163,110)
  live behind them and stay unreachable when the area is unpowered. Not in
  the audit spec — the mixer at 79/21 feeding distro is the health check.
- The mixer window may open under a NEW window id when a stale/admin window
  holds tgui-window-1 — `loop_pumps_audit` scans ALL ids and verifies the
  window `title:` matches the machine name before parsing (the stale-window
  swallow bit the mixer and both airmix reads with Waste to Filter's data).
- quickpower (Secrets panel) leaves its admin window around — close ALL
  windows before any machine interaction.
