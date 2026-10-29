# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Configure an engine air alarm — FULLY ROUND-AGNOSTIC: device refs, counts
and ids are all read live from the alarm's tgui data (never hard-coded).

stage "vents":     for EVERY vent in data.vents -> set_external_pressure 0
                   (this fork's excheck is read-only; external=0 == no limit;
                   never set vents to siphon!).
stage "scrubbers": for EVERY scrubber in data.scrubbers -> widenet ON.
                   (Siphon comes later, per the fork truth: only once the
                   chamber has >8 mol and >90% N2 — use the alarm's "siphon"
                   mode then, else you empty the chamber to vacuum.)

Run: run_script {script: ".../engineering/air_alarm_setup.py",
                 args: {"id": <air alarm obj id>, "stage": "vents"|"scrubbers"}}
Returns {stage, devices: [{id, ref, ok}], ok} — verify ok on every device.
Fork truths: the alarm UI is the ref-based AirAlarm (actions like
"set_external_pressure {ref, value}", "widenet {ref, val}"); refs look like
"[0x200973b]" and are parsed from the window, whatever they are this round.
"""
import re
import time
opts = args or {}
oid = opts.get("oid") or opts.get("id")
stage = (opts.get("stage") or "").lower()
if not oid or stage not in ("vents", "scrubbers"):
    raise ValueError("args: {'id': alarm_id, 'stage': 'vents'|'scrubbers'}")
out = {"id": oid, "stage": stage}

def airalarm_window():
    """Find the open tgui window bound to this alarm (agnostic on window id;
    matches the AirAlarm interface — the digest may not carry the obj id)."""
    txt = sk.tgui_windows().text or ""
    found = None
    for m in re.finditer(r"(tgui-window-\d+):", txt):
        wid = m.group(1)
        try:
            blob = sk.tgui_window(id=wid).text or ""
        except Exception:
            continue
        if "AirAlarm" in blob:
            found = wid   # keep the LAST match (most recently opened)
    return found

def dev_list(wid, path):
    """Read data.<vents|scrubbers> and extract {ref, id} per device."""
    d = sk.tgui_window(id=wid, path="data." + path).text or ""
    refs = re.findall(r'"refID":\s*"(\[0x[0-9a-fA-F]+\])"\s*\(=\s*obj\s*(\d+)', d)
    return [{"ref": r, "id": int(i)} for r, i in refs]

def act(wid, action, params):
    a = sk.tgui_act(id=wid, action=action, params=params)
    time.sleep(0.7)
    return (a.text or "")

# open the alarm window (empty active hand) if not already open
wid = airalarm_window()
if not wid:
    bot.goto(object_id=oid, adjacent=True)
    time.sleep(0.4)
    sk.click(object_id=oid, expect_name=None)
    time.sleep(1.6)
    wid = airalarm_window()
if not wid:
    raise SystemExit("AirAlarm window did not open for id %s" % oid)
out["win"] = wid

path = "vents" if stage == "vents" else "scrubbers"
devices = dev_list(wid, path)
if not devices:
    raise SystemExit("no %s found in window data (UI changed?) — dump "
                     "tgui_window(id=%r) raw and adapt" % (path, wid))
out["devices"] = []
for d in devices:
    if stage == "vents":
        act(wid, "set_external_pressure", {"ref": d["ref"], "value": 0})
    else:
        act(wid, "widenet", {"ref": d["ref"], "val": 1})
# verify against fresh data
time.sleep(1.0)
fresh = {(x["ref"]): x for x in dev_list(wid, path)}
data = sk.tgui_window(id=wid, path="data." + path).text or ""
for d in devices:
    seg = re.search(r'"refID":\s*"%s".*?(?=refID|\Z)' % re.escape(d["ref"]), data, re.S)
    seg = seg.group(0) if seg else ""
    if stage == "vents":
        d["ok"] = bool(re.search(r'"external":\s*0\b', seg))
        d["power"] = bool(re.search(r'"power":\s*1\b', seg))
    else:
        d["ok"] = bool(re.search(r'"widenet":\s*1\b', seg))
    out["devices"].append(d)
out["ok"] = all(d["ok"] for d in out["devices"])
RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
