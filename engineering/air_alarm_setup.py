# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Configure an engine air alarm — FULLY ROUND-AGNOSTIC: device refs, counts
and ids are all read live from the alarm's tgui data (never hard-coded).

stage "vents":     for EVERY vent in data.vents -> clear the external limit
                   CHECK (excheck XOR quirk: send val=1 to clear, val=0 is a
                   no-op — source air_alarm.dm) then set_external_pressure to
                   args.ext_pressure (default 101 kPa; never 0 — an external
                   bound of 0 with the check on means the vent never pumps).
                   Never set vents to siphon!.
stage "scrubbers": for EVERY scrubber in data.scrubbers -> widenet ON, and
                   (args.siphon) set SIPHON mode: scrubbing {ref, val: 0} —
                   POLARITY: set_scrubbing(true)=scrub-mode, so val:0 is
                   SIPHON (source air_alarm.dm set_scrubbing). Siphon only
                   once the chamber has >8 mol and >90% N2 (CIMS), else you
                   empty the chamber to vacuum.

Run: run_script {script: ".../engineering/air_alarm_setup.py",
                 args: {"id": <air alarm obj id>, "stage": "vents"|"scrubbers",
                        "ext_pressure": 101}}   # ext_pressure optional
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
    raise ValueError("args: {'id': alarm_id, 'stage': 'vents'|'scrubbers', "
                     "'ext_pressure'?: 101, 'siphon'?: bool (scrubbers only; "
                     "CIMS gates must pass first) }")
out = {"id": oid, "stage": stage}
try:
    ext_pressure = float(opts.get("ext_pressure", 101))
except (TypeError, ValueError):
    ext_pressure = 101.0

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

def vent_excheck_clear(wid, dev, data):
    """Disable a vent's external pressure CHECK (the guide's 'disable the
    external limits'). The act XORs the sent val into pressure_checks, so
    val=0 is a NO-OP; to CLEAR the external bound you must send val=1 when
    the check is on (source: air_alarm.dm 'excheck' -> checks ^ EXTERNAL).
    No-op when already off."""
    seg = re.search(r'"refID":\s*"%s".*?(?=refID|\Z)' % re.escape(dev["ref"]), data, re.S)
    seg = seg.group(0) if seg else ""
    if re.search(r'"excheck":\s*1\b', seg):
        act(wid, "excheck", {"ref": dev["ref"], "val": 1})

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
        # 1) clear the external limit CHECK (XOR quirk: val=1 clears, val=0 no-op)
        vent_excheck_clear(wid, d, sk.tgui_window(id=wid, path="data." + path).text or "")
        # 2) set the external target pressure (station default 101 kPa)
        act(wid, "set_external_pressure", {"ref": d["ref"], "value": ext_pressure})
    else:
        act(wid, "widenet", {"ref": d["ref"], "val": 1})
        if opts.get("siphon"):
            # POLARITY: scrubbing val 0 = SIPHON (set_scrubbing(true)=scrub);
            # val 1 = scrub mode (removes only selected gases -> nothing)
            act(wid, "scrubbing", {"ref": d["ref"], "val": 0})
# verify against fresh data
time.sleep(1.0)
fresh = {(x["ref"]): x for x in dev_list(wid, path)}
data = sk.tgui_window(id=wid, path="data." + path).text or ""
for d in devices:
    seg = re.search(r'"refID":\s*"%s".*?(?=refID|\Z)' % re.escape(d["ref"]), data, re.S)
    seg = seg.group(0) if seg else ""
    if stage == "vents":
        d["ok"] = (not re.search(r'"excheck":\s*1\b', seg)
                   and bool(re.search(r'"external":\s*%s\b' % re.escape(str(ext_pressure)), seg)))
        d["power"] = bool(re.search(r'"power":\s*1\b', seg))
    else:
        if opts.get("siphon"):
            # siphon = scrubbing 0 (see polarity note above)
            d["ok"] = bool(re.search(r'"scrubbing":\s*0\b', seg))
        else:
            d["ok"] = bool(re.search(r'"scrubbing":\s*1\b', seg))
        d["widenet"] = bool(re.search(r'"widenet":\s*1\b', seg))
    out["devices"].append(d)
out["ok"] = all(d["ok"] for d in out["devices"])
RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
