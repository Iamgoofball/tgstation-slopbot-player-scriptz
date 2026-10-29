# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Scan a patient with a health analyzer; return a tiny parsed dict.

Run: run_script {script: "E:/byond_agent_test/tgstation-slopbot-player-scriptz/medical/analyze_patient.py",
                 args: {"mob": 2892, "expect_name": "Lennox Fields"}}
Finds a health analyzer (held -> X-swap; else floor-in-view -> pick up), clicks
the mob, parses the report. Default return <= ~300 chars; verbose=true adds
the raw report tail.
"""
import re
opts = args or {}
mob = opts.get("mob"); name = opts.get("expect_name") or ""
if mob is None:
    raise ValueError("args: {'mob': id, 'expect_name': 'name'}")
m0 = re.search(r"mob (\d+)", sk.status().get("you") or "")
me = int(m0.group(1)) if m0 else None
# the client forgets mobs that leave view: re-find by name when the id is stale
if name:
    s = sk.search(query=name, kind="mob", all_things=True).text or ""
    if not any(re.search(r"mob " + str(mob) + r"\b", l) for l in s.split("\n")):
        for l in s.split("\n"):
            mm = re.search(r"mob (\d+) \"" + re.escape(name), l)
            if mm and int(mm.group(1)) != me and "ghost" not in l and "invisible" not in l:
                mob = int(mm.group(1))
                break

def hand_free_hands():
    inv = sk.inventory().text or ""
    hands = [l for l in inv.split("\n") if "in slot" in l and "hand" in l]
    return inv, hands

def ensure_analyzer_active():
    inv, hands = hand_free_hands()
    held = [l for l in inv.split("\n") if "health analyzer" in l.lower()]
    if held:
        if not any("handactive" in l for l in held):
            sk.key(key="X"); time.sleep(0.3)  # swap to the hand holding it
        return True
    s = sk.search(query="health analyzer", kind="obj", in_view=True).text or ""
    m = re.search(r"obj (\d+) \"", s)
    if not m:
        s = sk.search(query="health analyzer", kind="obj", all_things=True).text or ""  # anywhere the client knows
        m = re.search(r"obj (\d+) \"", s)
    if not m:
        return False
    aid = int(m.group(1))
    inv, hands = hand_free_hands()
    if "handactive" in inv:
        sk.key(key="Q"); time.sleep(0.4)  # X-swap frees no hand: drop the active item
    bot.goto(object_id=aid, expect_name="health analyzer", adjacent=True)
    sk.click(object_id=aid, expect_name="health analyzer")
    time.sleep(0.5)
    return "health analyzer" in (sk.inventory().text or "").lower()

if not ensure_analyzer_active():
    raise SystemExit("no health analyzer in hands or in view")

bot.goto(object_id=mob, expect_name=name or None, adjacent=True)  # scans need adjacency
c = sk.click(object_id=mob, expect_name=name or None)
txt = c.text or ""
if "Analyzing results" not in txt:
    txt += "\n" + (sk.read_chat(wait_s=2.5).text or "")

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
    bad = {}
    for organ in ("Heart", "Lungs", "Liver", "Kidneys", "Stomach", "Brain"):
        m = re.search(r"\b" + organ + r"\b[^\n]{0,40}?(Severely Damaged|Mildly Damaged|Non-Functional|Dysfunctional|Critical|Absent)", t)
        if m:
            bad[organ] = m.group(1)
    d["bad_organs"] = bad
    d["dark"] = "too dark" in t
    return d

out = parse_scan(txt)
out["ok"] = ("Analyzing results" in txt) and not out["dark"]
if out["dark"]:
    out["detail"] = "too dark to scan here"
if opts.get("verbose"):
    out["tail"] = txt[-240:]
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
