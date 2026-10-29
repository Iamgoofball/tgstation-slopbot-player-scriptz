"""Open a held container's storage UI (alt-click in this fork) and list its items.

Run: run_script {script: ".../inventory/open_held_container.py",
                 args: {"container_id": 186012, "expect_name": "surgical medkit"}}
Items are the UI grid entries (numeric screen_loc, not state=storage_* chrome).
"""
import re
opts = args or {}
cid, cname = opts.get("container_id"), opts.get("expect_name")
if cid is None:
    raise ValueError("args: {'container_id': id, 'expect_name': 'name'}")
sk.click(object_id=cid, expect_name=cname, alt=True)
time.sleep(0.5)
lines = (sk.screen(page_size=60).text or "").split("\n")
ui_open = any(("storage_close" in l) or ("go up a storage level" in l) for l in lines)
items = [l[2:110] for l in lines
         if l.startswith("- obj")
         and re.match(r"- obj \d+ \"[^\"]*\" at \d+:\d+,\d+:\d+", l)
         and "state=storage" not in l]
{"ok": ui_open, "container": cid, "items": items[:12]}
