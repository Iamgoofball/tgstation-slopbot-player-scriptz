# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Walk into an area by name and report where you ended up.

Run: run_script {script: ".../movement/goto_area.py", args: {"area": "Medbay Central"}}"""
opts = args or {}
area = opts.get("area") or ValueError("args: {'area': 'Medbay Central'}")
walk = bot.goto_area(area, max_steps=int((args or {}).get("max_steps", 80)))
after = sk.status()
RESULT = ({"ok": not walk.failed, "area": area, "answer": (walk.text or "")[:160],
 "now": (after.get("you") or "")[:80], "rev": after.rev})

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
