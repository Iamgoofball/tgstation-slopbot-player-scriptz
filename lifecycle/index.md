# lifecycle/

Round re-entry: ghost out, respawn (admin override), join as a job. Each is one
`run_script` call, one compact dict back.

| Script | Args | Purpose |
| --- | --- | --- |
| `ghost_out.py` | — | Verb `Ghost` + confirm the AlertModal. Returns whether the prompt appeared and was confirmed. |
| `respawn.py` | `choice` (default `"Yes"`) | Verb `Respawn`; answers the override prompt (server has respawn disabled; localhost admin gets asked). |
| `join_as_job.py` | `job` (required, e.g. `"Medical Doctor"`) | `lobby join` -> `select_job`. Late-joiners spawn **buckled into an Arrival Shuttle seat** — follow with `arrival_goto.py`. |
| `arrival_goto.py` | `target: ["Area Name", ...alias]`, `exit?`, `unbuckle?`, `attempts?`, `wait_s?` | The post-join arrival flow, generic: click the seat ONLY if the Buckled alert is up (guarding the sit-back-down trap), leave the shuttle (retries while it is still flying), then walk to the first target area that works. Replaces the one-off `unbuckle_to_bar.py` example. |
| `ride_shuttle.py` | `goto_area`?, `station_z`?=2, `max_wait_s`?=420 | Unbuckle + ride the arrival shuttle to the station (dock detection = the mob's z changes; movement-free), then optional `walk_to(area=...)`. Supersedes arrival_goto's shuttle half. The transit "Weightless" alert is stale noise - never click "Succumb" (suicide). |

Gotchas
- The job name must match the menu's exact key (`Medical Doctor`, not `MD`).
- After ghosting, your old body stays where it stood; the client may later
  *forget* it if it leaves view (re-search before acting on its ID).
- Respawn override says "Respawning is currently disabled..." — `Yes` is the
  admin-sanctioned answer here (operator's test server).
