# setup/

Session bootstrap. Run these after connecting and after every MCP reboot.

| Script | Args | Purpose |
| --- | --- | --- |
| `load_map.py` | `map_path` (optional; defaults to the MetaStation dmm on F:) | Load the station map so `bot.goto` can path over unseen tiles. **Required after each MCP reboot** — long walks fail with "no known path" otherwise. |
| `session_report.py` | — | Tiny snapshot: position, active-hand item, combat/pull HUD state, open windows. Cheap first call to re-orient. |

Return sizes: `load_map` ≤ ~150 chars, `session_report` ≤ ~350 chars.

Gotchas
- The map must be the same file the live server runs (F: copy for MetaStation).
- `session_report` reads HUD button states (`state=combat_off`, `state=pull0`),
  which is the cheap way to check combat mode / pull instead of experimenting.
