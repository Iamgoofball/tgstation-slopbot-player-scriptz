# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Compact "where am I, what do I hold, what's open" snapshot.

Run: run_script {script: ".../setup/session_report.py"}
Returns: position, active-hand item, pull/combat HUD states, open tgui windows."""
import re
t = (sk.inventory().text or "")
act = [l for l in t.split("\n") if "handactive" in l]
sc = (sk.screen(page_size=40).text or "")
def st(pat):
    for l in sc.split("\n"):
        if pat in l:
            return l.split("state=")[-1].split()[0] if "state=" in l else "?"
    return "absent"
w = sk.tgui_windows().text or ""
open_wins = re.findall(r"(\S+):\n", w)
RESULT = ({"ok": True,
 "you": (sk.status().get("you") or "")[:90],
 "active": (act[0][:90] if act else "none"),
 "combat": st("combat mode"), "pull": st("stop pulling"),
 "windows": open_wins[:4]})

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
