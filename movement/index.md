# movement/

Locomotion and hauling. One call per destination; each returns a compact
`ok / now / followed` dict.

| Script | Args | Purpose |
| --- | --- | --- |
| `goto_area.py` | `area` | Walk into a named area (needs the map loaded — see `setup/load_map.py`). |
| `goto_tile.py` | `x`, `y` | Walk to a tile; falls back to the nearest free tile when taken. |
| `pull_mob_to.py` | `mob`, plus `to_x`/`to_y` OR `onto_id`+`onto_kind`+`onto_name` | Ctrl+click grab, haul, optional buckle onto table/stasis. Verifies grab, following, placement. |

Gotchas
- **Pull = Ctrl+click** in this fork. Plain empty-hand clicks shove; drag
  mob→mob opens the StripMenu instead of pulling. Drag mob→obj = buckle/place.
- `pull0` in the HUD `stop pulling` button state means NOT pulling.
- Bodies you follow can be *forgotten* by the client after they leave view —
  re-search before re-grabbing.
- A defib shock on the patient electrocutes the puller and **breaks the pull**.
