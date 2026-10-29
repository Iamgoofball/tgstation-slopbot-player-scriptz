# lifecycle/

Round re-entry: ghost out, respawn (admin override), join as a job. Each is one
`run_script` call, one compact dict back.

| Script | Args | Purpose |
| --- | --- | --- |
| `ghost_out.py` | — | Verb `Ghost` + confirm the AlertModal. Returns whether the prompt appeared and was confirmed. |
| `respawn.py` | `choice` (default `"Yes"`) | Verb `Respawn`; answers the override prompt (server has respawn disabled; localhost admin gets asked). |
| `join_as_job.py` | `job` (required, e.g. `"Medical Doctor"`) | `lobby join` -> `select_job`. Late-joiners spawn **buckled into an Arrival Shuttle seat** — follow with `movement/unbuckle_and_exit_shuttle.py`. |

Gotchas
- The job name must match the menu's exact key (`Medical Doctor`, not `MD`).
- After ghosting, your old body stays where it stood; the client may later
  *forget* it if it leaves view (re-search before acting on its ID).
- Respawn override says "Respawning is currently disabled..." — `Yes` is the
  admin-sanctioned answer here (operator's test server).
