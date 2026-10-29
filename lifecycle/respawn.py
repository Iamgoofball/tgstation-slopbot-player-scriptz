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
out
