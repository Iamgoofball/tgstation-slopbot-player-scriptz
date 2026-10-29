# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Control one air alarm: unlock, set mode, set vent pressure. State-checked.

Run: run_script {script: ".../job_scriptz/atmospheric-technician/air_alarm_mode.py",
                 args: {"alarm": <obj id>, "mode"?: "panic_siphon", ...}}
modes (this fork, prefix /datum/air_alarm_mode/): filtering, contaminated,
draught, refill, cycle, siphon, panic_siphon, off, flood, vent_siphon.
Optional: {"vent_pressure": kPa} (set_external_pressure on every vent),
{"vent_power": 0|1}, {"scrub_power": 0|1}, {"panic": true} (shortcut for
panic_siphon), {"lock_after": false} (default false).
Flow (proven on Gas Storage alarm 37187): RMB-click with the ID WORN unlocks
(locked 1 -> 0; the vents/scrubbers lists ONLY appear when unlocked). Actions:
mode {mode: full path string}, power/direction/excheck/set_external_pressure
{ref, ...} where ref = the refID string from data.vents[]/scrubbers[].
Verify via data.selectedModePath and per-vent "external".
HAZARD: do NOT send reset_external_pressure "to restore 101" — in this fork
it UNBINDS the vent (external → 5066 = max flow, the room overpressurizes).
To restore the default bound, re-apply a mode (filtering sets 101.325 +
extdefault 1) or send set_external_pressure {ref, value: 101.325}.
"""
import re

MODES = ("filtering", "contaminated", "draught", "refill", "cycle",
         "siphon", "panic_siphon", "off", "flood", "vent_siphon")

opts = args or {}
aid = opts.get("alarm")
if not aid:
    raise ValueError("args: {'alarm': obj_id, 'mode'?: name, 'vent_pressure'?: kPa, ...}")
out = {"alarm": aid, "actions": []}

def close_all():
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        sk.tgui_send(id=m.group(1), type="close")
        time.sleep(0.1)

def find_window():
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        b = sk.tgui_window(id=m.group(1), max_chars=300).text or ""
        if "closed: true" in b:
            continue
        i = re.search(r"interface: (\S+)", b)
        if i and i.group(1) == "AirAlarm":
            return m.group(1)
    return None

def read_state(wid):
    d = sk.tgui_window(id=wid, max_chars=30000).text or ""
    di = d.find('"data"')
    data = d[di:] if di > -1 else d
    lk = re.search(r'"locked": (\d)', data)
    sm = re.search(r'"selectedModePath": "([^"]+)"', data)
    vents = [{"ref": m.group(1), "power": int(m.group(2)), "external": float(m.group(3))}
             for m in re.finditer(r'"refID": "(\[0x[0-9a-f]+\])[\s\S]{0,600}?"power": (\d)[\s\S]{0,400}?"external": ([\d.]+)', data)]
    scrubs = len(re.findall(r'"refID": "\[0x', data[data.find('"scrubbers"'):])) if '"scrubbers"' in data else 0
    env = dict(re.findall(r'"name": "(\w+)",\s*\n\s*"value": "([^"]{1,40})"', data))
    return {"locked": int(lk.group(1)) if lk else None,
            "mode": (sm.group(1).rsplit("/", 1)[-1] if sm else None),
            "vents": vents, "n_scrubbers": scrubs, "env": env}

g = bot.goto(object_id=int(aid))
if g.failed and "already there" not in (g.text or ""):
    raise SystemExit("walk failed: " + (g.text or "")[-100:])
close_all()
sk.click(object_id=int(aid))
time.sleep(1.5)
wid = find_window()
out["win"] = wid
if not wid:
    out["ok"] = False
    out["note"] = "AirAlarm window did not open (empty active hand?)"
    RESULT = out
else:
    s0 = read_state(wid)
    out["before"] = {"locked": s0["locked"], "mode": s0["mode"],
                     "env": s0["env"], "n_vents": len(s0["vents"]),
                     "n_scrubbers": s0["n_scrubbers"]}
    if s0["locked"]:
        sk.click(object_id=int(aid), right=True)   # ID worn: RMB = unlock
        time.sleep(0.8)
        s0 = read_state(wid)
        out["unlocked"] = not s0["locked"]
    if s0["locked"]:
        out["ok"] = False
        out["note"] = "still locked — RMB with ID worn didn't unlock"
        sk.tgui_send(id=wid, type="close")
        RESULT = out
    else:
        goal_mode = None
        if opts.get("panic"):
            goal_mode = "panic_siphon"
        elif opts.get("mode"):
            goal_mode = str(opts["mode"])
        if goal_mode:
            if goal_mode not in MODES:
                out["actions"].append({"mode": goal_mode, "error": "unknown mode"})
            elif s0["mode"] == goal_mode:
                out["actions"].append({"mode": goal_mode, "skip": "already"})
            else:
                sk.tgui_act(id=wid, action="mode",
                            params={"mode": "/datum/air_alarm_mode/" + goal_mode})
                time.sleep(0.8)
                s1 = read_state(wid)
                out["actions"].append({"mode": goal_mode, "was": s0["mode"],
                                       "now": s1["mode"],
                                       "done": s1["mode"] == goal_mode})
        if "vent_pressure" in opts:
            val = float(opts["vent_pressure"])
            for v in s0["vents"]:
                sk.tgui_act(id=wid, action="set_external_pressure",
                            params={"ref": v["ref"], "value": val})
                time.sleep(0.4)
            s2 = read_state(wid)
            exts = {v["external"] for v in s2["vents"]}
            out["actions"].append({"vent_pressure": val,
                                   "now": sorted(exts)[:4],
                                   "done": exts == {val}})
        if "vent_power" in opts:
            val = int(opts["vent_power"])
            for v in s0["vents"]:
                sk.tgui_act(id=wid, action="power",
                            params={"ref": v["ref"], "val": val})
                time.sleep(0.3)
            s3 = read_state(wid)
            pws = {v["power"] for v in s3["vents"]}
            out["actions"].append({"vent_power": val, "now": sorted(pws),
                                   "done": pws == {val}})
        if "scrub_power" in opts:
            val = int(opts["scrub_power"])
            d = sk.tgui_window(id=wid, max_chars=30000).text or ""
            seg = d[d.find('"scrubbers"'):]
            for m in re.finditer(r'"refID": "(\[0x[0-9a-f]+\])"', seg):
                sk.tgui_act(id=wid, action="power",
                            params={"ref": m.group(1), "val": val})
                time.sleep(0.3)
            out["actions"].append({"scrub_power": val, "sent": "all scrubbers"})
        if opts.get("lock_after"):
            sk.click(object_id=int(aid), right=True)
            out["actions"].append({"locked_again": True})
        s4 = read_state(wid)
        out["after"] = {"mode": s4["mode"], "env": s4["env"]}
        sk.tgui_send(id=wid, type="close")
        out["ok"] = True

RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
