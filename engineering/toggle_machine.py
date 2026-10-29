# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""State-Checked toggle for any machine with an on/off field. THE RULE THIS
ENCODES: toggles are NOT idempotent — never blind-click. Read the current
state first; only act if it differs from the goal; verify after.

Works for: emitters (state field in search facts has no on/off marker — give
the machine a UI where possible, or rely on the click echo "You turn on/off
the emitter"), pumps/valves (tgui "on"/"power" fields), SMES
(isOperating/outputAttempt). For emitters specifically prefer this script's
echo verification + a CIMS delta check (cims_watch.py) — icons lie.

Run: run_script {script: ".../engineering/toggle_machine.py",
                 args: {"id": 40384, "goal": true, "kind": "emitter"}}
kind: "emitter" (click, echo-verify) | "tgui_field" with
  {"field": "isOperating", "action": "tryinput"} — read field via open tgui
  window, act only if field != goal, re-read to verify.
Optional: {"x","y"} walk first. Empty active hand REQUIRED.
Returns {id, goal, before, acted, after, ok}.
before/after: true/false/None (None = unknown -> treated as "act needed").
"""
import re, time
opts = args or {}
oid = opts.get("id")
goal = bool(opts.get("goal", True))
kind = opts.get("kind", "emitter")
if not oid:
    raise ValueError("args: {'id': obj_id, 'goal': true|false, 'kind': 'emitter'|'tgui_field', ...}")
out = {"id": oid, "goal": goal}

if opts.get("x") is not None:
    bot.goto(x=opts["x"], y=opts["y"]); time.sleep(0.5)

# active hand must be empty for clicks/UIs
inv = (sk.inventory().text or "")
act = [l for l in inv.split("\n") if "active_hand" in l]
if act and "empty" not in act[0]:
    sk.key(key="X"); time.sleep(0.6)
    inv = (sk.inventory().text or "")
    act = [l for l in inv.split("\n") if "active_hand" in l]
out["active_hand"] = act[0].strip()[:60] if act else "?"

if kind == "emitter":
    # read current state from the emitter's own window if one opens cheaply —
    # emitters have no readable state, so use click echo as the state change:
    # a fresh open tgui list first to detect an existing window (stale reads lie)
    wins = (sk.tgui_windows().text or "")
    for m in re.finditer(r"(tgui-window-\d+):", wins):
        try:
            sk.tgui_send(id=m.group(1), type="close"); time.sleep(0.2)
        except Exception:
            pass
    c = sk.click(object_id=oid, expect_name=None); time.sleep(1.6)
    echo = (c.text or "")
    m = re.search(r"You turn (on|off) the emitter", echo)
    if m:
        out["before"] = (m.group(1) == "off")     # turning on => was off
        out["_echo_on"] = (m.group(1) == "on")
        out["acted"] = True
    else:
        out["before"] = None
        out["acted"] = False
        out["echo"] = echo[:120]
else:  # tgui_field
    field = opts.get("field", "isOperating")
    action = opts.get("action")
    if not action:
        raise ValueError("kind tgui_field needs 'action' (e.g. 'tryinput', 'output')")
    # find the window that actually HAS this field (a leftover window from
    # another machine would otherwise be misread — the stale-APC-as-SMES trap)
    def find_win():
        wins = (sk.tgui_windows().text or "")
        for m in re.finditer(r"(tgui-window-\d+):", wins):
            b = (sk.tgui_window(id=m.group(1)).text or "")
            if re.search(r'"' + field + r'":\s*(1|0|true|false)', b):
                return m.group(1)
        return None
    wid = find_win()
    if not wid:
        c = sk.click(object_id=oid, expect_name=None); time.sleep(2.2)
        wid = find_win()
    d = (sk.tgui_window(id=wid).text or "")
    m = re.search(r'"' + field + r'":\s*(1|0|true|false)', d)
    cur = None
    if m:
        cur = m.group(1) in ("1", "true")
    out["before"] = cur
    out["wid"] = wid
    if cur is None or cur != goal:
        a = sk.tgui_act(id=wid, action=action, params=opts.get("params", {}))
        out["acted"] = True
        time.sleep(1.0)
    else:
        out["acted"] = False
    d = (sk.tgui_window(id=wid).text or "")
    m = re.search(r'"' + field + r'":\s*(1|0|true|false)', d)
    out["after"] = (m.group(1) in ("1", "true")) if m else None

if kind == "emitter" and out.get("acted"):
    out["after"] = out.get("_echo_on", goal)
    out["ok"] = (out["after"] == goal)
elif kind == "tgui_field":
    out["ok"] = out.get("after") == goal
else:
    out["ok"] = False  # echo didn't confirm — ALWAYS follow with cims_watch

RESULT = out

END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
