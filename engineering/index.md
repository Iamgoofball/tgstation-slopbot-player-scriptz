# engineering/

Supermatter engine + power grid helpers. All are generic: pass machine **names
or ids** as args, never hard-code. Fork truths baked into each script are
listed here too.

**NtOS consoles remember their last program**: a program window
(NtPowerMonitor, NtosSupermatter…) has NO `programs` list in its data — send
`PC_exit` up to 3× to get back to NtosMain before running any program.
`cims_console` / `power_monitor_report` assume a fresh NtosMain on click;
`job_scriptz/station-engineer/shift_start_report.py` handles the leftover case.

| Script | Args | Purpose |
| --- | --- | --- |
| `pump_set.py` | `name`, `on?`, `max?` | Ctrl-click (on/off) + alt-click (4500 kPa) one pump/valve/bypass/filter by name, in view. |
| `freezer_set.py` | `id` or `name`, `target?` | Temperature control unit → `power` + `target` via tgui (engine: 73.15 K). **Never alt-click a freezer** — first alt-click = 573 K heating. |
| `smes_set.py` | `id`, `input_w?`, `output_w?` | Smes window: input 200 kW (max), output 190 kW; verifies `inputAttempt/outputAttempt`. |
| `smes_read.py` | `id` | Read-ONLY Smes window: charge %, input/output attempt flags, `inputAvailable`/`outputUsed`. Closes stale non-Smes windows first (the stale-APC-as-SMES trap). Pair with `smes_set.py` for writes. |
| `power_monitor_report.py` | `computer`, `x?`,`y?`, `limit?`=12 | Read-only AmpCheck (`PC_runprogram {name:"ampcheck"}`) on the Power Monitoring NtOS console: supply/demand strings + the per-area table read via **`tgui_window path:"data.areas"`** (149 entries `{name, charge, load, charging, eqp, lgt, env}`; the state block only says "list of 149"). Returns the N lowest-charge areas — the "who is about to go dark" overview. Close EVERY window first: a stale Smes window at tgui-window-1 swallows the click; stand adjacent (x,y). |
| `apc_channel.py` | `apc`, `set`=`{"eqp"\|"lgt"\|"env": 1\|2\|3}`, `breaker?`, `charge?`, `nightshift?` | State-checked APC control, verified both directions. **Unlock = RIGHT-click the APC with the ID in a hand** (any hand; maptext hints "[RMB] Toggle interface lock"); LMB with the ID in the ACTIVE hand is also a swipe (toggles — don't chain them), so swap (X) to make the active hand empty before the opening LMB click. Channels live in `data.powerChannels[]` (`title` Equipment/Lighting/Environment → `eqp/lgt/env`, `status` 1 off / 2 on / 3 auto); action `channel {key: n}`; parse only inside the `"data": {` block — `config.window.locked` (always 0) would false-match. Retries once after a re-swipe when an act doesn't take. Also `breaker` (`isOperating`), `charge`, `nightshift`. |
| `cims_read.py` | — | NT CIMS from the PDA (no need to hold it): integrity, energy (GeV), gas temp vs temp_limit, moles, gas %, zap MW. Healthy: 100 / 1.3-1.6 GeV / 70-85 K / ~14 mol / ~97% N2. **PDA-dependent — the battery dies and takes the program with it; prefer cims_console.py.** |
| `cims_console.py` | `computer`, `x?`,`y?` | CIMS via the SMES-room **NtOS engineering console** (`PC_runprogram {name:"ntcims"}`) — PDA-independent. Must stand NEXT to the console (2 tiles = view-only, reads still work; 3-5 disabled). `computer` is REQUIRED (ids change every round — survey_machines.py finds it). Empty active hand! |
| `cims_watch.py` | `computer?`, `gap_s?`=20 | TWO CIMS reads + delta → `trend`: healing / stable / **destabilizing** (act!). A single read can't tell healing from falling — deltas are ground truth. |
| `toggle_machine.py` | `id`, `goal`, `kind`=`emitter`\|`tgui_field` | **State-checked toggle** (toggles are NOT idempotent — both our near-delams came from blind re-clicks): tgui_field reads the field, acts only if it differs, verifies. `kind:"emitter"` uses the click echo ("You turn on/off the emitter") — follow with `emitters_on verify` or `cims_watch`. |
| `emitters_on.py` | `ids`, `off?`, `verify?: {computer}` | Click each emitter from beside/behind (never in front: 30 burn/hit), examine-verify per emitter. `verify` adds a CIMS energy delta check (ON→rising, OFF→falling) — **never trust clicks/icons: emitter icons look identical on/off.** |
| `air_alarm_setup.py` | `id`, `stage`, `ext_pressure`=101, `siphon?` | `vents`: external limit CHECK off (**XOR quirk: excheck val=1 clears, val=0 is a no-op**) + external target `ext_pressure` (NEVER 0 with the check on — the vent then never pumps). `scrubbers`: widenet; with `siphon: true` sets **siphon = `scrubbing val:0`** (val:1 is scrub-mode!) — siphon only when CIMS reads >8 mol and >90% N2, else you vacuum the chamber. |
| `ui_batch.py` | `ids`, `actions?`, `set_states?` | Open many machines' tgui in one envelope; read `data` (filter_types compressed); per-id `actions` (blind!) or **`set_states`** (state-checked: `{field, goal, action}` — acts only if the field differs from goal, re-reads to verify). Empty active hand! |
| `machine_ui.py` | `id`, `actions?` | Single machine: walk adjacent, open, parse, act. |
| `survey_machines.py` | `spots`, `only?` | Walk spots, page in-view search, return filtered machinery list. |
| `pull.py` | `id`, `release?`, `walk?` | Pull a thing (this fork: Pull is the shift-right-click context verb; script runs `Pull` + answers the target prompt — auto-walks adjacent). Pulled things trail on your previous tile; `sk.move(direction, steps)` pushes them ahead when you bump them. HUD "stop pulling" releases. |
| `wrench.py` | `id`, `belt?` | Wrench a thing with the toolbelt wrench (opens belt, takes wrench, clicks target, stows). Wrench toggles fasten/unfasten — check the new_chat line. |
| `delam_response.py` | `emitters`, `alarm`, `canisters` | **EMERGENCY, one envelope**: emitters off → air alarm panic siphon + widenet scrubbers → open N2 canister valves → trend check. ABORTS + "RUN NOW" on countdown chat. Then flee (`sk.move` 10+ tiles) and re-run `cims_read.py`. (Guide: the 30 s window from 0% can still heal the crystal — but once the 15 s broadcast plays, just RUN.) |
| `canister_port_seat.md` note | — | Seating recipe that works here: pull the canister, walk so it **trails onto the target port tile** (it lands on your previous tile each step — approach the port from the far side), or bump-push it with `sk.move(direction, 1..2)`. Then wrench (`wrench.py`). Wrench toggles fasten/unfasten — trust the new_chat line, not assumptions. |

Port layout (verified one round — POSITIONS are stable on this fork, ids are not):
- **Intake ports (white)**: a two-tile strip on the engine-room wall's
  southeast side — **N2 goes here**. Wrench canisters there, verify
  `portConnected: 1`, valves CLOSED until feeding time.
- **Output ports (red)** further north along the same wall: the OUTPUT side —
  never connect N2 there; park empty spares well away from both strips.
- Between the red ports and the intake strip is solid wall; reach the intake
  strip from its own side. Push canisters along the strip row, or trail them
  by walking.

Setup order (this fork's SM engine — "omni" devices, tgui-driven; device NAMES
are stable, ids are not — survey each shift):
0. **Pre-flight**: CIMS baseline (integrity 100, energy 0), APC has power
   (externalPower > 0 or cell charged), chamber at ~101 kPa / 293 K. If the
   chamber shows O2 > 5% or pressure > 200 kPa BEFORE the engine runs, purge
   first. THEN:
1. Wrench both Nitrogen canisters to the WHITE intake ports (valves CLOSED —
   verified `portConnected: 1`). The RED ports are the output side —
   leave the empty canisters off them.
2. Engine Coolant Bypass OFF (AtmosPump tgui); SW omni gas filter ON (no
   gases); Gas to Cold Loop + Cold Loop to Gas ON @ 4500; column omni filters
   (two with no gases + one N2-only); freezer ON @ 73.15 K; Cooling Loop
   Bypass + Atmos to Loop stay OFF. All via `ui_batch.py actions`.
3. Chamber air alarm: vents external-limit OFF (excheck val=1); scrubbers
   widenet + **siphon (`scrubbing val:0`) only after CIMS gates**.
4. CIMS baseline (`cims_console.py` via the SMES-room NtOS console — or
   PDA if its battery lives), SMES 200/190, emitters (3 on this fork; one is
   enough) from behind, shutters, lock emitters + reflectors.
   (Guide variants of the same steps: see "Guide's setup order" below.)

Killer gotchas:
- **SAFETY WATCHDOG between EVERY step** (README section 1): read chat + status
  between actions; abort and change plan on danger. The agent re-reads chat
  between run_script envelopes too. **Before turning any engine power on
  (emitters), check the APC has power and the CIMS is at baseline** — turning
  emitters on an O2-flooded chamber started a delam that cost us our character.
- **Delam signatures** (from the one that killed us): integrity <95% and
  FALLING + chamber O2 >10% + moles climbing + temp ≫ temp_limit. React
  instantly: `delam_response.py`, then flee. The countdown is 15 s; the blast
  with O2 is ~37 tiles. Don't try to outrun it from inside the engine room —
  the walls channel you into dead ends (163,151 blocks, 164,147 wall).
- Scrubbers CANNOT out-pump a flood (chamber hit 6000 kPa / 7700 K with 3
  siphoning scrubbers on widenet). Cut the SOURCE (vents off, valves closed,
  emitters off) before expecting the siphon to save integrity.
- **Never step past the outer "Supermatter Chamber" doorway**; never open the
  inner door (chamber is sub-pressure after scrubbers start: it pulls you in).
- **Free the active hand before ANY world click** — a held PDA/wrench gets
  "used" on the target instead (silent: the click still "succeeds"). Store the
  PDA in the backpack at round start; press X to swap hands if something is
  held. Verify `active_hand: ... empty` in inventory before acting.
- The crystal: touch = dust, pull ≥1-3 tiles by energy, radiation in 8 tiles
  (suit + hood both, or MODsuit), hallucinations within ~7 tiles (mesons do
  NOT stop them — trust CIMS, not what you see/hear; Poly repeats fake alarms).
- Bullets damage the crystal, lasers don't. Emitters settle ~1.3-1.6 GeV on N2.
- Integrity <95% warns on :e, <25% on common, 0% = 15 s countdown then blast
  (small on N2, ~37 tiles heavy damage if O2/plasma-rich).

## Excursion case study (round "Anthropic Station XIII", recovered 74.6% → 100%)

What happened, in order — every step is a lesson:
1. Ignited with **3 emitters while the chamber still read 14% O2** (>10% = delam
   risk; also SMES read "charge 0" from a **stale APC window** — the bank was
   actually full; always re-verify `interface:`).
2. Set scrubbers to "siphoning" that was actually **scrub-mode** (`scrubbing
   val:1` = scrub; **siphon = val:0** — Parabellum yelled this correction on :e).
   O2 climbed unchecked → integrity 100 → 74.6, temp 1622 K.
3. **Blind re-click** on the last emitter during the kill turned it back ON
   (interrupted earlier click = unknown state). Energy jumped 413 → 928.
4. Recovery that worked: kill ALL beams → siphon (val:0) + widenet → feed cold
   N2 → **Low Temperature Healing near ~100 K restored 100% integrity**. Moles
   97 → 6.6 purge, then refill; O2 → 0.

Rules now encoded: `cims_watch.py` trend before/after ANY emitter or alarm
change; `toggle_machine.py`/`ui_batch set_states` instead of blind toggles;
siphon polarity in `air_alarm_setup.py`; **one emitter is a complete, stable
engine** (temp ~60-80 K, energy ~300-1000 oscillating, integrity 100, SMES
input ~192 kW available). Machine **ids change every round** — the ids in the
setup order below are examples, re-survey each shift.

## Guide mechanics (integrated from `supermatter_setup_guide.txt`, tg wiki)

### Integrity & damage
- Damage factors: **heating** (absorbed gas above the temp limit), **charge**
  (internal energy > **5000 MeV**), **molar** (> **1800 moles** absorbed),
  **external** (bullets, destabilizing crystals), **space exposure** (crystal on
  or near space while powered).
- Default temp limit **626.3 K**; base heat resistance 313.15 K, raised by gas
  heat resistance (N2O +500%, proto-nitrate +400%), a psy coefficient
  (psychologist / HYPERG1G4 chip / Psychosyphoning diode disk, up to +45 K),
  and low moles (up to +100%).
- The real number to fear: **plasma + O2 combust at 373.15 K** — combustion is
  exothermic and drags the chamber past 626 K. Keep waste O2/plasma out, not
  just temp under the limit.
- **At 0% integrity a 30 s final countdown starts. The crystal can still be
  healed within it** (it keeps taking damage, integrity can go negative off-UI,
  and it must heal above 0 to cancel). Our round broadcast "15 seconds" on
  common at the final stage — treat 30 s as the ceiling, 15 s as what you'll
  actually hear. Once you hear the countdown, RUN — don't try to heal under
  15 s unless you're already at the alarm console.
- At 0% the delam is one of four (later takes priority):
  1. **Explosive** (default) — explosion sized by gas heat power; irradiates,
     hallucinates, anomalies.
  2. **Tesla** — internal energy > **5000 MeV** at delam: explosion + energy
     ball.
  3. **Singularity** — absorbed > **1800 moles** at delam: spawns a singulo.
  4. **Resonance cascade** — **40% hyper-nob + 40% anti-nob with ≥270 moles**
     (or a destabilizing crystal): crystal mass station-wide, shuttle disabled,
     CentCom rift. Main engine only, never shards.
- Below 40% integrity (or >5000 MeV) the crystal rapidly spawns **flux and
  gravitational anomalies** — grav anomalies drag/throw you. At low integrity,
  enter with an engineering MODsuit; otherwise radsuit + insuls + magboots.

### Gas interactions (100% composition numbers, from the guide table)
| Gas | Safety | Key effects (power transmission / waste multiplier / heat power gain) |
| --- | --- | --- |
| Hyper-Nob | Extremely safe | Stops reactions ≥5 mol & >20 K; waste −1400%; transmission +30%; cascade ingredient |
| Helium | Very safe | Inert, nothing |
| Freon | Very safe | Stops power emission >30%; waste −900%, transmission −300%; makes hot ice with O2; cool via H/E, not into the SM |
| Proto-Nitrate | Very safe | Transmission +150%, waste −400%, **heat resistance +400%** |
| **N2** | Very safe | Waste −250%, heat power gain −100%; the standard engine gas |
| Pluoxium | Safe | Negates CO2's bonuses; transmission −50%; remove it |
| N2O | Safe | **Heat resistance +500%**; decays to O2+N2 when hot (tritium-fire risk); slows a delam if not past the tipping point |
| O2 | Relatively dangerous | Transmission +15%, heat power gain +100%; combusts with waste plasma at 373 K |
| Miasma / Healium | Relatively dangerous | Small power boosts, waste/heath penalties (healium waste +300%) |
| Halon | Dangerous | Makes CO2, eats O2 — turns heat delams into charge delams; just don't |
| CO2 | Dangerous | Heat power +100%, **power decay negation +100%**; high amounts → charge delam (tesla); rewarding but needs prep |
| Zauker / BZ | Dangerous | Big transmission but heavy waste; BZ >40% shoots lethal particles |
| Water vapor | Very dangerous | Waste +1100%; accumulates from fires; keep out |
| Plasma | Very dangerous | Transmission +40%, **waste +1400%**; roundstart setup cannot run pure plasma |
| Tritium / H2 | Very dangerous | Transmission +300%/+250%, waste +900%; jumpy, fire-prone |
| Anti-Nob | Extremely dangerous | Worst specific heat; cascade ingredient; never a coolant |

### Diode disks (research-printable, loaded into emitters — open the maint panel; swap with crowbar)
- **Psychosyphoning**: psy coeff +25%, energy −25 MeV — efficient setups keep this in.
- **Electrodisruptive**: integrity +0.25%, energy −60 MeV per hit — the safety disk.
- **Conflagratory**: integrity −0.15%, energy +150 MeV — combo with Electrodisruptive for energy gain.
- **Magnetogenerative**: molar absorption +5% (stacks, decays fast) — lowers cascade threshold.
- **Hyperconcussive** (traitor): integrity −2%, +500 MeV, explosions. Bioregenerative: useless for engineering.

### Guide's setup order (color-coded MetaStation) vs this fork
Guide steps, mapped to our omni-fork order (numbers in the setup order above):
1. Gear: **mesons (or engi goggles in meson mode) + full radiation suit AND hood**; NT CIMS on the tablet — before anything else.
2. Bypass pump OFF (green) → our Engine Coolant Bypass.
3. Wrench N2 canisters, main loop pump ON + max (red) → our step 1 + Gas to Cold Loop / Cold Loop to Gas.
4. Chamber in/out pumps ON + max (orange).
5. SW filter ON, max, **filter nothing** (blue) → our SW omni gas filter.
6. Cold-loop pumps max (violet) → our Gas to Cold Loop / Cold Loop to Gas.
7. White filters all ON + max; the double-circle one set to **N2**, others to **nothing** → our three column filters. (All must be ON even when set to nothing — that's how bad gas gets vented.)
8. Freezer pumps ON + max (brown) and freezers ON + **minimize temp** (pink) → our freezer @ 73.15 K.
9. Air alarm vents: **disable the external limit** (internals green, externals blue), keep vents on Pressurize → our vents stage.
10. Air alarm scrubbers: **siphon + expanded range** → our scrubbers stage (guide does it immediately; our fork gates on CIMS >8 mol / >90% N2).
11. Verify via CIMS: temp dropping, composition → pure N2, **moles above 8**.
12. Start: double-check the loop first; click each emitter with an EMPTY hand, never standing in front; close radiation shutters.
13. SMES: **input 200 kW, output 190 kW** (the 10 kW delta keeps the cells topped as backup) — we previously set output 200k; use 190k per the guide.

If emitters don't fire once on: check cable/SMES connection → maximize SMES → run a **P.A.C.M.A.N.** generator for kickstart power (off once the engine feeds) → or toss a **1-credit holochip** (alt-click your ID) / `*kiss` the crystal **through the glass** — items hitting the crystal add trickle energy.

### Delam mitigation checklist (guide's "common causes", in fix order)
1. **Emitters OFF first** — waste scales with energy (our `delam_response.py` step 1).
2. Pumps offline / left at 101 kPa default → ON + max.
3. Filters offline or no filter returning coolant → white filters ON, N2 filter set.
4. Chamber vents misconfigured (external limit back on) → re-disable.
5. Scrubbers not siphoning → siphon + widenet.
6. Heat exchangers broken (space dust, traitor) → inspect the loop.
7. **Too much gas** (pumps can't push into high pressure — exactly our 6000 kPa death) → cut the feed source, then siphon.
8. **Too little N2** → waste O2/plasma dominates composition, waste multiplier spikes → add N2 canisters or the Atmos-to-engine pipe.
Also: a psy coefficient source (psychologist, HYPERG1G4 chip, Psychosyphoning disk) buys heat resistance and decay negation for free.
