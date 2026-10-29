"""Draw a reagent from a container with a syringe, then inject it into a mob.

Run: run_script {script: "E:/byond_agent_test/tgstation-slopbot-player-scriptz/medical/inject_reagent.py",
                 args: {"mob": 2892, "container_query": "multiver",
                        "purge_clicks": 3, "draw_clicks": 3, "inject_clicks": 3}}
Fork truths: this fork has NO syringe mode toggle — LMB injects, RMB draws.
`purge_clicks` first empties the syringe's preload into SELF (spaceacillin
preloads are harmless; needed so there is room to draw). Caller must stand
next to the container when calling; the script walks to the mob for the
injects and re-activates the syringe hand first.
"""
import re
opts = args or {}
mob = opts.get("mob")
cq = opts.get("container_query")
sq = opts.get("syringe_query", "syringe")
purge = int(opts.get("purge_clicks", 0))
draw = int(opts.get("draw_clicks", 0))
inject_n = int(opts.get("inject_clicks", 1))
if mob is None:
    raise ValueError("args: {'mob': id, 'container_query': 'multiver', ...}")
out = {"purged": 0, "drawn": 0, "injected": 0}

def hands():
    inv = sk.inventory().text or ""
    return [l for l in inv.split("\n") if "in slot" in l and "hand" in l], inv

def find_item(query, held_ok=True):
    if held_ok:
        hs, _ = hands()
        for l in hs:
            if re.search(query, l, re.I):
                m = re.search(r"obj (\d+)", l)
                if m:
                    return int(m.group(1)), "held"
    s = sk.search(query=query, in_view=True).text or ""
    m = re.search(r"obj (\d+) \"", s)
    if m:
        return int(m.group(1)), "floor"
    return None, None

def ensure_active(iid):
    hs, inv = hands()
    for l in hs:
        if str(iid) in l and "handactive" in l:
            return True
    if any(str(iid) in l for l in hs):
        sk.key(key="X"); time.sleep(0.3)
        return True
    return False

def acquire(query):
    iid, where = find_item(query)
    if iid is None:
        raise SystemExit("item not found in hands/view: " + query)
    hs, inv = hands()
    if where == "held":
        if not ensure_active(iid):
            raise SystemExit("held item hand-swap failed")
        return iid
    if "handactive" in inv:          # need a free hand for the floor pickup
        sk.key(key="Q"); time.sleep(0.4)
    bot.goto(object_id=iid, adjacent=True)
    sk.click(object_id=iid)
    time.sleep(0.5)
    hs, _ = hands()
    if not any(str(iid) in l for l in hs):
        raise SystemExit("floor pickup failed")
    ensure_active(iid)
    return iid

def click_chat(oid, name=None, right=False):
    c = sk.click(object_id=oid, expect_name=name, right=right)
    return c.text or ""

sid = acquire(sq)

m = re.search(r"mob (\d+)", sk.status().get("you") or "")
me = int(m.group(1)) if m else None
nm = re.search(r"mob \d+ \"([^\"]+)\"", sk.status().get("you") or "")
my_name = nm.group(1) if nm else None
if me is None:
    raise SystemExit("cannot resolve self mob id from status")
for _ in range(purge):
    t = click_chat(me, name=my_name)  # click SELF with the syringe, not the syringe itself
    if re.search(r"inject", t, re.I):
        out["purged"] += 1
    elif re.search(r"full|empty|nothing", t, re.I):
        break
    time.sleep(1.0)

if cq and draw:
    cid, _ = find_item(cq)
    if cid is None:
        raise SystemExit("container not found in hands/view: " + cq)
    for _ in range(draw):
        t = click_chat(cid, right=True)
        if re.search(r"draw|sample|transfer", t, re.I) and not re.search(r"full|unable|empty", t, re.I):
            out["drawn"] += 1
        time.sleep(0.8)

bot.goto(object_id=mob, expect_name=opts.get("mob_name"), adjacent=True)
ensure_active(sid)
for _ in range(inject_n):
    t = click_chat(mob, name=opts.get("mob_name"))
    if re.search(r"inject", t, re.I):
        out["injected"] += 1
    elif re.search(r"empty|nothing", t, re.I):
        break
    time.sleep(2.5)  # target injects have a do_after delay
out["ok"] = out["injected"] > 0
out
