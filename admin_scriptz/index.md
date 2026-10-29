# admin_scriptz/

Admin-panel helpers (Secrets panel, panels and powers). These bypass normal
crew rules — dev-server / admin duty only, and the noisy ones announce
themselves to the station. Crew-facing scripts live elsewhere.

| Script | Args | Purpose |
| --- | --- | --- |
| `quickpower.py` | `force?` | Recharge every SMES station-wide via Secrets → `quickpower`. Announces a CC "Power Systems Nominal" update to everyone — guard with `force: true` and only run when power is really low (the operator's standing order: restore power whenever it runs low). Opens the Secrets panel itself if not already open. |

Notes:
- Secrets panel actions of note (read from a live panel): `power`,
  `quickpower` (recharge), `unpower` (kill station power — testing only),
  `blackout`/`whiteout` (lights), `fix_gravity`, `mass_heal`, `cascade`,
  `fix_gravity`, `maint_access_brig`, `maint_access_engiebrig`.
- Power-check habit between jobs: `generic_scriptz/apc_read.py` — verdict
  "low"/"dying" → run this script with `force: true`.
