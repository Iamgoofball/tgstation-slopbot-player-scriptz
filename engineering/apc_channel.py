# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Control one APC's channels / breaker via its tgui, state-checked: only acts
when the field differs from the goal, verifies via the server's data_changes.

Run: run_script {script: ".../engineering/apc_channel.py",
                 args: {"apc": <obj id>, "set": {"eqp": 2, "lgt": 1}, ...}}
set values: 1 off, 2 on, 3 auto. Optional: {"breaker": "on"|"off",
"charge": true, "nightshift": true} (charge/nightshift are bare toggles).
Flow (proven on Engineering APC 36713): RMB-click the APC with the ID in hand
= UNLOCK swipe (any hand works; LMB with ID in ACTIVE hand is also a swipe but
toggles randomly), then swap so the ACTIVE hand is empty and LMB-click to open
the Apc UI. Channel action is "channel" with params {eqp|lgt|env: 1|2|3};
state lives in data.powerChannels[] (title Equipment/Lighting/Environment ->
key eqp/lgt/env, "status": 1 off / 2 on / 3 auto) plus "locked"/"isOperating".
"""
import re

TITLE_KEY = {"Equipment": "eqp", "Lighting": "lgt", "Environment": "env"}

opts = args or {}
aid = opts.get("apc")
wanted = opts.get("set") or {}
if not aid:
    raise ValueError("args: {'apc': obj_id, 'set': {'eqp'|'lgt'|'env': 1|2|3}, ...}")
out = {"apc": aid, "actions": []}

def hand_lines():
    return [l for l in (sk.inventory().text or "").split("\n")
            if re.search(r'in slot "(left|right) hand"', l)]

def active_hand():
    for l in hand_lines():
        if "handactive" in l or re.search(r"\[marked: [lr]handactive\]", l):
            return l
    return None

def has_id_in_hand():
    return [l for l in hand_lines() if re.search(r"ID Card|card_grey", l, re.I)]

def ensure_id_in_hand():
    """ID must be in a hand for the unlock swipe. Takes it off the HUD slot."""
    if has_id_in_hand():
        return True
    # free the active hand first (HUD id draws into it)
    if active_hand() and re.search(r"obj \d+", active_hand()):
        sk.key(key="X"); time.sleep(0.4)          # try the other hand
        if active_hand() and re.search(r"obj \d+", active_hand()):
            sk.key(key="Q"); time.sleep(0.4)      # drop it
    btn = None
    for l in (sk.screen().text or "").split("\n"):
        m = re.search(r'obj (\d+) "?id"?.*state=id\b', l)
        if m:
            btn = int(m.group(1))
            break
    if btn is None:
        return False
    bot.click_thing(btn)
    time.sleep(0.5)
    return bool(has_id_in_hand())

def open_ui():
    """RMB = unlock swipe; then empty ACTIVE hand LMB = open the Apc UI."""
    a = sk.click(object_id=int(aid), right=True)
    out["swipe"] = (a.text or "")[-90:]
    time.sleep(0.6)
    if active_hand() and re.search(r"obj \d+", active_hand()):
        sk.key(key="X"); time.sleep(0.4)   # ID -> inactive hand, active empty
    c = sk.click(object_id=int(aid))
    time.sleep(1.0)
    wid = None
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        b = sk.tgui_window(id=m.group(1), max_chars=400).text or ""
        i = re.search(r"interface: (\S+)", b)
        if i and i.group(1) == "Apc":
            wid = m.group(1)
            break
    return wid

def read_state(wid):
    d = sk.tgui_window(id=wid, max_chars=20000).text or ""
    # parse ONLY the data block: "config" also carries a "locked": 0 (tgui
    # window lock) that must not be confused with the APC's interface lock
    m = re.search(r'"data": \{([\s\S]*?)\n   \},?\n', d)
    data = m.group(1) if m else d
    lk = re.search(r'"locked": (\d)', data)
    op = re.search(r'"isOperating": (\d)', data)
    cell = re.search(r'"powerCellStatus": ([\d.]+)', data)
    ext = re.search(r'"externalPower": (\d)', data)
    chs = {}
    for mm in re.finditer(r'"title": "(\w+)",\s*"powerLoad": "[^"]*",\s*"status": (\d)', data):
        chs[TITLE_KEY.get(mm.group(1), mm.group(1))] = int(mm.group(2))
    return {"locked": int(lk.group(1)) if lk else None,
            "operating": int(op.group(1)) if op else None,
            "cell": float(cell.group(1)) if cell else None,
            "external": int(ext.group(1)) if ext else None,
            "chs": chs}

g = bot.goto(object_id=int(aid))
if g.failed and "already there" not in (g.text or ""):
    raise SystemExit("walk to APC failed: " + (g.text or "")[-120:])
out["id_in_hand"] = ensure_id_in_hand()
wid = open_ui()
out["win"] = wid
if not wid:
    out["ok"] = False
    out["note"] = "Apc UI did not open (unlock swipe then empty-hand click)"
else:
    s0 = read_state(wid)
    out["before"] = s0
    if s0["locked"]:
        sk.click(object_id=int(aid), right=True)
        time.sleep(0.6)
        s0 = read_state(wid)
        out["unlocked_now"] = not s0["locked"]
    for key, goal in wanted.items():
        cur = s0["chs"].get(key)
        if cur is None:
            out["actions"].append({key: "no such channel"})
            continue
        if cur == int(goal):
            out["actions"].append({key: goal, "skip": "already %d" % cur})
            continue
        for attempt in (1, 2):
            sk.tgui_act(id=wid, action="channel", params={key: int(goal)})
            time.sleep(0.6)
            s1 = read_state(wid)
            now = s1["chs"].get(key)
            if now == int(goal):
                out["actions"].append({key: goal, "was": cur, "now": now,
                                       "done": True})
                break
            if attempt == 1 and s1["locked"]:
                # buttons do nothing while locked: swipe again, reopen, retry
                sk.click(object_id=int(aid), right=True)
                time.sleep(0.6)
                c = sk.click(object_id=int(aid))
                time.sleep(1.0)
                s0 = read_state(wid)
                cur = s0["chs"].get(key)
                out["actions"].append({key: "retry after unlock",
                                       "locked_was": s1["locked"]})
        else:
            out["actions"].append({key: goal, "was": cur, "now": now,
                                   "done": False})
    if opts.get("breaker") in ("on", "off"):
        goal = 1 if opts["breaker"] == "on" else 0
        if s0["operating"] != goal:
            sk.tgui_act(id=wid, action="breaker")
            time.sleep(0.6)
            s2 = read_state(wid)
            out["actions"].append({"breaker": opts["breaker"],
                                   "now_operating": s2["operating"]})
        else:
            out["actions"].append({"breaker": "already %s" % opts["breaker"]})
    if "charge" in opts:
        sk.tgui_act(id=wid, action="charge")
        out["actions"].append({"charge": "toggled"})
    if "nightshift" in opts:
        sk.tgui_act(id=wid, action="toggle_nightshift")
        out["actions"].append({"nightshift": "toggled"})
    sk.tgui_send(id=wid, type="close")
    out["after"] = read_state(wid) if False else None
    out["ok"] = True

RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
