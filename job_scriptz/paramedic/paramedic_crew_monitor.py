# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Handheld crew monitor triage â€” the paramedic's pocket version of the CMO's
console. ONE envelope: who is dead, critical or wounded station-wide.

Run: run_script {script: ".../job_scriptz/paramedic/paramedic_crew_monitor.py",
                 args: {"monitor"?: id, "x"?, "y"?, "min_damage"?: 20}}
monitor id optional â€” found on screen (belt overlay `state=crew_monitor`, belt
view opened via the belt HUD if needed; the spawn belt renders it at
4:16,2:16). Works anywhere â€” GLOB.crewmonitor is station-wide.

Flow (verified live): click the belt overlay icon (picks the monitor into the
active hand; empty hand required) -> click it AGAIN in hand (attack_self ->
sensor_device.dm: GLOB.crewmonitor.show) -> interface CrewConsole window ->
parse data.sensors[] exactly like the CMO's crew_monitor.py:
  life_status 0 conscious / 1-2 unconscious-crit / 3 DEAD; health;
  oxydam/toxdam/burndam/brutedam (None = binary-only sensors).
Classifies DEAD / CRITICAL / WOUNDED (>= min_damage) / BROKEN (health -50
garbage) / binary-only. Closes the window and stows the monitor back on the
belt with E afterwards.
"""
import re

opts = args or {}
min_dmg = float(opts.get("min_damage", 20))
out = {"crew": [], "verdict": [], "counts": {}}

if opts.get("x") and opts.get("y"):
    g = bot.goto(x=int(opts["x"]), y=int(opts["y"]), max_steps=80)
    if g.failed and "already there" not in (g.text or ""):
        out["verdict"].append("walk to %s,%s failed â€” scanning anyway" % (opts["x"], opts["y"]))


def close_all():
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        sk.tgui_send(id=m.group(1), type="close")
        time.sleep(0.12)


def empty_active_hand():
    for _ in range(2):
        inv = sk.inventory().text or ""
        act = [l for l in inv.split("\n") if "active_hand" in l]
        if act and ("empty" in act[0] or "obj" not in act[0]):
            return True
        sk.key(key="X")
        time.sleep(0.4)
    return False


def find_monitor_on_screen(sc):
    m = re.search(r'- obj (\d+) "handheld crew monitor" .*?state=crew_monitor', sc)
    return int(m.group(1)) if m else None


# ---- 1) locate the monitor (belt overlay -> open the belt view if hidden)
mid = opts.get("monitor") and int(opts["monitor"])
if not mid:
    sc = sk.screen(page_size=250).text or ""
    mid = find_monitor_on_screen(sc)
    if not mid:
        m = re.search(r'- obj (\d+) "belt" at CENTER', sc)
        if m:
            sk.click(object_id=int(m.group(1)))  # open belt view
            time.sleep(0.6)
            sc = sk.screen(page_size=250).text or ""
            mid = find_monitor_on_screen(sc)
out["monitor"] = mid
if not mid:
    RESULT = {"ok": False, "note": "no handheld crew monitor (belt? NanoMed?)"}
else:
    # ---- 2) into the hand, then attack_self
    empty_active_hand()
    sk.click(object_id=mid)
    time.sleep(0.7)
    inv = sk.inventory().text or ""
    if not re.search(r'active_hand[^\n]*obj %d\b' % mid, inv):
        # not in hand yet (belt view click opened the view instead?) â€” click again
        sk.click(object_id=mid)
        time.sleep(0.7)
    sk.click(object_id=mid)  # in-hand click = attack_self
    time.sleep(1.8)

    # ---- 3) the CrewConsole window
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
        out["note"] = "CrewConsole window did not open (monitor in hand? powered?)"
        RESULT = out
    else:
        d = sk.tgui_window(id=wid, max_chars=30000).text or ""
        di = d.find('"sensors"')
        data = d[di:] if di > -1 else d
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
            out["crew"].append({"name": nm and nm.group(1) or "Unknown",
                                "assignment": asg and asg.group(1) or None,
                                "life_status": int(ls.group(1)) if ls else None,
                                "health": float(hl.group(1)) if hl else None,
                                "damage": dmg,
                                "area": ar and ar.group(1) or None})
        sk.tgui_send(id=wid, type="close")

        # ---- 4) classify + verdict (same rules as CMO crew_monitor.py)
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
            out["verdict"].append("DEAD: %s (%s)%s â€” bring the body to medbay "
                                  "(formaldehyde if unrecoverable)" %
                                  (c["name"], c["assignment"] or "?",
                                   " in " + c["area"] if c["area"] else ""))
        for c in crit:
            out["verdict"].append("CRITICAL: %s health %s%s â€” roller bed + defib" %
                                  (c["name"], c["health"],
                                   " in " + c["area"] if c["area"] else ""))
        for c in wounded:
            w = {k: v for k, v in c["damage"].items() if (v or 0) >= min_dmg}
            out["verdict"].append("WOUNDED: %s %s" % (c["name"], w))
        if off:
            out["verdict"].append("%d crew with binary-only sensors â€” "
                                  "announce suit sensors" % len(off))
        if not out["crew"]:
            out["verdict"].append("no sensor data (crew with sensors off?)")
        out["ok"] = True
        # ---- 5) stow the monitor back on the belt
        sk.key(key="E")
        time.sleep(0.6)

RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
