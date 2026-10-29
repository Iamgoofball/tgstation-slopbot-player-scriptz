"""Wrench a thing with the wrench from the toolbelt: opens the belt
(alt-click), takes the wrench into the active hand, clicks the target, stows
the wrench back into the belt.

Run: run_script {script: ".../engineering/wrench.py", args: {"id": 38318}}
Optional: {"belt": 169154}. Returns {wrenched, target}. Use for canisters on
connector ports (verify with ui_batch: portConnected 1), girders, machines.
\"\"\""""
import re
opts = args or {}
oid = opts.get("id")
belt = opts.get("belt") or 169154
if not oid:
    raise ValueError("args: {'id': obj_id, 'belt'?: id}")
out = {"id": oid}
bot.goto(object_id=oid, adjacent=True)
time.sleep(0.3)
# open the toolbelt
sk.click(object_id=belt, alt=True, expect_name="toolbelt")
time.sleep(1.0)
wid = None
# find the wrench: belt window items may appear in view or inventory
s = (sk.search(query="wrench", in_view=True).text or "")
m = re.search(r"obj (\d+) \"wrench\"", s)
if not m:
    cur = None
    for i in range(4):
        a = sk.screen(all=True, cursor=cur).text or ""
        mm = re.search(r"next_cursor (\S+)", a)
        m = re.search(r'- obj (\d+) "wrench"', a)
        if m:
            break
        cur = mm.group(1) if mm else None
        if not cur:
            break
if not m:
    raise SystemExit("wrench not found after opening toolbelt")
wid = int(m.group(1))
out["wrench"] = wid
sk.click(object_id=wid, expect_name="wrench")     # take to hand
time.sleep(0.6)
inv = (sk.inventory().text or "")
wl = [l for l in inv.split("\n") if "wrench" in l.lower()]
if wl and "handactive" not in wl[0]:
    sk.key(key="X"); time.sleep(0.4)
c = sk.click(object_id=oid, expect_name=None)
time.sleep(1.2)
out["click"] = (c.text or "")[:140]
out["wrenched"] = "wrench" in (c.text or "").lower() or "wrench" in (out["click"] or "")
# stow wrench back into belt
sk.click(object_id=belt, alt=True, expect_name="toolbelt")
time.sleep(0.8)
sk.click(object_id=wid, expect_name="wrench")     # belt item click stores it
time.sleep(0.6)
out
