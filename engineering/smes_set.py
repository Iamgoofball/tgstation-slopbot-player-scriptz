"""Set a SMES ("power storage unit") input/output via its tgui window.
Fork defaults: input 200 kW (max), output 190 kW.

Run: run_script {script: ".../engineering/smes_set.py",
                 args: {"id": 12345}}
Optional: {"input_w": 200000, "output_w": 190000}. Empty active hand required
to open the window. Returns {inputting, outputting, charge, ok}.
"""
import re
opts = args or {}
oid = opts.get("id")
in_w = opts.get("input_w", 200000)
out_w = opts.get("output_w", 190000)
if not oid:
    raise ValueError("args: {'id': obj_id}")
out = {"id": oid}
sk.click(object_id=oid, expect_name=None)   # opens the Smes window
time.sleep(1.2)
w = [k for k in (sk.tgui_windows().text or "").split("\n") if "tgui-window" in k]
win = w[-1].strip().rstrip(":") if w else None
out["win"] = win
if win:
    sk.tgui_act(id=win, action="input", params={"target": in_w}); time.sleep(0.4)
    sk.tgui_act(id=win, action="output", params={"target": out_w}); time.sleep(0.4)
    d = sk.tgui_window(id=win).text or ""
    out["inputting"] = bool(re.search(r'"inputAttempt":\s*1', d))
    out["outputting"] = bool(re.search(r'"outputAttempt":\s*1', d))
    m = re.search(r'"charge":\s*([\d.]+)', d)
    out["charge"] = float(m.group(1)) if m else None
    out["ok"] = out["inputting"] and out["outputting"]
out
