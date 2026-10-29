# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""One-envelope ROBOTICS LAB + MECH BAY survey (read-only): exosuit
fabricators (materials / queue / processing via their tgui), recharging
stations, mech bay power control, cell chargers, cyborg shells + MMIs +
mechs in view. Verdicts tell you what the shift needs.

Run: run_script {script: ".../job_scriptz/roboticist/robotics_lab_check.py",
                 args: {"fabs"?: true,       # limit to the fabricators
                        "no_walk"?: true}}   # survey from where you stand
Stand in/near the Robotics Lab (MetaStation: fabs at (110,95) + (110,93),
Mech Bay east of it) or pass no_walk to skip the adjacency walk.

Fork truths (live-verified):
  - The fab tgui (interface ExosuitFabricator) lists data.materials[] with
    per-material amounts - the amounts come from the STATION ORE SILO (a
    material insert says "N sheets were added to the ore silo"; all fabs
    share it). queue[] has jobId/designPath/processing/timeLeft (deciseconds).
  - Opening a fab (or ANY machine tgui) needs an EMPTY active hand - a held
    item attackbys instead (with sheets that INSERTS them; recorded + warned).
  - recharging station icon_state borgchargerN; examine when occupied shows
    the occupant; mech bay power console (MechBayPowerConsole) shows
    data.recharge_port.mech (null = no mech docked, action "reconnect").
  - Prints eject onto the fab tile or a NEIGHBOR (borg head landed at
    (111,95) for the fab at (110,95)).
"""
import re

opts = args or {}
out = {"fabs": [], "chargers": [], "cell_chargers": [], "mech_power": None,
       "shells": [], "verdict": []}


def active_obj():
    inv = sk.inventory().text or ""
    m = re.search(r"active_hand[^\n]*obj (\d+)", inv)
    return int(m.group(1)) if m else None


def empty_active_hand():
    dropped = []
    for attempt in range(3):
        inv = sk.inventory().text or ""
        act = [l for l in inv.split("\n") if "active_hand" in l]
        if act and ("empty" in act[0] or "obj" not in act[0]):
            if dropped:
                out["verdict"].append("dropped to free the active hand: %s "
                                      "(pick them back up later!)" % dropped)
            return dropped
        if attempt == 0:
            sk.key(key="X")
            time.sleep(0.4)
        else:
            m = re.search(r"active_hand[^\n]*obj (\d+)", inv)
            if m:
                sk.key(key="Q")
                time.sleep(0.5)
                dropped.append(int(m.group(1)))
    out["verdict"].append("could not free the active hand")
    return dropped


def search_objs(q, in_view=True, limit=100):
    s = sk.search(query=q, in_view=in_view, page_size=limit).text or ""
    rows = []
    for line in s.split("\n"):
        m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+).*?state=([\w-]+)', line.strip())
        if m:
            rows.append({"id": int(m.group(1)), "name": m.group(2),
                         "x": int(m.group(3)), "y": int(m.group(4)),
                         "state": m.group(5),
                         "stale": "left the view" in line or "last seen" in line})
    return rows


def walk_to_known(obj_q, area_q, limit=20):
    """Coords from the known index -> goto; on 'no known path' fall back to
    the loaded map's area names (search kind=area). Returns True if moved."""
    rows = search_objs(obj_q, in_view=False, limit=limit)
    if not rows:
        return False
    empty_active_hand()
    g = bot.goto(x=rows[0]["x"], y=rows[0]["y"], max_steps=60)
    if "arrived" in (g.text or ""):
        return True
    sa = sk.search(query=area_q, kind="area", page_size=20).text or ""
    marea = re.search(r'area "([^"]*%s[^"]*)"' % re.escape(area_q.split()[0]),
                      sa, re.I)
    if marea:
        g2 = sk.walk_to(area=marea.group(1), max_steps=120)
        return "arrived" in (g2.text or "") or "already" in (g2.text or "")
    return False


def fab_window(want_open=True):
    w = sk.tgui_windows(all=True).text or ""
    for mm in re.finditer(r"(  (tgui-window-\d+):\n(?:(?:    [^\n]*)\n)+)", w):
        blk = mm.group(1)
        if "ExosuitFabricator" in blk and ("closed: true" not in blk) == want_open:
            return mm.group(2)
    return None


# ---- 1. exosuit fabricators (walk to them first if out of view)
fab_rows = search_objs("exosuit fabricator", limit=60)
if not fab_rows and not opts.get("no_walk"):
    walk_to_known("exosuit fabricator", "robotics")
    fab_rows = search_objs("exosuit fabricator", limit=60)
for r in fab_rows:
    f = dict(r, meaning={})
    if r["stale"]:
        out["fabs"].append(dict(f, note="not in view (stale line) - walk closer"))
        continue
    if not opts.get("no_walk"):
        empty_active_hand()
        # fab tile is DENSE: goto parks on a neighboring tile
        g = bot.goto(x=r["x"], y=r["y"], max_steps=40)
        f["walk"] = "arrived" in (g.text or "")
        c = sk.click(object_id=r["id"])
        time.sleep(2.0)
    wid = fab_window(True)
    if not wid:
        f["meaning"]["error"] = "fab window did not open (unpowered? blocked?)"
        out["fabs"].append(f)
        continue
    d = sk.tgui_window(id=wid, max_chars=6000).text or ""
    mats = {}
    for mm in re.finditer(r'"name": "([^"]+)",\s*"ref": "[^"]*",\s*"amount": (\d+)', d):
        if int(mm.group(2)) > 0:
            mats[mm.group(1)] = int(mm.group(2))
    f["materials"] = mats
    qm = re.search(r'"queue": (\[[^\]]*\])', d, re.S)
    jobs = []
    if qm and qm.group(1).strip() != "[]":
        for jm in re.finditer(r'"designPath": "([^"]+)"[^}]*?"timeLeft": (\d+)', qm.group(1)):
            jobs.append({"design": jm.group(1), "timeLeft": int(jm.group(2))})
    f["queue"] = jobs
    pm = re.search(r'"processing": (\d+)', d)
    f["processing"] = bool(pm and int(pm.group(1)))
    try:
        sk.tgui_send(id=wid, type="close")
    except Exception:
        pass
    out["fabs"].append(f)

# ---- 2. recharging stations (cyborg chargers): they live in the Mech Bay,
# out of view from the fabs - walk there via the known index / area fallback
charger_rows = search_objs("recharging station", limit=40)
if not charger_rows and not opts.get("no_walk"):
    walk_to_known("recharging station", "mech bay")
    charger_rows = search_objs("recharging station", limit=40)
for r in charger_rows:
    if r["stale"]:
        continue
    e = sk.examine(object_id=r["id"]).text or ""
    r2 = dict(r)
    r2["examine_head"] = (e.split("\n")[1] if len(e.split("\n")) > 1 else "")[:120]
    r2["occupied"] = bool(re.search(r"cyborg|MODsuit|ethereal", e)) and \
        not re.search(r"like cyborgs", e)
    out["chargers"].append(r2)
for r in search_objs("cell charger", limit=40):
    if not r["stale"]:
        out["cell_chargers"].append(r)

# ---- 4. mech bay power control console (same out-of-view dance)
console_rows = search_objs("mech bay power control console", limit=20)
if not console_rows and not opts.get("no_walk"):
    walk_to_known("mech bay power control console", "mech bay")
    console_rows = search_objs("mech bay power control console", limit=20)
for r in console_rows:
    if r["stale"]:
        continue
    empty_active_hand()
    # console tile is DENSE: goto parks on a neighboring tile
    g = bot.goto(x=r["x"], y=r["y"], max_steps=40)
    sk.click(object_id=r["id"])
    time.sleep(2.0)
    w = sk.tgui_windows(all=True).text or ""
    for mm in re.finditer(r"(  (tgui-window-\d+):\n(?:(?:    [^\n]*)\n)+)", w):
        blk = mm.group(1)
        if "MechBayPowerConsole" in blk and "closed: true" not in blk:
            d = sk.tgui_window(id=mm.group(2), max_chars=3000).text or ""
            mech = re.search(r'"mech": (null|"[^"]*")', d)
            out["mech_power"] = {"console": r["id"],
                                 "docked_mech": mech and mech.group(1)}
            try:
                sk.tgui_send(id=mm.group(2), type="close")
            except Exception:
                pass

# ---- 5. shells / MMIs / mechs in view (tight filters: "mechanical toolbox"
# must NOT count as a mech; Ripley boards are not mechs either). The console
# dance may have left us in the Mech Bay - walk back to the lab first.
if not opts.get("no_walk"):
    walk_to_known("exosuit fabricator", "robotics")
for q, kind, include, exclude in (
        ("cyborg endoskeleton", "endoskeleton", r"cyborg endoskeleton", None),
        ("interface", "MMI", r"MMI|Man-Machine Interface", None),
        ("mech", "mech", r"Ripley|Odysseus|Gygax|Durand|Phazon",
         r"board|module|console|control")):
    for r in search_objs(q, limit=60):
        if r["stale"]:
            continue
        if not re.search(include, r["name"], re.I):
            continue
        if exclude and re.search(exclude, r["name"], re.I):
            continue
        out["shells"].append({"kind": kind, "id": r["id"], "name": r["name"],
                              "x": r["x"], "y": r["y"], "state": r["state"]})
s = sk.search(query="", kind="mob", in_view=True, page_size=60).text or ""
for line in s.split("\n"):
    if re.search(r"cyborg|borg|Silicon", line.strip()) and line.strip().startswith("- mob"):
        out["shells"].append({"kind": "cyborg", "line": line.strip()[:140]})

# ---- verdicts
for f in out["fabs"]:
    if f.get("meaning", {}).get("error"):
        out["verdict"].append("fab %s: window did not open (power?)" % f["id"])
    elif not f.get("materials"):
        out["verdict"].append("fab %s (%s,%s): NO materials - load metal/glass "
                              "sheets" % (f["id"], f["x"], f["y"]))
    if f.get("queue"):
        out["verdict"].append("fab %s: queue %d job(s), %s"
                              % (f["id"], len(f["queue"]),
                                 f["queue"][0]["design"].split("/")[-1]))
if out["fabs"] and not any(f.get("materials") for f in out["fabs"]):
    out["verdict"].append("no fab has materials - a cyborg build cannot start")
if not out["shells"]:
    out["verdict"].append("no endoskeleton / MMI / mech in view - print parts "
                          "and build a shell (keep one shell on standby)")
for c in out["chargers"]:
    if c.get("state") == "borgcharger0":
        pass  # empty charger is normal
if out["mech_power"] and out["mech_power"]["docked_mech"] in (None, "null"):
    out["verdict"].append("mech bay: no mech docked on the recharge port")
RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
