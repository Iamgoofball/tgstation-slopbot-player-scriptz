# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Toggle the worn-inventory slot display (the "toggle" button at the bottom
left of the HUD, state=toggle at WEST:6,SOUTH:5). Worn slots (suit, head,
gloves...) are hidden by default; clicking the button reveals them, after
which `sk.inventory()` lists slots like "suit storage", "head", "hands".

Run: run_script {script: ".../inventory/toggle_worn.py"}
Returns {found, clicked, worn_visible}.
"""
import re
out = {}
s = ""
cur = None
for i in range(8):                      # the button may sit on a later page
    a = sk.screen(all=True, cursor=cur).text or ""
    m = re.search(r"next_cursor (\S+)", a)
    hit = re.search(r'- obj (\d+) "toggle" at WEST', a)
    if hit:
        out["found"] = int(hit.group(1))
        break
    cur = m.group(1) if m else None
    if not cur:
        break
if not out.get("found"):
    raise SystemExit('"toggle" button not on any screen page')
c = sk.click(object_id=out["found"], expect_name="toggle")
time.sleep(0.5)
out["clicked"] = ("clicked: obj %d" % out["found"]) in (c.text or "")
inv = (sk.inventory().text or "")
out["worn_visible"] = bool(re.search(r"in slot \"(suit storage|head|gloves|wear_suit)\"", inv, re.I))
out["ok"] = out["clicked"]
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
