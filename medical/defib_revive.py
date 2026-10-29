# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Defib a dead patient via wall mount (the proven route): gate on the scan,
fetch paddles from the mount, wield, combat off, not pulling, shock, verify.

Run: run_script {script: "E:/byond_agent_test/tgstation-slopbot-player-scriptz/medical/defib_revive.py",
                 args: {"mob": 2892, "expect_name": "Lennox Fields"}}
Optional: {"mount": id}. Fork truths: defib refuses brute/burn >= 180
("Tissue damage too severe") and a Non-Functional heart; "Severely Damaged"
still shocks. Revived patients wake at -50 health. The shock ZAPS THE PULLER
and breaks the pull — make sure you are not pulling before shocking.
"""
import re
opts = args or {}
mob = opts.get("mob"); name = opts.get("expect_name") or ""
if mob is None:
    raise ValueError("args: {'mob': id, 'expect_name': 'name'}")
out = {"mob": mob}

m0 = re.search(r"mob (\d+)", sk.status().get("you") or "")
me = int(m0.group(1)) if m0 else None
if name:  # the client forgets mobs that leave view: re-find by name
    s = sk.search(query=name, kind="mob", all_things=True).text or ""
    if not any(re.search(r"mob " + str(mob) + r"\b", l) for l in s.split("\n")):
        for l in s.split("\n"):
            mm = re.search(r"mob (\d+) \"" + re.escape(name), l)
            if mm and int(mm.group(1)) != me and "ghost" not in l and "invisible" not in l:
                mob = int(mm.group(1))
                break
bot.goto(object_id=mob, expect_name=name or None, adjacent=True)

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
    d["heart_dead"] = bool(re.search(r"\bHeart\b[^\n]{0,40}?Non-Functional", t))
    d["dark"] = "too dark" in t
    return d

def scan():
    inv = sk.inventory().text or ""
    if "health analyzer" not in inv.lower():
        return {}
    if not any("handactive" in l and "health analyzer" in l.lower()
               for l in inv.split("\n")):
        sk.key(key="X"); time.sleep(0.3)
    c = sk.click(object_id=mob, expect_name=name or None)
    t = c.text or ""
    if "Analyzing results" not in t:
        t += "\n" + _pull_chat(2.5)
    return parse_scan(t)

gate = scan()
out["gate"] = {k: gate.get(k) for k in ("dead", "brute", "burn", "heart_dead")}
fail = None
if gate:
    if not gate.get("dead"):
        fail = "patient not dead; no shock needed"
    elif (gate.get("brute") or 0) >= int(opts.get("gate_brute", 180)) or \
         (gate.get("burn") or 0) >= int(opts.get("gate_burn", 180)):
        fail = "brute/burn >= 180 - heal first (treat_patient.py / gel)"
    elif gate.get("heart_dead"):
        fail = "heart Non-Functional - defib will refuse"
if fail:
    raise SystemExit(fail)

# paddles from the mount (empty active hand clicks the mount)
mount = opts.get("mount")
if mount is None:
    m = re.search(r"obj (\d+) \"", sk.search(query="defibrillator mount", kind="obj", in_view=True).text or "")
    if not m:  # mounts are sparse: search everywhere the client knows, then walk
        m = re.search(r"obj (\d+) \"", sk.search(query="defibrillator mount", kind="obj", all_things=True).text or "")
    mount = int(m.group(1)) if m else None
if mount is None:
    raise SystemExit("no defibrillator mount known; pass args.mount")
bot.goto(object_id=mount, expect_name="defibrillator mount", adjacent=True)

inv = sk.inventory().text or ""
if "paddles" not in inv.lower():
    hands = [l for l in inv.split("\n") if "in slot" in l and "hand" in l]
    act = [l for l in hands if "handactive" in l]
    if act:
        if len(hands) < 2:
            sk.key(key="X"); time.sleep(0.3)          # switch to the empty hand
        elif "health analyzer" in act[0].lower():
            sk.key(key="X"); sk.key(key="Q"); time.sleep(0.5)  # drop the other item, keep the analyzer
        else:
            sk.key(key="Q"); time.sleep(0.4)          # drop the active (non-analyzer) item
    c = sk.click(object_id=mount, expect_name="defibrillator mount")
    time.sleep(0.6)
    if "paddles" not in (sk.inventory().text or "").lower():
        raise SystemExit("mount click did not yield paddles: " + (c.text or "")[-120:])
paddle = None
for l in (sk.inventory().text or "").split("\n"):
    if "paddle" in l.lower():
        m = re.search(r"obj (\d+)", l)
        if m:
            paddle = int(m.group(1))
if paddle is None:
    raise SystemExit("paddle id not found in inventory")

# wield (in-hand click), then combat off
c = sk.click(object_id=paddle, expect_name=None)
out["wielded"] = "wield" in (c.text or "") or "both hands" in (c.text or "")
time.sleep(0.4)
sc = sk.screen(page_size=40).text or ""
for l in sc.split("\n"):
    if "combat mode" in l and "combat_off" not in l:
        m = re.search(r"obj (\d+)", l)
        if m:
            sk.click(object_id=int(m.group(1)))
            time.sleep(0.3)
        break
sc2 = sk.screen(page_size=40).text or ""
out["combat_off"] = "combat_off" in sc2
out["pulling"] = "pull0" not in sc2

# shock (walk back to the patient first - the mount may be far away)
bot.goto(object_id=mob, expect_name=name or None, adjacent=True)
c = sk.click(object_id=mob, expect_name=name or None)
t = c.text or ""
time.sleep(1.5)
t += "\n" + _pull_chat(2.5)
out["resus"] = "Resuscitation successful" in t
out["refused"] = "Tissue damage too severe" in t
out["zapped_puller"] = bool(re.search(r"shock|electrocut", t, re.I)) and not out["resus"]
after = scan()
out["after"] = {k: after.get(k) for k in ("health", "dead", "brute", "burn", "tox", "oxy")}
out["ok"] = out["resus"]
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
