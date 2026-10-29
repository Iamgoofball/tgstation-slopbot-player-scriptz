# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""One-envelope heal loop: scan a patient, apply sutures (brute) / regen mesh
(burn) from a medkit until clean or items run out, re-scan, return deltas.

Run: run_script {script: "E:/byond_agent_test/tgstation-slopbot-player-scriptz/medical/treat_patient.py",
                 args: {"mob": 2892, "expect_name": "Lennox Fields", "medkit": 186012}}
Tox does NOT decay on its own — it needs dylovene/tricordrazine. Sutures/mesh
refuse corpses — dead patients go through defib_revive.py first (gauze is the
only dead-safe stack). Compact return; verbose=true adds scan sizes.
"""
import re
opts = args or {}
mob = opts.get("mob"); name = opts.get("expect_name") or ""
medkit = opts.get("medkit")
if mob is None:
    raise ValueError("args: {'mob': id, 'expect_name': 'name', 'medkit': id?}")

def parse_scan(t):
    t = re.sub(r"<[^>]+>", " ", t)
    d = {}
    m = re.search(r"Overall status:?\s*\**\s*(\d+)% healthy", t); d["health"] = int(m.group(1)) if m else None
    d["dead"] = bool(re.search(r"\bDeceased\b", t))
    n = None
    m = re.search(r"Overall:\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)", t)
    if m:
        n = [int(m.group(i)) for i in (1, 2, 3, 4)]
    if n is None:
        m = re.search(r"Overall:?\s*\**\s*[|\s]*([\d|\s]+)", t)
        if m:
            n = [int(x) for x in re.findall(r"\d+", m.group(1))][:4]
    if n and len(n) == 4:
        d["brute"], d["burn"], d["tox"], d["oxy"] = n
    m = re.search(r"Blood level:?\s*\**\s*(\d+)%", t, re.I)
    if m:
        d["blood"] = int(m.group(1))
    d["dark"] = "too dark" in t
    return d

def ensure_analyzer_active():
    inv = sk.inventory().text or ""
    held = [l for l in inv.split("\n") if "health analyzer" in l.lower()]
    if held:
        if not any("handactive" in l for l in held):
            sk.key(key="X"); time.sleep(0.3)
        return True
    s = sk.search(query="health analyzer", kind="obj", in_view=True).text or ""
    m = re.search(r"obj (\d+) \"", s)
    if not m:
        s = sk.search(query="health analyzer", kind="obj", all_things=True).text or ""  # anywhere the client knows
        m = re.search(r"obj (\d+) \"", s)
    if not m:
        return False
    aid = int(m.group(1))
    if "handactive" in inv:
        sk.key(key="Q"); time.sleep(0.4)  # X-swap frees no hand: drop the active item
    bot.goto(object_id=aid, expect_name="health analyzer", adjacent=True)
    sk.click(object_id=aid, expect_name="health analyzer")
    time.sleep(0.5)
    return "health analyzer" in (sk.inventory().text or "").lower()

def scan():
    if not ensure_analyzer_active():
        return {}
    c = sk.click(object_id=mob, expect_name=name or None)
    t = c.text or ""
    if "Analyzing results" not in t:
        t += "\n" + _pull_chat(2.5)
    return parse_scan(t)

def ui_open():
    return any(("storage_close" in l) or ("go up a storage level" in l)
               for l in (sk.screen(page_size=40).text or "").split("\n"))

def ui_find(kind_re):
    for l in (sk.screen(page_size=60).text or "").split("\n"):
        m = re.match(r"- obj (\d+) \"([^\"]*)\"", l)
        if m and re.search(kind_re, m.group(2).lower()):
            return int(m.group(1))
    return None

def get_item(kind_re):
    for l in (sk.inventory().text or "").split("\n"):
        if "in slot" in l and "hand" in l and re.search(kind_re, l.lower()):
            m = re.search(r"obj (\d+)", l)
            if m:
                return int(m.group(1))
    if medkit is None:
        return None
    if not ui_open():
        sk.click(object_id=medkit, expect_name=opts.get("medkit_name", "surgical medkit"), alt=True)
        time.sleep(0.5)
    iid = ui_find(kind_re)
    if iid is None:
        return None
    hands = [l for l in (sk.inventory().text or "").split("\n") if "in slot" in l and "hand" in l]
    if "handactive" in (sk.inventory().text or "") and len(hands) >= 2:
        sk.key(key="X"); time.sleep(0.3)
    elif "handactive" in (sk.inventory().text or ""):
        sk.key(key="Q"); time.sleep(0.4)
    sk.click(object_id=iid, expect_name=None)
    time.sleep(0.5)
    return iid if re.search(r"obj " + str(iid) + r"\b", sk.inventory().text or "") else None

def apply(kind_re):
    iid = get_item(kind_re)
    if iid is None:
        return None
    c = sk.click(object_id=mob, expect_name=name or None)
    t = c.text or ""
    time.sleep(1.3)  # stack auto-repeat ~1 s per use
    return {"id": iid,
            "used": bool(re.search(r"suture|apply|patch|mesh|gauze|begin", t, re.I)),
            "refused": "refuse" in t.lower() or "too injured" in t.lower()}

before = scan()
if not before or before.get("dark"):
    raise SystemExit("scan failed: " + repr(before))
if before.get("dead"):
    raise SystemExit("patient dead: run medical/defib_revive.py first (sutures/mesh refuse corpses)")
rounds, log = 0, []
after = dict(before)
for _ in range(int(opts.get("max_rounds", 6))):
    rounds += 1
    if (after.get("brute") or 0) > 0:
        r = apply(r"suture")
        if r is None:
            log.append("sutures exhausted"); break
        log.append("suture:" + str(r["used"])); after = scan()
        if r["refused"]:
            break
    if (after.get("burn") or 0) > 0:
        r = apply(r"mesh")
        if r is None:
            log.append("mesh exhausted"); break
        log.append("mesh:" + str(r["used"])); after = scan()
        if r["refused"]:
            break
    if (after.get("brute") or 0) == 0 and (after.get("burn") or 0) == 0:
        log.append("clean"); break
keys = ("health", "brute", "burn", "tox", "oxy")
RESULT = ({"ok": (after.get("brute") or 0) == 0 and (after.get("burn") or 0) == 0,
 "before": {k: before.get(k) for k in keys},
 "after": {k: after.get(k) for k in keys + ("blood",)},
 "rounds": rounds, "log": log})

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
