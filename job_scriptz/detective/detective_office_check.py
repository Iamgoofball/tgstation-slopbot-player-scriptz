# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'),
          encoding='utf-8').read())
precheck()
"""One-envelope Detective's Office survey (READ-ONLY): the detective's
cabinet (state + contents), the filing cabinet, the security + medical
records consoles, the camera monitor + office shutters control, and what
the backpack kit holds.

Run: run_script {script: ".../job_scriptz/detective/detective_office_check.py",
                 args: {"no_walk"?: true,     # skip all walking
                        "door_x"?/door_y?: tile,  # nook door override
                        "say"?: true}}        # :s check-in at the end
MetaStation Detective's Office (map coords, find machines by NAME - ids
re-roll): public room x=119-126 y=157-163 - office chair (123,162), work
tables (122,162)/(122,163) + (124,163), security records console (124,162),
medical records console (124,161), camera monitor + office shutters control
(124,163), private nook behind the INTERIOR DOOR: filing cabinet +
detective's cabinet in a row just south of it.

Fork truths (live-verified):
  - **The dark nook is invisible to SEARCH** (the known index forgets dark
    /out-of-sight things within minutes) but `sk.tile(x, y, all=True)`
    still reports REMEMBERED contents there. So: anchor the walk on the
    records console (searchable), reach the nook door by MetaStation
    geometry (4W 3N of the console), then find the cabinets by TILE READ.
  - The nook door (an "interior door") bump-opens; stand ON its tile.
  - The cabinet opens like a locker: 1st click UNLOCK, 2nd OPEN; RMB = lock.
  - Dark tiles: clicks STILL LAND (take/scan work; reading windows warns
    "too dark to read!" but the window still opens).
  - Detective spawn kit: black gloves, trenchcoat, fedora, hard-worn suit,
    loose tie, chalk, Zippo, bowman headset, mindshield, PDA/ID, and INSIDE
    the backpack: a spare forensic scanner, a police baton, evidence bag
    box + bags.
  - Records console reuse: security-officer/sec_records_control.py (pass
    console=<found id> x=<x> y=<y>); medical records: coroner/
    medical_records.py (pass laptop=<found id>).
"""
import re

opts = args or {}
out = {"consoles": {}, "verdict": []}


def norm(t):
    return (t or "").replace("\\n", "\n")


def read_status():
    time.sleep(0.8)
    return norm(sk.status().text or "")


def active_obj():
    for l in norm(sk.inventory().text or "").split("\n"):
        if "lhandactive" in l:
            m = re.match(r"- obj (\d+)", l.strip())
            if m:
                return int(m.group(1))
    return None


def empty_active_hand():
    if active_obj() is None:
        return
    sk.key(key="X")
    time.sleep(0.5)
    if active_obj() is not None:
        sk.key(key="Q")
        time.sleep(0.6)


def find_named(q, pat, area_pat=None):
    s = norm(sk.search(query=q, kind="obj", page_size=8).text or "")
    for l in s.split("\n"):
        m = re.match(r"- obj (\d+) \"([^\"]*)\" at (\d+),(\d+)", l.strip())
        if m and re.search(pat, m.group(2), re.I) and \
                "left the view" not in l:
            if area_pat and not re.search(area_pat, l, re.I):
                continue
            return {"id": int(m.group(1)), "name": m.group(2),
                    "x": int(m.group(3)), "y": int(m.group(4)),
                    "line": l.strip()[:150]}
    return None


def tile_objs(x, y, limit=12):
    t = norm(sk.tile(x, y, all=True).text or "")
    rows = []
    for l in t.split("\n"):
        m = re.match(r"- (obj|mob) (\d+) \"([^\"]*)\"", l.strip())
        if m:
            rows.append({"kind": m.group(1), "id": int(m.group(2)),
                         "name": m.group(3), "dark": "in the dark" in l})
    return rows[:limit]


# ---- staged walk: public room (records console, searchable) -> the dark
# nook via the interior door (MetaStation geometry: the nook door sits 4W
# 3N of the records console; args door_x/door_y override) -> cabinet row
rec = find_named("security records console", r"security records",
                 area_pat=r"Detective's Office")
cab = None
if not opts.get("no_walk"):
    empty_active_hand()
    if rec:
        g = bot.goto(x=rec["x"] - 1, y=rec["y"], max_steps=60)
        out["walk_public"] = "arrived" in (g.text or "")
        dx_ = opts.get("door_x", rec["x"] - 4)
        dy_ = opts.get("door_y", rec["y"] - 3)
        g = bot.goto(x=dx_, y=dy_, max_steps=40)
        out["walk_door"] = "arrived" in (g.text or "")
        time.sleep(0.8)
        for (cx, cy) in ((dx_ + 1, dy_ - 1), (dx_, dy_ - 1),
                         (dx_ + 1, dy_ - 2), (dx_, dy_ - 2)):
            for row in tile_objs(cx, cy):
                if re.search(r"detective's cabinet", row["name"], re.I) \
                        and not cab:
                    cab = {"id": row["id"], "name": row["name"],
                           "x": cx, "y": cy}
                elif re.search(r"filing cabinet", row["name"], re.I) and \
                        "filing_cabinet" not in out["consoles"]:
                    out["consoles"]["filing_cabinet"] = {
                        "id": row["id"], "name": row["name"],
                        "x": cx, "y": cy,
                        "line": "(dark nook - found by tile read)"}
    if cab:
        g = bot.goto(x=cab["x"], y=cab["y"] + 1, max_steps=30)
        out["walk_nook"] = "arrived" in (g.text or "")
    out["walk"] = bool(out.get("walk_nook") or out.get("walk_public"))
else:
    out["walk"] = "skipped"
if not cab:
    out["verdict"].append("no detective's cabinet located (walk to the "
                          "office first; the dark nook is invisible to "
                          "search - tile reads find it)")

# ---- 1) the detective's cabinet: state + contents
if cab:
    out["cabinet"] = {"id": cab["id"], "x": cab["x"], "y": cab["y"]}
    t = norm(sk.tile(cab["x"], cab["y"], all=True).text or "")
    line = ""
    for l in t.split("\n"):
        if ("obj %d " % cab["id"]) in l:
            line = l.strip()
    out["cabinet"]["open"] = "cabinet_open" in line
    out["cabinet"]["locked"] = "[locked]" in line
    kit = [r for r in tile_objs(cab["x"], cab["y"])
           if r["id"] != cab["id"]]
    out["cabinet"]["contents"] = [r["name"] for r in kit]
    out["verdict"].append("cabinet %s: %s"
                          % ("open" if out["cabinet"]["open"] else
                             ("locked" if out["cabinet"]["locked"] else
                              "closed+unlocked"),
                          ", ".join(r["name"] for r in kit[:8]) or "empty"))
    if not out["cabinet"]["open"] and out.get("walk_nook"):
        empty_active_hand()
        sk.click(object_id=cab["id"])   # unlock
        time.sleep(1.2)
        sk.click(object_id=cab["id"])   # open
        time.sleep(1.2)
        kit = [r for r in tile_objs(cab["x"], cab["y"])
               if r["id"] != cab["id"]]
        out["cabinet"]["contents"] = [r["name"] for r in kit]
        out["cabinet"]["open"] = True
    if out["cabinet"]["open"] and out.get("walk_nook"):
        # tidy: close the cabinet again (leave the nook as found)
        empty_active_hand()
        sk.click(object_id=cab["id"])
        time.sleep(1.2)
        out["cabinet"]["open"] = False

# ---- 2) consoles + monitor + shutters control (locate + state, office
# area only so the Law Office's twin cabinets don't match)
for key, q, pat in (("security_records", "security records console",
                     r"security records"),
                    ("medical_records", "medical records console",
                     r"medical records"),
                    ("camera_monitor", "security camera monitor",
                     r"camera monitor"),
                    ("shutters_control", "detective's office shutters",
                     r"shutters control"),
                    ("filing_cabinet", "filing cabinet", r"filing cabinet")):
    f = find_named(q, pat, area_pat=r"Detective's Office")
    if f:
        out["consoles"][key] = f
    else:
        out["verdict"].append("no %s found in view" % key)

# ---- 3) my kit (worn + hand; backpack contents need the panel open)
inv = norm(sk.inventory().text or "")
out["kit"] = {
    "black_gloves_worn": "black gloves" in inv,
    "scanner": len(re.findall(r"forensic scanner", inv)),
    "scanner_note": "count of 'forensic scanner' lines in inventory "
                    "(hand + panel-open backpack)",
}

# ---- radio check-in
if opts.get("say", True):
    try:
        sk.say(text="Detective on shift. Office checked, scanner ready.",
               radio="security")
        time.sleep(0.6)
        out["said"] = True
    except Exception as exc:
        out["verdict"].append("radio say failed: %s" % exc)

RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
