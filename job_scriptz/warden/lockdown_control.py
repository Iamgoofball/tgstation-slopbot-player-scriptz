# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'),
          encoding='utf-8').read())
precheck()
"""Brig lockdown buttons driver (the Warden's button grid): read the
buttons + what they gate, toggle a lockdown (drops/raises the shutters or
blast doors it controls), or a guarded round-trip (mode "cycle": toggle on,
verify, toggle off, verify).

Run: run_script {script: ".../job_scriptz/warden/lockdown_control.py",
                 args: {"mode": "status"|"toggle"|"cycle",
                        "button"?: <obj id>,   # else Brig Lockdown Control
                        "force"?: true}}       # skip the wing-people guard
Buttons on MetaStation (this round): Brig Lockdown Control 23169, Prison
Wing Lockdown 23170, Cell Window Control 23168 - all at (105,164)ish in
Brig Control; they gate the Warden Desk Shutters 23717 (107,161) and the
brig/permawing/armory barriers. Use when a mob comes for the Brig.

Live-verified: toggle round-trip on Brig Lockdown Control (shutter state
flips open <-> closed both ways, verified on the shutters object).
Hazard: a lockdown seals people OUT of the brig (and officers IN their
posts) - never leave one engaged by accident; cycle restores the state.
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


def find_button():
    bid = opts.get("button")
    if bid:
        return bid
    s = sk.search(query="Lockdown", kind="obj", page_size=8).text or ""
    for l in s.split("\n"):
        m = re.match(r"- obj (\d+) \"Brig Lockdown Control\"", l.strip())
        if m:
            return int(m.group(1))
    return None


def obj_line(oid):
    """Search by NAME (search never matches bare obj ids), then find the
    id in the results."""
    s = sk.search(query="Lockdown", kind="obj", page_size=8).text or ""
    for l in s.split("\n"):
        m = re.match(r"- obj (\d+) \"([^\"]*)\" at (\d+),(\d+)", l.strip())
        if m and int(m.group(1)) == oid:
            return m.group(2), int(m.group(3)), int(m.group(4))
    return None, None, None


def read_line(oid, x, y):
    t = (sk.tile(x, y, all=True).text or "")
    for l in t.split("\n"):
        if ("obj %d " % oid) in l:
            return l.strip()
    return ""


def shutters_state():
    """The Brig's Warden Desk Shutters: state=open/closed from its line."""
    s = sk.search(query="Warden Desk Shutters", kind="obj",
                  page_size=5).text or ""
    for l in s.split("\n"):
        m = re.match(r"- obj (\d+) \"Warden Desk Shutters\"", l.strip())
        if m:
            e = (sk.examine(object_id=int(m.group(1))).text or "")
            st = re.search(r"state=(\w+)", l)
            return {"id": int(m.group(1)), "state": st and st.group(1)}
    return None


def people_near(x, y, r=6):
    st = (sk.status().text or "")
    mid = re.search(r"you: mob (\d+)", st)
    mid = mid.group(1) if mid else None
    my_name = _my_name()
    found = []
    s = sk.search(query="", kind="mob", page_size=25).text or ""
    for l in s.split("\n"):
        m = re.match(r"- mob (\d+) \"([^\"]*)\" at (\d+),(\d+)", l.strip())
        if m and m.group(1) != mid and m.group(2) != my_name:
            dx, dy = int(m.group(3)) - x, int(m.group(4)) - y
            if abs(dx) <= r and abs(dy) <= r:
                found.append("%s (%d,%d)" % (m.group(2), int(m.group(3)),
                                             int(m.group(4))))
    return found


bid = find_button()
if not bid:
    RESULT = {"ok": False, "note": "no lockdown button found"}
else:
    name, bx, by = obj_line(bid)
    out["button"] = {"id": bid, "name": name, "x": bx, "y": by}
    if bx is None:
        out["verdict"].append("button position unknown - walk there first")
    else:
        empty_active_hand()
        g = bot.goto(x=bx, y=by, max_steps=40)
        out["walk"] = "arrived" in (g.text or "")
        sh = shutters_state()
        out["shutters_before"] = sh
        e = (sk.examine(object_id=bid).text or "")
        out["button_examine"] = e[:220]
        if mode == "status":
            out["ok"] = True
        elif mode in ("toggle", "cycle"):
            guards = people_near(bx, by)
            if guards and not opts.get("force") and mode == "cycle":
                out["verdict"].append("REFUSED: mobs near the brig front: "
                                      "%s - use force=true only when the "
                                      "lockdown is the point" %
                                      ", ".join(guards))
                out["ok"] = False
            else:
                c = sk.click(object_id=bid)
                time.sleep(2.0)
                sh2 = shutters_state()
                out["shutters_after"] = sh2
                changed = sh and sh2 and sh["state"] != sh2["state"]
                out["toggled"] = bool(changed)
                if mode == "toggle":
                    out["ok"] = bool(changed)
                    if not out["ok"]:
                        out["verdict"].append("no state change - the "
                                              "button may not gate these "
                                              "shutters")
                else:
                    # cycle: restore
                    c2 = sk.click(object_id=bid)
                    time.sleep(2.0)
                    sh3 = shutters_state()
                    out["shutters_restored"] = sh3
                    restored = sh and sh3 and sh["state"] == sh3["state"]
                    out["ok"] = bool(changed and restored)
                    if not out["ok"]:
                        out["verdict"].append("round-trip broken: changed="
                                              "%s restored=%s - restore the "
                                              "state by hand" %
                                              (bool(changed), bool(restored)))
        else:
            out["verdict"].append("unknown mode %r" % mode)
            out["ok"] = False

RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
