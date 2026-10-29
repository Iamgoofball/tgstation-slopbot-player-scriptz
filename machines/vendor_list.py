# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Open a vending machine (empty active hand) and return its product rows.

Run: run_script {script: "E:/byond_agent_test/tgstation-slopbot-player-scriptz/machines/vendor_list.py",
                 args: {"vendor": 17794, "expect_name": "NanoDrug Plus",
                        "match": "tox|dylovene|tricord"}}
Rows carry the `ref` needed by machines/vend_buy.py. `match` (regex, optional)
filters the returned rows; the item must be walked into view first.
"""
import re
opts = args or {}
vid, vname = opts.get("vendor"), opts.get("expect_name")
if vid is None:
    raise ValueError("args: {'vendor': id, 'expect_name': 'name', 'match': 'regex?'}")

def active_hand_item():
    for l in (sk.inventory().text or "").split("\n"):
        if "handactive" in l:
            return l
    return None

if active_hand_item():
    sk.key(key="Q"); time.sleep(0.4)  # vendors refuse clicks with an item in hand
c = sk.click(object_id=vid, expect_name=vname)
m = re.search(r"(tgui-window-\d+)", c.text or "")
if not m:
    raise SystemExit("vendor tgui did not open: " + (c.text or "")[-140:])
wid = m.group(1)
time.sleep(0.4)
w = sk.tgui_window(id=wid, find=opts.get("find"), max_chars=opts.get("max_chars", 6000))
t = w.text or ""
rows = re.findall(r'([A-Za-z0-9 ()\/\-\+\'\.]{4,60}?)\s*:?\s*(\d+)? ?cr\b[^\n]*vend \{"ref": "(\[[^\]]+\])"', t)
pat = opts.get("match")
out = []
for name_, cr, ref in rows:
    if pat and not re.search(pat, name_, re.I):
        continue
    out.append({"name": name_.strip()[:44], "cr": cr, "ref": ref})
RESULT = ({"ok": bool(out) or len(rows) > 0, "rows": out[:10],
 "raw_len": len(t), "note": "no match filter -> rows shows first hits; widen 'match'"})

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
