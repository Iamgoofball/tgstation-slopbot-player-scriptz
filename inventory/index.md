# inventory/

Hands, containers, HUD slots. All returns are tiny (slot lines, ok flags).

| Script | Args | Purpose |
| --- | --- | --- |
| `drop_active_hand.py` | — | Q-drop with verification (`ok` only if the active hand was holding something and is empty now). |
| `open_held_container.py` | `container_id`, `expect_name` | **Alt-click** the held container, verify the UI opened, list item ids/names/uses. Alt-click is the only reliable opener — a plain in-hand click often does nothing. |
| `take_from_container.py` | `item_id`, `expect_name`, `auto_drop?` | Take an item from an open UI into an empty hand (drops the active item first when `auto_drop`). Verifies the item id landed in a hand slot. |
| `equip_to_slot.py` | `mode: equip` + `item_id`, `hud_slot_id` — or `mode: remove_to_turf` + `to_x/to_y` | Equip held → HUD slot (click the slot button); or drag a worn item to a turf. |

Gotchas
- **Bags resist removal**: dragging a worn bag to a turf dumps its *contents*
  and stays worn. To actually strip worn gear: drag your mob onto an adjacent
  mob → StripMenu → strip the row (unproven live; TODO).
- Storage takes need an **empty hand** (the item lands there and activates it).
- `state=pull0`-style HUD states are the cheap way to read toggles.
