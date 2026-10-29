# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Walk to tile x,y (falls back to the nearest free tile when it is taken).

Run: run_script {script: ".../movement/goto_tile.py", args: {"x": 85, "y": 97}}"""
opts = args or {}
x, y = opts.get("x"), opts.get("y")
if x is None or y is None:
    raise ValueError("args: {'x': 85, 'y': 97}")
w = bot.goto(x=x, y=y)
after = sk.status()
RESULT = ({"ok": not w.failed, "target": [x, y], "answer": (w.text or "")[:160],
 "now": (after.get("you") or "")[:80], "rev": after.rev})

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
