# machines/

Vendor and tray interactions. One call per purchase / tool grab.

| Script | Args | Purpose |
| --- | --- | --- |
| `vend_buy.py` | `vendor`, `expect_name`, `buy: [{ref, premium}]`, `auto_drop?` | Open the vendor tgui (needs an EMPTY active hand — drops it for you with `auto_drop`), vend each ref, report `vended` / `on_floor` per item. |
| `vendor_list.py` | `vendor`, `expect_name`, `match?` (regex), `max_chars?` | Open the vendor and return product rows (name / cr / ref) — the discovery step before `vend_buy.py`. `match` filters to what you're looking for. |
| `tray_take.py` | `tray_id`, `expect_name`, `tool`, `auto_drop?` | RMB the surgery tray → specific-tool picker → take the named tool into a hand. |

Gotchas
- Clicking a vendor with something in the active hand = "does not accept X!".
- To discover product refs: open the vendor once (empty hand) and read the
  tgui product list — rows look like `medical gel (synthflesh): 350 cr, 2 left
  -> vend {"ref": "[0x...]", "premium": true}`.
- Vended items land in a free hand, otherwise drop on your tile.
- Tray LMB = **random** tool; only RMB is deterministic.
- **Premium rows are hidden/contraband records**: `vend {ref, premium}` on
  them is a SILENT no-op unless the vendor's `extended_inventory` is pulsed on
  via its wires panel. Normal products vend with a bare `{"ref": ...}` and the
  department discount auto-applies (e.g. list 50 cr → 10 cr for an MD).
