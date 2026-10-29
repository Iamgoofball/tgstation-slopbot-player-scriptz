# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Set a Temperature control unit (freezer) to a target temperature via tgui.
Do NOT alt-click a freezer: the first alt-click sets it to 573 K (heating)!

Run: run_script {script: ".../engineering/freezer_set.py",
                 args: {"id": 12345, "target": 73.15}}
Args: id (obj id) or name (searched in view). Engine target: 73.15 K.
Returns {on, target, ok}.
"""
import re
opts = args or {}
oid = opts.get("id")
name = opts.get("name") or ""
target = opts.get("target", 73.15)
if not oid and name:
    s = sk.search(query=name, in_view=True).text or ""
    m = re.search(r'- obj (\d+) "' + re.escape(name) + '"', s)
    if m: oid = int(m.group(1))
if not oid:
    raise ValueError("args: {'id': obj_id, 'target': 73.15} (or name)")

out = {"id": oid}
sk.click(object_id=oid, expect_name=name or None)   # open the window (empty hand!)
time.sleep(1.2)
w = [k for k in (sk.tgui_windows().text or "").split("\n") if "tgui-window" in k]
win = w[-1].strip().rstrip(":") if w else None
out["win"] = win
if win:
    a = sk.tgui_act(id=win, action="power")
    time.sleep(0.5)
    b = sk.tgui_act(id=win, action="target", params={"target": target})
    time.sleep(0.5)
    d = sk.tgui_window(id=win).text or ""
    out["on"] = '"on": 1' in d or '"on":true' in d
    m = re.search(r'"target":\s*([\d.]+)', d)
    out["target"] = float(m.group(1)) if m else None
    out["ok"] = bool(out["on"]) and out["target"] is not None and abs(out["target"] - float(target)) < 1
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
