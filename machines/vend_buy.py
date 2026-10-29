"""Buy items from a vending machine (NanoMed/NanoDrug/...): empty-hand click to
open the tgui, then vend by ref (premium flag for premium rows).

Run: run_script {script: ".../machines/vend_buy.py",
                 args: {"vendor": 17794, "expect_name": "NanoDrug Plus",
                        "buy": [{"ref": "[0x2100eb19]", "premium": true}]}}
Find refs/rows by opening the vendor once and reading the tgui product list.
The item vends into a free hand, else falls on the floor at your tile.
"""
import re
opts = args or {}
vid, vname = opts.get("vendor"), opts.get("expect_name")
buy = opts.get("buy") or []
if vid is None or not buy:
    raise ValueError("args: {'vendor': id, 'expect_name': 'name', 'buy': [{'ref': '[0x..]', 'premium': bool}]}")

def hands_full():
    t = (sk.inventory().text or "")
    return [l for l in t.split("\n") if "hand" in l and "in slot" in l]

if len(hands_full()) >= 2 and opts.get("auto_drop"):
    sk.key(key="Q")
    time.sleep(0.3)
if not hands_full() or "handactive" not in (sk.inventory().text or ""):
    pass  # active hand empty is what we want for opening
# open the vendor with an EMPTY ACTIVE hand
act_line = [l for l in (sk.inventory().text or "").split("\n") if "handactive" in l]
if act_line:
    sk.key(key="Q")
    time.sleep(0.3)
c = sk.click(object_id=vid, expect_name=vname)
m = re.search(r"(tgui-window-\d+)", c.text or "")
if not m:
    # the UI may already be open from a previous look — reuse it
    wins = sk.tgui_windows().text or ""
    m = re.search(r"(tgui-window-\d+):", wins)
if not m:
    raise ValueError("vendor tgui did not open: " + (c.text or "")[-150:])
wid = m.group(1)
res = []
for b in buy:
    a = sk.tgui_act(id=wid, action="vend",
                    params={"ref": b["ref"], **({"premium": True} if b.get("premium") else {})})
    t = (a.text or "")
    ok = ("out of the slot" in t) or re.search(r"amount: \d+ -> ", t)
    fell = "falls onto the floor" in t
    res.append({"ref": b["ref"], "vended": bool(ok), "on_floor": fell})
time.sleep(0.3)
{"ok": all(r["vended"] for r in res), "results": res}
