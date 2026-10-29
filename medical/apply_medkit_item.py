# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Take one medical item from a container UI (or floor) and apply it to a mob.

Run: run_script {script: "E:/byond_agent_test/tgstation-slopbot-player-scriptz/medical/apply_medkit_item.py",
                 args: {"item": "suture", "container": 186012, "mob": 2892}}
`item` = id, or kind string ("suture"|"mesh"|"gauze"|"ointment"|"bruise")
resolved from the open container UI. Verifies the take landed in a hand and
the apply message; returns uses left on stacks.
"""
import re
opts = args or {}
item, container, mob = opts.get("item"), opts.get("container"), opts.get("mob")
if mob is None or item is None:
    raise ValueError("args: {'item': id|kind, 'container': id?, 'mob': id, 'mob_name': ...}")
KINDS = {"suture": "suture", "mesh": "mesh", "gauze": "gauze",
         "ointment": "ointment", "bruise": "bruise"}

def hand_lines():
    return [l for l in (sk.inventory().text or "").split("\n") if "in slot" in l and "hand" in l]

def holding(iid=None, kind_re=None):
    for l in hand_lines():
        if (iid is not None and str(iid) in l) or (kind_re and re.search(kind_re, l.lower())):
            return l.strip()[:100]
    return None

iid = item if isinstance(item, int) else None
kind_re = None
if iid is None:
    kind_re = KINDS.get(str(item).lower())
    if kind_re is None:
        raise ValueError("item kind must be one of: " + ", ".join(KINDS))

cur = holding(iid=iid, kind_re=kind_re)
if cur is None:
    if container:
        if not any(("storage_close" in l) or ("go up a storage level" in l)
                   for l in (sk.screen(page_size=40).text or "").split("\n")):
            sk.click(object_id=container, expect_name=opts.get("container_name"), alt=True)
            time.sleep(0.5)
        for l in (sk.screen(page_size=60).text or "").split("\n"):
            m = re.match(r"- obj (\d+) \"([^\"]*)\"", l)
            if m and ((kind_re and re.search(kind_re, m.group(2).lower()))
                      or (iid is not None and str(iid) == m.group(1))):
                iid = int(m.group(1)); break
    if iid is None:
        raise SystemExit("item not resolved (no id given / not in container UI)")
    hands = hand_lines()
    if "handactive" in (sk.inventory().text or "") and len(hands) >= 2:
        sk.key(key="X"); time.sleep(0.3)   # keep active item; take lands in free hand
    elif "handactive" in (sk.inventory().text or ""):
        sk.key(key="Q"); time.sleep(0.4)
    sk.click(object_id=iid, expect_name=None)
    time.sleep(0.5)
    cur = holding(iid=iid)
    if cur is None:
        raise SystemExit("take failed (click-by-id needs the item in view or UI open)")

c = sk.click(object_id=mob, expect_name=opts.get("mob_name"))
t = c.text or ""
time.sleep(1.3)  # stacks apply ~1 s per use
m = re.search(r"\(x (\d+)\)", cur or "")
RESULT = ({"ok": bool(re.search(r"suture|apply|patch|mesh|gauze|begin|inject", t, re.I))
       and "refuse" not in t.lower(),
 "item": iid, "uses": int(m.group(1)) if m else None, "chat": t[-140:]})

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
