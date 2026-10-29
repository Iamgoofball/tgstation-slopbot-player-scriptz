# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Ghost out of the current body (verb Ghost -> confirm the AlertModal).

Run: run_script {script: ".../lifecycle/ghost_out.py"}"""
import re
r = sk.command(line="Ghost")
m = re.search(r"tgui-window-\d+", r.text or "")
out = {"prompt": bool(m)}
if m:
    a = sk.tgui_act(id=m.group(0), action="choose", params={"choice": "Ghost"})
    out["confirmed"] = "closed" in (a.text or "")
time.sleep(1.0)
out["you"] = (sk.status().get("you") or "")[:80]
out["ok"] = out.get("confirmed", False)
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
