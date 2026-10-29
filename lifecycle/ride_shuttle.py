# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Unbuckle and ride the arrival shuttle to the station, then optionally walk
to a target area. Run right after lifecycle/join_as_job.py (you spawn
buckled on the shuttle, z != station z while in transit).

Run: run_script {script: ".../lifecycle/ride_shuttle.py",
                 args: {"goto_area"?: "Security Locker Room",
                        "station_z"?: 2,          # the main station z level
                        "max_wait_s"?: 420}}      # dock wait budget
Dock detection is movement-free: the mob's z changes to the station z when
the shuttle docks. The transient "Weightless" alert during transit is STALE
noise - ignore it (never click "Succumb", that is suicide).

Fork truths (live-verified):
  - Clicking your OWN mob unbuckles the arrival chair ("You unbuckle...").
  - The shuttle docks within ~1-2 min of joining; walk_to during transit
    only wastes attempts (the precheck can abort on the Weightless danger).
"""
import re

opts = args or {}
station_z = int(opts.get("station_z") or 2)
max_wait = int(opts.get("max_wait_s") or 420)
out = {"verdict": []}


def mob_and_z():
    st = sk.status().text or ""
    m = re.search(r"you: mob (\d+) .*?at (\d+),(\d+),(\d+)", st)
    return (int(m.group(1)), int(m.group(4))) if m else (None, None)


def unbuckle(mid):
    # click own mob = unbuckle; fall back to the pending Buckled alert
    try:
        sk.click(object_id=mid)
        time.sleep(1.0)
        st = sk.status().text or ""
        if "Buckled" not in st:
            return True
    except Exception:
        pass
    try:
        sk.answer_alert()
        time.sleep(1.0)
    except Exception:
        pass
    st = sk.status().text or ""
    out["buckled_alert_gone"] = "Buckled" not in st
    return "Buckled" not in st


mid, z = mob_and_z()
out["mob"], out["z_at_start"] = mid, z
if mid is None:
    RESULT = {"ok": False, "note": "could not read the mob id from status"}
elif z != station_z:
    out["unbuckled"] = unbuckle(mid)
    deadline = max_wait
    while deadline > 0 and z != station_z:
        time.sleep(10)
        deadline -= 10
        mid, z = mob_and_z()
    out["z_after_wait"] = z
    out["docked"] = z == station_z
    if not out["docked"]:
        out["verdict"].append("shuttle did not dock within %ss - still at "
                              "z=%s" % (max_wait, z))
else:
    out["docked"] = True   # already on the station

target = opts.get("goto_area")
if out["docked"] and target:
    for attempt in range(3):
        g = sk.walk_to(area=target, max_steps=150)
        t = g.text or ""
        out.setdefault("walk", []).append(
            re.search(r"result: [^|\n]*", t) and
            re.search(r"result: [^|\n]*", t).group(0)[:80])
        if "arrived" in t or "already" in t:
            out["ok"] = True
            break
        time.sleep(4)
    else:
        out["verdict"].append("walk to %r did not arrive - check the map "
                              "is loaded (setup/load_map.py)" % target)

if "RESULT" not in dir():
    RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
