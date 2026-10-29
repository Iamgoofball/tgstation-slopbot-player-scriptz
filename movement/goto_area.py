"""Walk into an area by name and report where you ended up.

Run: run_script {script: ".../movement/goto_area.py", args: {"area": "Medbay Central"}}"""
opts = args or {}
area = opts.get("area") or ValueError("args: {'area': 'Medbay Central'}")
walk = bot.goto_area(area)
after = sk.status()
{"ok": not walk.failed, "area": area, "answer": (walk.text or "")[:160],
 "now": (after.get("you") or "")[:80], "rev": after.rev}
