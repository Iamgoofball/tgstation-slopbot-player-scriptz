# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Unbuckle from the arrival seat, leave the shuttle, walk to a target area.

Run: run_script {script: ".../lifecycle/arrival_goto.py",
                 args: {"target": ["Medbay Central", "Medical Lobby"]}}
target: list of area names, tried in order (use 1-2 aliases of the room).
Optional: {"exit": ["Arrivals", "Central Primary Hallway"]} (default),
{"unbuckle": false} to skip the seat click, {"attempts": 4}, {"wait_s": 15}.
Guards: only clicks the seat when the Buckled alert is actually up (an empty
seat under an empty hand would sit us back down); retries while the shuttle
is still flying. Idempotent: works when already unbuckled/on-station.
"""
import re

opts = args or {}
target = opts.get("target") or ValueError("args: {'target': ['Area Name']}")
exit_names = opts.get("exit") or ["Arrivals", "Arrival Shuttle Hallway",
                                  "Central Primary Hallway"]
attempts = int(opts.get("attempts", 4))
wait_s = int(opts.get("wait_s", 15))
THING_RE = re.compile(r'^(mob|obj|turf|area)\s+(\d+)\s+"([^"]*)"')

def parse_thing(line):
    m = THING_RE.match(str(line).strip())
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (None, None, None)

def try_area(names, tries=attempts, gap=wait_s):
    last = None
    for name in names:
        for i in range(tries):
            ans = bot.goto_area(name)
            if not ans.failed:
                return name, ans
            last = ans
            print("goto_area %r failed (attempt %d): %s"
                  % (name, i + 1, (ans.text or "")[-90:]))
            sk.wait(gap)
    return None, last

def unbuckle():
    st = sk.status()
    buckled = "buckled" in (sk.screen().text or "").lower()
    info = {"was_buckled": buckled, "clicked": None}
    if not buckled:
        return info
    m = re.search(r"at (\d+),(\d+),(\d+)", st.get("you") or "")
    if not m:
        return dict(info, clicked="no position parse")
    x, y, z = int(m.group(1)), int(m.group(2)), int(m.group(3))
    seat = None
    for line in sk.tile(x, y).first_list():
        kind, tid, name = parse_thing(line)
        if kind == "obj" and re.search(r"seat|chair", name or "", re.I):
            seat = (kind, tid, name)
            break
    if seat is None:
        for line in bot.find("seat").first_list():
            kind, tid, name = parse_thing(line)
            if kind == "obj" and name:
                seat = (kind, tid, name)
                break
    info["seat"] = seat and "%s %d %r" % seat
    if seat is None:
        info["clicked"] = "no seat found"
        return info
    c = bot.click_thing(seat[1], kind=seat[0], expect_name=seat[2])
    info["clicked"] = (c.text or "")[:120]
    time.sleep(0.6)
    info["unbuckled"] = "buckled" not in (sk.screen().text or "").lower()
    return info

out = {}
if opts.get("unbuckle", True):
    watch("before unbuckle")
    out["unbuckle"] = unbuckle()
watch("before exit")
out["exit_area"], out["exit_ans"] = try_area(exit_names)
watch("before target")
out["target_area"], out["target_ans"] = try_area(list(target), tries=2, gap=8)
st2 = sk.status()
out["after"] = st2.get("you")
out["ok"] = bool(out["target_area"])
RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
