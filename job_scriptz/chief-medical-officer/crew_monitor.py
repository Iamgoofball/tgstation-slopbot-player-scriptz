# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""The CMO's crew-monitor triage, ONE envelope: who is dead, critical or
wounded station-wide, from the crew monitoring console.

Run: run_script {script: ".../job_scriptz/chief-medical-officer/crew_monitor.py",
                 args: {"console"?: id, "x"?, "y"?, "min_damage"?: 20}}
console id optional — auto-surveys "crew monitoring console" in view (Medbay
Central ~89,111 has one in Paramedic Dispatch at 85,107; Bridge has another).
Read-only. Parses data.sensors[] from the CrewConsole window:
  ref [mob_N], name, assignment, ijob, life_status (0 conscious, 1-2
  unconscious/crit, 3 DEAD), oxydam/toxdam/burndam/brutedam, health, area.
Classifies: DEAD (life_status 3), CRIT (life_status 1-2 or health < 0),
WOUNDED (any damage >= min_damage), BROKEN (health -50 + wild random data =
BROKEN_SENSORS garbage, code crew.dm:249), OFF (binary only: no damage
fields = suit sensors not on vitals — remind them).
Verdict lines per casualty + counts. NOTE: the click needs an EMPTY ACTIVE
hand (the CMO spawns holding a surgical medkit — swap X first; a hand-item
click "uses" it on the console and opens nothing).
"""
import re

opts = args or {}
min_dmg = float(opts.get("min_damage", 20))
out = {"crew": [], "verdict": [], "counts": {}}

def close_all():
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        sk.tgui_send(id=m.group(1), type="close")
        time.sleep(0.12)

# 1) find + open the console
cid = opts.get("console")
if cid:
    g = bot.goto(object_id=int(cid))
    if g.failed and "already there" not in (g.text or ""):
        raise SystemExit("walk to console failed: " + (g.text or "")[-100:])
else:
    s = sk.search(query="crew monitoring console", in_view=True, page_size=5)
    m = re.search(r'- obj (\d+) "crew monitoring console" at (\d+),(\d+)', s.text or "")
    if not m:
        raise SystemExit("no crew monitoring console in view — stand in Medbay "
                         "Central or the Bridge")
    cid, cx, cy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    g = bot.goto(x=cx, y=cy + 1)
    if g.failed and "already there" not in (g.text or ""):
        raise SystemExit("walk failed: " + (g.text or "")[-100:])
out["console"] = cid

# empty active hand: CMO spawns with a medkit in hand — a hand-item click
# "uses" it on the console and opens nothing
for _ in range(2):
    inv = sk.inventory().text or ""
    act = [l for l in inv.split("\n") if "active_hand" in l]
    if act and ("empty" in act[0] or "obj" not in act[0]):
        break
    sk.key(key="X")
    time.sleep(0.4)

close_all()
time.sleep(0.4)
sk.click(object_id=int(cid))
time.sleep(1.8)

wid = None
for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
    d = sk.tgui_window(id=m.group(1), max_chars=500).text or ""
    if "closed: true" in d:
        continue
    i = re.search(r"interface: (\S+)", d)
    if i and i.group(1) == "CrewConsole":
        wid = m.group(1)
        break
out["win"] = wid
if not wid:
    out["ok"] = False
    out["note"] = "CrewConsole window did not open (empty active hand? powered?)"
    RESULT = out
else:
    d = sk.tgui_window(id=wid, max_chars=30000).text or ""
    di = d.find('"sensors"')
    data = d[di:] if di > -1 else d
    # split per-entry on "ref": and parse each entry's fields in order
    entries = re.split(r'"ref": "\[mob_\d+\]"', data)[1:]
    for seg in entries:
        nm = re.search(r'"name": "([^"]*)"', seg)
        asg = re.search(r'"assignment": "([^"]*)"', seg)
        ls = re.search(r'"life_status": (\d)', seg)
        hl = re.search(r'"health": (-?[\d.]+)', seg)
        dmg = {}
        for key in ("oxydam", "toxdam", "burndam", "brutedam"):
            mm = re.search(r'"%s": ([\d.]+)' % key, seg)
            dmg[key] = float(mm.group(1)) if mm else None
        ar = re.search(r'"area": "([^"]*)"', seg)
        row = {"name": nm and nm.group(1) or "Unknown",
               "assignment": asg and asg.group(1) or None,
               "life_status": int(ls.group(1)) if ls else None,
               "health": float(hl.group(1)) if hl else None,
               "damage": dmg,
               "area": ar and ar.group(1) or None}
        out["crew"].append(row)
    sk.tgui_send(id=wid, type="close")

    # 2) classify + verdict
    dead = [c for c in out["crew"] if c["life_status"] == 3]
    crit = [c for c in out["crew"]
            if c["life_status"] in (1, 2) or (c["health"] is not None
                                              and c["health"] < 0
                                              and c["health"] > -60)]
    wounded = [c for c in out["crew"]
               if c["life_status"] == 0 and any(
                   (v or 0) >= min_dmg for v in c["damage"].values())]
    broken = [c for c in out["crew"]
              if c["health"] == -50 and c["life_status"] in (0, 1)]
    off = [c for c in out["crew"]
           if c["life_status"] is not None
           and all(v is None for v in c["damage"].values())
           and c["life_status"] != 3]
    out["counts"] = {"total": len(out["crew"]), "dead": len(dead),
                     "critical": len(crit), "wounded": len(wounded),
                     "broken_sensors": len(broken), "binary_only": len(off)}
    for c in dead:
        out["verdict"].append("DEAD: %s (%s)%s" %
                              (c["name"], c["assignment"] or "?",
                               " in " + c["area"] if c["area"] else ""))
    for c in crit:
        out["verdict"].append("CRITICAL: %s health %s%s" %
                              (c["name"], c["health"],
                               " in " + c["area"] if c["area"] else ""))
    for c in wounded:
        w = {k: v for k, v in c["damage"].items() if (v or 0) >= min_dmg}
        out["verdict"].append("WOUNDED: %s %s" % (c["name"], w))
    if off:
        out["verdict"].append("%d crew with binary-only sensors — announce "
                              "suit sensors" % len(off))
    if not out["crew"]:
        out["verdict"].append("no sensor data (console powered? crew on grid?)")
    out["ok"] = True

RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
