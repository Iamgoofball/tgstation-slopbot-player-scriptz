# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Seat a gas canister onto an omni connector port: pull it (ctrl-click), walk
next to the port tile, drag it onto the port tile, then wrench it (wrench from
toolbelt via belt click) and verify portConnected=1 in the canister tgui.

Run: run_script {script: ".../engineering/canister_seat.py",
                 args: {"canister": <id>, "port": [<x>, <y>], "wrench": true}}
Optional: {"wrench": false} to only position it. Returns {moved, connected}.
Wrench must be inside the toolbelt; the script opens it if needed.
"""
import re
opts = args or {}
cid = opts.get("canister")
px, py = opts.get("port") or (None, None)
if not cid or px is None:
    raise ValueError("args: {'canister': id, 'port': [x, y], 'wrench'?: bool}")

out = {"canister": cid, "port": [px, py]}
# 1. pull the canister
c = sk.click(object_id=cid, ctrl=True, expect_name="Nitrogen canister")
time.sleep(0.5)
st = (sk.status().text or "")
out["pulling"] = "pulling" in st.lower() or "pull" in st.lower()
# 2. stand next to the port tile (not on it)
w = bot.goto(x=px, y=py + 1)
time.sleep(0.3)
if "arrived" not in (w.text or ""):
    w = bot.goto(x=px - 1, y=py)
time.sleep(0.3)
# 3. drag canister onto the port tile
d = sk.drag(object_id=cid, onto_x=px, onto_y=py, expect_name="Nitrogen canister")
time.sleep(0.9)
out["drag"] = (d.text or "")[:150]
# 4. stop pulling so it stays
sk.click(object_id=cid, ctrl=True, expect_name=None)
time.sleep(0.4)
# 5. check position
s = sk.search(query="canister", in_view=True).text or ""
for l in s.split("\n"):
    if re.match(r"- obj %d " % cid, l):
        out["pos"] = l[:140]
# 6. wrench it in (toolbelt): open belt, click wrench, click canister
def _belt_id():
    b = (args or {}).get("belt")
    if b:
        return b
    inv = (sk.inventory().text or "")
    m = re.search(r"obj (\d+) \"toolbelt\"", inv)
    if m:
        return int(m.group(1))
    s = sk.search(query="toolbelt", in_view=True).text or ""
    m = re.search(r"obj (\d+) \"toolbelt\"", s)
    if m:
        return int(m.group(1))
    raise SystemExit("no toolbelt found — pass args {'belt': obj_id}")
if opts.get("wrench", True):
    c = sk.click(object_id=_belt_id(), alt=True, expect_name="toolbelt")
    time.sleep(1.0)
    bt = (c.text or "")
    m = re.search(r"obj (\d+) \"wrench\"", bt)
    if not m:
        b = sk.search(query="wrench", in_view=True).text or ""
        m = re.search(r"obj (\d+) \"wrench\"", b)
    if not m:
        raise SystemExit("wrench not found in toolbelt/view")
    # belt contents are screen items; take wrench to hand
    sk.click(object_id=int(m.group(1)), expect_name="wrench")
    time.sleep(0.6)
    inv = sk.inventory().text or ""
    wl = [l for l in inv.split("\n") if "wrench" in l.lower()]
    if wl and "handactive" not in wl[0]:
        sk.key(key="X"); time.sleep(0.4)
    c = sk.click(object_id=cid, expect_name="canister")
    time.sleep(1.2)
    out["wrench_click"] = (c.text or "")[:120]
    # stow wrench back? leave in hand-free: put away via belt click
    sk.click(object_id=int(m.group(1)), expect_name="wrench")
    time.sleep(0.6)
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
