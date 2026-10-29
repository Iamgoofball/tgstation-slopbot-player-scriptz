# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Setup an engine air alarm's devices: stage "vents" turns OFF the external
pressure limit on every vent (never set vents to siphon!); stage "scrubbers"
sets every scrubber to siphon + expanded range. Fork truth: only siphon once
the chamber has >8 mol and >90% N2, or you empty it to vacuum.

Run: run_script {script: ".../engineering/air_alarm_setup.py",
                 args: {"id": <air alarm obj id>, "stage": "vents"|"scrubbers"}}
Returns {vents: [{ref, ok}], scrubbers: [...], ok}.
"""
import re
opts = args or {}
oid = opts.get("id")
stage = (opts.get("stage") or "").lower()
if not oid or stage not in ("vents", "scrubbers"):
    raise ValueError("args: {'id': alarm_id, 'stage': 'vents'|'scrubbers'}")
out = {"id": oid, "stage": stage}
sk.click(object_id=oid, expect_name=None)   # open the alarm window (empty hand)
time.sleep(1.2)
w = [k for k in (sk.tgui_windows().text or "").split("\n") if "tgui-window" in k]
win = w[-1].strip().rstrip(":") if w else None
out["win"] = win
d = sk.tgui_window(id=win).text or "" if win else ""

def refs(kind):
    """Pull ref ids for entries of one kind out of the window dump."""
    return re.findall(r'"ref":\s*"?([\w\-\[\]0-9.]+)"?[^{}]{0,120}?"name":\s*"[^"]*' + kind, d) or \
           re.findall(r'"name":\s*"[^"]*' + kind + r'[^"]*"[^{}]{0,120}?"ref":\s*"?([\w\-\[\]0-9.]+)"?', d)

if stage == "vents":
    out["vents"] = []
    for r in refs("vent"):
        cur = re.search(r'"ref":\s*"' + re.escape(r) + r'"[^{}]*"checks[^}]*}', d)
        val = 1  # sending val:1 flips the external-limit bit (with checks:1 -> 0)
        a = sk.tgui_act(id=win, action="excheck", params={"ref": r, "val": val})
        time.sleep(0.4)
        out["vents"].append({"ref": r, "sent": "sent" in (a.text or "")})
    out["ok"] = len(out["vents"]) > 0
else:
    out["scrubbers"] = []
    for r in refs("scrubber"):
        sk.tgui_act(id=win, action="scrubbing", params={"ref": r, "val": 0}); time.sleep(0.4)
        a = sk.tgui_act(id=win, action="widenet", params={"ref": r, "val": 1}); time.sleep(0.4)
        out["scrubbers"].append({"ref": r, "sent": "sent" in (a.text or "")})
    out["ok"] = len(out["scrubbers"]) > 0
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
