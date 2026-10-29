"""Open ANY machine's tgui window by id (walks adjacent first), return its
parsed state keys compactly, and optionally apply tgui actions.

Run: run_script {script: ".../engineering/machine_ui.py", args: {"id": 12345}}
Optional: {"actions": [{"action": "power"}, {"action": "target", "params": {...}}, ...]}
Returns {win, state_keys, data, acted}. `data` is the window's JSON "data"
object (compact); compare before/after by running it twice.
Empty active hand required — a held tool gets used ON the machine instead.
"""
import json
import re
opts = args or {}
oid = opts.get("id")
if not oid:
    raise ValueError("args: {'id': obj_id, 'actions'?: [{action, params}]}")
out = {"id": oid}
bot.goto(object_id=oid, adjacent=True)
time.sleep(0.3)
# close stale same-interface windows first (clicks REUSE an open window)
for cand in [k.strip().rstrip(":") for k in (sk.tgui_windows().text or "").split("\n") if "tgui-window" in k]:
    try:
        d0 = sk.tgui_window(id=cand).text or ""
        if "interface" in d0 and "Ntos" not in d0:
            sk.tgui_send(id=cand, type="close")
            time.sleep(0.2)
    except Exception:
        pass
sk.click(object_id=oid, expect_name=None)
time.sleep(1.4)
w = [k.strip().rstrip(":") for k in (sk.tgui_windows().text or "").split("\n") if "tgui-window" in k]
win = w[-1] if w else None
out["win"] = win
if win:
    for act in opts.get("actions") or []:
        a = sk.tgui_act(id=win, action=act["action"], params=act.get("params") or {})
        time.sleep(0.5)
        out.setdefault("acted", []).append(act["action"])
    # SAFETY WATCHDOG (README section 1): abort on danger after acting
    DANGER = (r"delaminat|integrity|countdown|blast|explod|flood|fire|electroc|shock|causality|warning|emergency")
    ch = re.sub(r"<[^>]+>", " ", sk.read_chat(wait_s=1).text or "")
    hits = re.findall(r"[^\n]{0,60}(?:%s)[^\n]{0,60}" % DANGER, ch, re.I)
    if hits:
        raise SystemExit("ABORT danger after acting: %s" % hits[-2:])
    d = sk.tgui_window(id=win).text or ""
    m = re.search(r"state: \|\n(.*?)\nmessages_by_type", d, re.S) or re.search(r"state: \|\n(.*)", d, re.S)
    raw = m.group(1) if m else ""
    try:
        j = json.loads(raw)
        data = j.get("data", j)
        out["state_keys"] = sorted(data.keys()) if isinstance(data, dict) else []
        out["data"] = json.dumps(data)[: opts.get("slice", 900)]
    except Exception as ex:
        out["parse"] = str(ex)[:80]
        out["raw"] = d[:500]
out["ok"] = bool(win)
out
