# common/

Shared helpers every scriptz script loads. Neither file runs standalone and
neither carries the safety prelude itself (README section 1: they are "the
only files without it") — they ARE the prelude.

| File | Args | Purpose |
| --- | --- | --- |
| `watch_prelude.py` | — | The SAFETY PRELUDE, exec'd at the top of every script: `precheck()` (start check — aborts on danger), `postcheck()` (end check, returns the full sit-rep: chat tail, heard speech, needs_response, danger words, view census), `watch(tag)` (mid-script danger check — call between EVERY world-affecting step). Also owns `_pull_chat()` chat accumulation so speech arriving mid-script is never lost. |
| `check.py` | — | Standalone session check for BETWEEN run_script envelopes (the agent runs it directly: chat + status + view in one answer). Scripts must not exec it — use watch_prelude. |

The DANGER regex (delam, countdown, explosions, flood, fire, shock, attack,
husk, crit/dead status...) lives in watch_prelude.py; `_view_census()` scans
the ASCII view for threats chat never mentions (fires, singulo, breaches).
