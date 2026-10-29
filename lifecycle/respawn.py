# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
# respawn.py STARTS AS A GHOST by design (Respawn is a ghost verb) — the shared
# precheck() aborts on "[ghost]" status, so use a chat-only danger check here.
# postcheck() at the end is fine: by then we expect a living/new-player status.
_sit = _sitrep()
_raw = " ".join(str(h.get("text") or h.get("raw") or "") for h in _sit["heard"])
_bad = re.findall(r"[^\n]{0,70}(?:%s)[^\n]{0,70}" % DANGER, _raw, re.I)
if _bad:
    raise SystemExit("PRECHECK ABORT: %s" % _bad[-2:])
"""Respawn into a new body (verb Respawn; answers the admin-override prompt Yes).

Run: run_script {script: ".../lifecycle/respawn.py", args: {"choice": "Yes"}}
choice "No" declines the override. Server has respawn disabled; localhost admins
get the override prompt."""
import re
choice = (args or {}).get("choice", "Yes")
r = sk.command(line="Respawn")
m = re.search(r"tgui-window-\d+", r.text or "")
out = {"prompt": bool(m)}
if m:
    a = sk.tgui_act(id=m.group(0), action="choose", params={"choice": choice})
    t = (a.text or "")
    out["override"] = "closed" in t
    out["welcome"] = bool(re.search(r"Welcome|roleplay", t))
time.sleep(1.5)
out["you"] = (sk.status().get("you") or "")[:80]
out["ok"] = out.get("override", False) or "new player" in out["you"]
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
