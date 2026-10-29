"""Spray medigel on a corpse to bring its damage under the defib threshold.

Run: run_script {script: "E:/byond_agent_test/tgstation-slopbot-player-scriptz/medical/gel_corpse.py",
                 args: {"mob": 20, "expect_name": "Parabellum Phillips", "sprays": 2}}
Sutures/mesh refuse corpses; medigel does not (live-proven: synthflesh gel cut
a corpse 75 brute per spray). Gel is found in hands or on the floor (global
search), picked up, then sprayed at the mob; ends with a parsed scan.
"""
import re
opts = args or {}
mob = opts.get("mob"); name = opts.get("expect_name") or ""
if mob is None:
    raise ValueError("args: {'mob': id, 'expect_name': 'name', 'sprays': 2}")
gq = opts.get("gel_query", "synthflesh")
out = {"sprayed": 0, "gel": None}

m0 = re.search(r"mob (\d+)", sk.status().get("you") or "")
me = int(m0.group(1)) if m0 else None
if name:
    s = sk.search(query=name, kind="mob", all_things=True).text or ""
    if not any(re.search(r"mob " + str(mob) + r"\b", l) for l in s.split("\n")):
        for l in s.split("\n"):
            mm = re.search(r"mob (\d+) \"" + re.escape(name), l)
            if mm and int(mm.group(1)) != me and "ghost" not in l and "invisible" not in l:
                mob = int(mm.group(1)); break

def hands():
    inv = sk.inventory().text or ""
    return [l for l in inv.split("\n") if "in slot" in l and "hand" in l], inv

def find_gel():
    hs, _ = hands()
    for l in hs:  # already holding it?
        if re.search(r"gel", l, re.I):
            m = re.search(r"obj (\d+)", l)
            if m:
                return int(m.group(1)), "held"
    for q in (gq, "gel"):
        s = sk.search(query=q, in_view=True).text or ""
        m = re.search(r"obj (\d+) \"", s)
        if not m:
            s = sk.search(query=q, all_things=True).text or ""
            m = re.search(r"obj (\d+) \"", s)
        if m:
            return int(m.group(1)), "floor"
    return None, None

def ensure_active(iid):
    hs, _ = hands()
    for l in hs:
        if str(iid) in l and "handactive" in l:
            return True
    if any(str(iid) in l for l in hs):
        sk.key(key="X"); time.sleep(0.3)
        return True
    return False

gid, where = find_gel()
if gid is None:
    raise SystemExit("no medigel found (hands/view/known) - NanoDrug Plus sells it")
out["gel"] = gid
hs, inv = hands()
if where == "held":
    ensure_active(gid)
else:
    if "handactive" in inv:
        sk.key(key="Q"); time.sleep(0.4)  # X-swap frees no hand: drop the active item
    bot.goto(object_id=gid, adjacent=True)
    sk.click(object_id=gid)
    time.sleep(0.5)
    if not ensure_active(gid):
        raise SystemExit("gel pickup failed")

bot.goto(object_id=mob, expect_name=name or None, adjacent=True)
empty = False
for _ in range(int(opts.get("sprays", 2))):
    c = sk.click(object_id=mob, expect_name=name or None)
    t = c.text or ""
    if re.search(r"empty|out of", t, re.I):
        empty = True; break
    if re.search(r"spray|gel|apply", t, re.I):
        out["sprayed"] += 1
    time.sleep(4.0)  # medigel on others has a 3 s do_after - shorter sleeps cancel it

# final scan with the analyzer (X-swap to it if needed)
if "health analyzer" in (sk.inventory().text or "").lower():
    if not any("handactive" in l and "health analyzer" in l.lower() for l in hands()[0]):
        sk.key(key="X"); time.sleep(0.3)
    c = sk.click(object_id=mob, expect_name=name or None)
    t = c.text or ""
    if "Analyzing results" not in t:
        t += "\n" + (sk.read_chat(wait_s=2.5).text or "")
    tt = re.sub(r"<[^>]+>", " ", t)
    m = re.search(r"Overall status:?\s*\**\s*(\d+)% healthy", tt)
    scan = {"health": int(m.group(1)) if m else None}
    m = re.search(r"Overall:\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)", tt)
    if m:
        scan.update(brute=int(m.group(1)), burn=int(m.group(2)), tox=int(m.group(3)), oxy=int(m.group(4)))
    scan["dead"] = bool(re.search(r"\bDeceased\b", tt))
    out["scan"] = scan
out["empty"] = empty
out["ok"] = out["sprayed"] > 0
out
