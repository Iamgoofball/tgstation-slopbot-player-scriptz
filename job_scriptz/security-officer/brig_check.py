# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'),
          encoding='utf-8').read())
precheck()
"""One-envelope security wing survey (READ-ONLY): the three cells with their
door timers, lockers and beds, the cell flashers, the holding cell, Brig
Control (records/camera/prisoner-management consoles, lockdown buttons,
warden's locker), the Security Office (records + camera consoles, department
techfab (Security)), Beepsky's last-known position, and any prisoners.

Run: run_script {script: ".../job_scriptz/security-officer/brig_check.py",
                 args: {"no_walk"?: true,        # known-index only, no walking
                        "x"?/y?: walk target fallback,
                        "say"?: true}}
MetaStation wing layout (verified this round): brig corridor y=166-169
x=95-116; cells south of it (cell interiors y=161-164); cell door timers =
wall displays named "Cell 2" (22173 at 101,165) and "Cell 3" (22651 at
103,165), "Cell 1" is the far-west cell (its locker 20908 at 97,162); flasher
buttons "Brig Entrance Flasher" (25314) + "Holding Cell Flasher" (25315) both
at (113,165); Brig Control x=105-110 (security records console 23971 at
108,163, security camera console 23973 at 108,162, prisoner management
console 23959 at 108,165, warden's locker 23163, Brig Lockdown Control /
Prison Wing Lockdown buttons); Security Office x=116-122 (records console
27423 at 121,169, camera console 27162 at 120,169, department techfab
(Security) 26728 at 118,169); Beepsky patrols (may be anywhere - reported
with staleness). McGriff the pug lives in Brig Control.

Fork truths:
  - The wing is WALKABLE from the Security Locker Room (no firelocks inside,
    unlike the central hallway this round) - walk_to(area="Brig") works.
  - Cell timers are found by their display name ("Cell 2"), not "timer".
"""
import re

opts = args or {}
out = {"cells": {}, "consoles": {}, "verdict": []}


def find_all(q, kind=None, page_size=20):
    try:
        s = sk.search(query=q, kind=kind, page_size=page_size).text or ""
    except Exception:
        return []
    rows = []
    for l in s.split("\n"):
        base = re.match(r"- (obj|mob) (\d+) \"([^\"]*)\"", l.strip())
        if not base:
            continue
        row = {"kind": base.group(1), "id": int(base.group(2)),
               "name": base.group(3)}
        am = re.search(r"\bat [^ ]+ in (?:area )?\"?([A-Za-z][A-Za-z' &-]*)",
                       l)
        row["area"] = am.group(1).strip() if am else None
        sm = re.search(r"\bat (\d+),(\d+)", l)
        if sm:
            row["x"], row["y"] = int(sm.group(1)), int(sm.group(2))
        stale = re.search(r"last seen here (\d+) s ago", l)
        row["stale_s"] = int(stale.group(1)) if stale else 0
        if "left the view" in l:
            row["stale_s"] = row["stale_s"] or 9999
        rows.append(row)
    return rows


# ---- 1) machines + robots via the known index
out["consoles"]["security_records"] = find_all("security records console",
                                               "obj")[:6]
out["consoles"]["camera"] = find_all("security camera console", "obj")[:6]
out["consoles"]["prisoner_management"] = find_all("prisoner management",
                                                  "obj")[:4]
out["consoles"]["techfab_sec"] = find_all("department techfab", "obj")
timers = find_all("Cell", "obj")
out["cells"]["timers"] = [t for t in timers
                          if re.match(r"Cell \d+$", t["name"])]
out["cells"]["lockers"] = [t for t in find_all("Cell", "obj")
                           if "locker" in t["name"]]
out["flashers"] = [t for t in find_all("Flasher", "obj")
                   if "flasher" in t["name"].lower()]
beep = find_all("Beepsky")
out["beepsky"] = beep[0] if beep else None
if out["beepsky"] and out["beepsky"].get("stale_s", 0) and \
        out["beepsky"]["stale_s"] > 300:
    out["verdict"].append("Beepsky not seen for %ss (last known %s) - not "
                          "patrolling near the brig"
                          % (out["beepsky"]["stale_s"],
                             out["beepsky"].get("area") or "?"))
if not out["cells"]["timers"]:
    out["verdict"].append("no cell door timers found - walk the corridor "
                          "in view of the cells first")

# ---- 2) walk the corridor + read the cells in view
if not opts.get("no_walk"):
    # walk anchor = a cell door timer found by NAME (ids re-roll every
    # round): timers are WALL displays, so stand in the corridor a few
    # tiles north of one - never inside the staff-only Brig Control
    anchor = None
    for t in out["cells"]["timers"]:
        if t.get("x") and not t.get("stale_s"):
            anchor = t
            break
    if anchor:
        g = bot.goto(x=anchor["x"], y=anchor["y"] + 3, max_steps=120)
        out["walk_brig"] = "arrived" in (g.text or "")
    elif opts.get("x") and opts.get("y"):
        g = sk.walk_to(x=opts["x"], y=opts["y"], max_steps=120)
        out["walk_brig"] = "arrived" in (g.text or "")
    else:
        out["verdict"].append("no in-view cell timer anchor - pass args x/y "
                              "or set no_walk")
    lk = sk.look(radius=10).text or ""
    out["in_view_cells"] = [l.strip()[:120] for l in lk.split("\n")
                            if re.search(r'"Cell \d|cell door|Cell \d locker',
                                         l) and l.strip().startswith("- ")]
    # any prisoner mobs in the wing areas? (exclude by the status mob id -
    # _my_name() alone can misfire after a reconnect)
    st_me = sk.status().text or ""
    mid = re.search(r"you: mob (\d+)", st_me)
    mid = mid.group(1) if mid else None
    mobs = [m for m in find_all("", "mob", page_size=30)
            if str(m["id"]) != mid and m["name"] != _my_name()]
    wing = [m for m in mobs if any(
        (m.get("area") or "").startswith(w)
        for w in ("Brig", "Holding Cell", "Prison", "Security Office"))]
    out["mobs_in_wing"] = wing
    if wing:
        out["verdict"].append("mobs in the security wing: %s"
                              % ", ".join("%s (%s)" % (m["name"], m["area"])
                                          for m in wing[:5]))
    else:
        out["verdict"].append("no mobs in the wing - cells are empty")
    # examine one timer (read-only) for its state line
    if out["cells"]["timers"]:
        tm = out["cells"]["timers"][0]
        e = sk.examine(object_id=tm["id"]).text or ""
        out["timer_examine"] = e[:300]

# ---- 3) verdicts on the essentials
for key, label in (("security_records", "security records console"),
                   ("camera", "camera console"),
                   ("prisoner_management", "prisoner management console")):
    if not out["consoles"].get(key):
        out["verdict"].append("no %s found" % label)
if not out["consoles"].get("techfab_sec"):
    out["verdict"].append("no department techfab (Security) found")

if opts.get("say", True):
    try:
        n = len(out.get("mobs_in_wing") or [])
        sk.say(text="Brig check: %d in the wing, consoles + timers %s."
               % (n, "OK" if out["cells"]["timers"] else "MISSING"),
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
