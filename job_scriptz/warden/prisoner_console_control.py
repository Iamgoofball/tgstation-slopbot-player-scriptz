# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'),
          encoding='utf-8').read())
precheck()
"""Prisoner management console (tgui "PrisonerManagement") driver: status
(login + data dump), insert_id, eject_id, reset_id, set_id_goal (the
labor-camp point goal), handle_implant (trigger/deactivate an implant on
the inserted ID).

Run: run_script {script: ".../job_scriptz/warden/prisoner_console_control.py",
                 args: {"mode": "status"|"insert_id"|"eject_id"|
                              "reset_id"|"set_id_goal"|"handle_implant",
                        "console"?: <obj id>,     # else auto-find
                        "goal"?: 10,              # points for set_id_goal
                        "implant_action"?: "trigger"|"deactivate"|"remove",
                        "implant_ref"?: "[0x...]"}}
Console on MetaStation: prisoner management console 23959 at (108,165) in
Brig Control (dense - the script walks to the tile in front; clicks beyond
1 tile are silently ignored).

Live-verified: open (adjacent empty-hand click), login
(authorized: 0 -> 1), data dump shape {authorized, inserted_id, implants}.
NOT live-tested (no prisoner ID available): insert_id (put the prisoner's
ID card in your ACTIVE HAND first), eject_id, reset_id (clears the
sentence), set_id_goal (labor-camp points), handle_implant.

Warden duty tie-ins: set_id_goal on labor-camp IDs or they may be stuck
forever; the console also triggers/deactivates chemical/tracking implants.
"""
import re

opts = args or {}
mode = opts.get("mode") or "status"
out = {"mode": mode, "verdict": []}


def active_obj():
    for l in (sk.inventory().text or "").split("\n"):
        if "lhandactive" in l:
            m = re.match(r"- obj (\d+)", l.strip())
            if m:
                return int(m.group(1))
    return None


def empty_active_hand():
    if active_obj() is None:
        return
    sk.key(key="X")
    time.sleep(0.5)
    if active_obj() is not None:
        sk.key(key="Q")
        time.sleep(0.6)


def find_console():
    cid = opts.get("console")
    if cid:
        return cid
    s = sk.search(query="prisoner management console", kind="obj",
                  page_size=5).text or ""
    for l in s.split("\n"):
        m = re.match(r"- obj (\d+) \"prisoner management console\" "
                     r"at (\d+),(\d+)", l.strip())
        if m and "left the view" not in l:
            return int(m.group(1))
    return None


def open_window(cid):
    empty_active_hand()
    s = sk.search(query="prisoner management console", kind="obj",
                  page_size=5).text or ""
    cx = cy = None
    for l in s.split("\n"):
        m = re.match(r"- obj (\d+) \"[^\"]*\" at (\d+),(\d+)", l.strip())
        if m and int(m.group(1)) == cid:
            cx, cy = int(m.group(2)), int(m.group(3))
    if cx is not None:
        g = bot.goto(x=cx - 1, y=cy, max_steps=40)
        if "arrived" not in (g.text or ""):
            out["verdict"].append("walk to the console failed")
    c = sk.click(object_id=cid)
    time.sleep(1.8)
    wins = (sk.tgui_windows(all=True).text or "")
    for m in re.finditer(r"  (tgui-window-\d+):\n((?:    [^\n]*\n)+)", wins):
        if "PrisonerManagement" in m.group(2) and \
                "closed: true" not in m.group(2):
            return m.group(1)
    return None


def data_of(wid):
    w = (sk.tgui_window(id=wid, max_chars=1600).text or "")
    m = re.search(r'"data": \{(.*?)\n   \}', w, re.S)
    return (m.group(1).replace("\n", " ").strip() if m else w[:300])


def act_changes(a):
    t = a.text or ""
    if re.search(r"data_changes: none", t):
        return {}
    seg = re.split(r"data_changes:", t)
    if len(seg) < 2:
        return None
    ch = {}
    for line in seg[1].split("\n"):
        m = re.match(r'\s*- ([\w.]+(?: \([^)]*\))?): "?([^" ]*)"?\s*->\s*'
                     r'"?([^" ]*)"?', line)
        if m:
            ch[m.group(1)] = (m.group(2), m.group(3))
        elif line.strip() and not line.strip().startswith("-") and ch:
            break
    return ch


cid = find_console()
if not cid:
    RESULT = {"ok": False, "note": "no prisoner management console found"}
else:
    out["console"] = cid
    wid = open_window(cid)
    if not wid:
        RESULT = {"ok": False, "note": "PrisonerManagement tgui did not "
                                        "open"}
    else:
        out["wid"] = wid
        a = sk.tgui_act(id=wid, action="login")
        time.sleep(1.2)
        ch = act_changes(a)
        out["login"] = ch.get("authorized") if ch else ("already", "1")
        if mode == "status":
            out["data"] = data_of(wid)
            out["ok"] = True
        elif mode == "insert_id":
            held = active_obj()
            if not held:
                out["verdict"].append("put the prisoner ID in your ACTIVE "
                                      "hand first")
                out["ok"] = False
            else:
                a = sk.tgui_act(id=wid, action="insert_id")
                time.sleep(1.4)
                out["changes"] = act_changes(a)
                out["data"] = data_of(wid)
                out["ok"] = bool(out["changes"])
        elif mode == "eject_id":
            a = sk.tgui_act(id=wid, action="eject_id")
            time.sleep(1.4)
            out["changes"] = act_changes(a)
            out["data"] = data_of(wid)
            out["ok"] = bool(out["changes"])
        elif mode == "reset_id":
            a = sk.tgui_act(id=wid, action="reset_id")
            time.sleep(1.4)
            out["changes"] = act_changes(a)
            out["ok"] = bool(out["changes"])
        elif mode == "set_id_goal":
            goal = opts.get("goal", 10)
            a = sk.tgui_act(id=wid, action="set_id_goal",
                            params={"goal": goal})
            time.sleep(1.4)
            out["changes"] = act_changes(a)
            out["data"] = data_of(wid)
            out["ok"] = bool(out["changes"])
            if not out["ok"]:
                out["verdict"].append("goal not set (an ID must be "
                                      "inserted; maybe a modal opened)")
        elif mode == "handle_implant":
            a = sk.tgui_act(id=wid, action="handle_implant",
                            params={"implant_action":
                                    opts.get("implant_action") or "trigger",
                                    "implant_ref":
                                    opts.get("implant_ref")})
            time.sleep(1.4)
            out["changes"] = act_changes(a)
            out["data"] = data_of(wid)
            out["ok"] = bool(out["changes"])
        else:
            out["verdict"].append("unknown mode %r" % mode)
            out["ok"] = False

RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
