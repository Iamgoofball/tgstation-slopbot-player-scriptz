# machines/

Vendor and tray interactions. One call per purchase / tool grab.

| Script | Args | Purpose |
| --- | --- | --- |
| `vend_buy.py` | `vendor`, `expect_name`, `buy: [{ref, premium}]`, `auto_drop?` | Open the vendor tgui (needs an EMPTY active hand — drops it for you with `auto_drop`), vend each ref, report `vended` / `on_floor` per item. |
| `vendor_list.py` | `vendor`, `expect_name`, `match?` (regex), `max_chars?` | Open the vendor and return product rows (name / cr / ref) — the discovery step before `vend_buy.py`. `match` filters to what you're looking for. |
| `tray_take.py` | `tray_id`, `expect_name`, `tool`, `auto_drop?` | RMB the surgery tray → specific-tool picker → take the named tool into a hand. |
| `fabricator_control.py` | `mode`: status/list/build/insert/eject, `machine`?, `design`?, `amount`?, `wait`?, `sheet`?/`sheet_name`?, `mat`?, `amount_mat`?, `pattern`? | Generic driver for every tgui "Fabricator" lathe — department protolathe, circuit imprinter, department techfabs (NOT the ExosuitFabricator: that is `roboticist/exofab_control.py`). status = silo materials/busy/queue; list = designs (path/name, regex filter); build = name→path resolve → `build {design_path, amount}` verified via `busy: 0 -> 1` in the act's data_changes, `wait` polls to done and lists the 3x3 around the fab; insert = find the sheet (id — known index, not the in-view page — or name), pickup, walk BACK to the machine, adjacent click, verify via the ore-silo line AND silo growth; eject = `remove_mat {amount, ref}` (not yet live-verified). The job wrappers (`scientist/protolathe_print.py`) set the default machine. |

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
- **Fabricators (protolathe / circuit imprinter / techfab) draw from the
  SHARED ORE SILO**: 1 sheet = 100 units, a 50-sheet stack = 5000;
  `materialMaximum` (7500) is the fab's own store cap, not the silo's.
  Opening the tgui needs an EMPTY active hand; inserting needs the sheet IN
  the active hand + adjacency. Prints eject onto the machine tile or a
  neighbor — scan the 3x3 and match the design name.
