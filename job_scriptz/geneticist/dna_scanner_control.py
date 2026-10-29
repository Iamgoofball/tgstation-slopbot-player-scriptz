# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Control a DNA scanner (pod): open / close / load a carbon / (un)lock bolts.

Run: run_script {script: ".../job_scriptz/geneticist/dna_scanner_control.py",
                 args: {"mode": "open"|"close"|"toggle"|"load"|"lock"|"unlock",
                        "scanner"?, "console"?, "load"?: <mob id>, "x"?, "y"?}}
Default mode "toggle". Ids optional — nearest "DNA scanner" / "DNA Console"
in view otherwise (Genetics Lab this round: pod 25834 at 114,85, console
25839 at 114,84; other pods 25855 at 114,81, 24694 at 110,80).

How it works (all verified live):
  open/close/toggle — an EMPTY-HAND click on the pod toggles the door
    (toggle_open). Closing captures whoever stands ON the pod tile; opening
    drops the occupant beside it. Clicking with an item in hand does NOT
    toggle (item_interaction takes over) — the script empties the hand first.
  load <mob id> — DRAG the mob onto the pod (mouse_drop_receive accepts any
    carbon): capture without pull-chasing. Needs the mob adjacent to you and
    you in reach of the pod (verified: monkey diagonal-adjacent, me standing
    ON the pod tile). Far mobs: walk/pull them next to the pod first.
  lock/unlock — console action toggle_lock (bolts: a locked pod can't be
    opened even from inside without resisting). Needs the console linked.
Pod states: scanner (closed empty) / scanner_open / scanner_occupied
(closed + occupant) / *_unpowered / *_maintenance.
"""
import re

opts = args or {}
mode = (opts.get("mode") or "toggle").lower()
out = {"mode": mode, "verdict": []}


def close_all():
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        sk.tgui_send(id=m.group(1), type="close")
        time.sleep(0.12)


def empty_active_hand():
    for _ in range(2):
        inv = sk.inventory().text or ""
        act = [l for l in inv.split("\n") if "active_hand" in l]
        if act and ("empty" in act[0] or "obj" not in act[0]):
            return
        sk.key(key="X")
        time.sleep(0.4)


def nearest(name):
    s = sk.search(query=name, in_view=True, page_size=30)
    best, bestd = None, None
    for m in re.finditer(
            r'- obj (\d+) "%s[^"]*" at \d+,\d+(?:,\d+)? in .+? '
            r'\(dx (-?\d+), dy (-?\d+)\)' % name, s.text or ""):
        d2 = int(m.group(2)) ** 2 + int(m.group(3)) ** 2
        if bestd is None or d2 < bestd:
            best, bestd = int(m.group(1)), d2
    return best


def obj_state(oid, name):
    """icon_state: tile remembered-contents FIRST (updates live, works on dark
    tiles), search-line 'state=' as fallback (can lag a beat behind)."""
    s = sk.search(query=name, in_view=True, page_size=30)
    for m in re.finditer(r'- obj %d "[^"]*" at (\d+),(\d+)' % int(oid), s.text or ""):
        t = sk.tile(int(m.group(1)), int(m.group(2)), all=True)
        mm = re.search(r'- obj %d "[^"]*" \[([\w-]+)\]' % int(oid), t.text or "")
        if mm:
            return mm.group(1)
    for m in re.finditer(r'- obj %d "[^"]*"[^\n]*?state=([\w-]+)' % int(oid), s.text or ""):
        return m.group(1)
    return None


def read_console_row(console_id):
    """Open the console and return (window_id, {scannerLocked, scannerOpen})."""
    close_all()
    empty_active_hand()
    time.sleep(0.3)
    sk.click(object_id=console_id)
    time.sleep(1.8)
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        d = sk.tgui_window(id=m.group(1), max_chars=9000).text or ""
        if "closed: true" in d[:300] or not re.search(r"interface: DnaConsole\b", d):
            continue
        dd = d[d.find('"data"'):d.find('"data"') + 1200]
        row = {}
        for key in ("scannerLocked", "scannerOpen", "isScannerConnected"):
            mm = re.search(r'"%s": ([0-9.]+)' % key, dd)
            row[key] = float(mm.group(1)) if mm else None
        return m.group(1), row
    return None, None


pod_id = opts.get("scanner") and int(opts["scanner"]) or nearest("DNA scanner")
console_id = opts.get("console") and int(opts["console"]) or nearest("DNA Console")
out["ids"] = {"scanner": pod_id, "console": console_id}
if not pod_id:
    RESULT = {"ok": False, "note": "no DNA scanner in view"}
else:
    before = obj_state(pod_id, "DNA scanner")
    out["before"] = before
    if "unpowered" in (before or ""):
        out["verdict"].append("scanner UNPOWERED — fix area power first (nothing will move)")

    if mode in ("open", "close", "toggle"):
        g = bot.goto(object_id=pod_id)
        if g.failed and "already there" not in (g.text or ""):
            out["ok"] = False
        else:
            empty_active_hand()
            time.sleep(0.3)
            sk.click(object_id=pod_id)
            time.sleep(1.6)
            after = obj_state(pod_id, "DNA scanner")
            out["after"] = after
            out["ok"] = after != before
            if not out["ok"]:
                out["verdict"].append("state did not change (locked bolts? unpowered?)")
            if after == "scanner_occupied":
                out["verdict"].append("pod closed WITH occupant — captured")
            if mode == "open" and before == "scanner_occupied":
                out["verdict"].append("occupant released beside the pod")

    elif mode == "load":
        mob_id = opts.get("load") and int(opts["load"])
        if not mob_id:
            RESULT = {"ok": False, "note": "mode load needs args.load = <mob id>"}
        else:
            s = sk.search(query="monkey", in_view=True, page_size=30)  # geneticist's usual subject
            mob_tile, pod_tile = None, None
            for m in re.finditer(r'- mob %d "monkey[^"]*" at (\d+),(\d+)' % mob_id, s.text or ""):
                mob_tile = (int(m.group(1)), int(m.group(2)))
            s2 = sk.search(query="DNA scanner", in_view=True, page_size=30)
            for m in re.finditer(r'- obj %d "DNA scanner" at (\d+),(\d+)' % pod_id, s2.text or ""):
                pod_tile = (int(m.group(1)), int(m.group(2)))
            out["tiles"] = {"mob": mob_tile, "pod": pod_tile}
            g = bot.goto(object_id=mob_id)
            if g.failed and "already there" not in (g.text or ""):
                out["ok"] = False
                out["verdict"].append("cannot reach the mob to drag it")
            else:
                empty_active_hand()
                time.sleep(0.3)
                if mob_tile == pod_tile:
                    # mob stands IN the open pod — closing captures it
                    sk.click(object_id=pod_id)
                    time.sleep(1.6)
                else:
                    d = sk.drag(object_id=mob_id, onto_id=pod_id)
                    out["drag"] = (d.text or "")[:160]
                    time.sleep(1.6)
                after = obj_state(pod_id, "DNA scanner")
                out["after"] = after
                out["ok"] = after == "scanner_occupied"
                if not out["ok"]:
                    out["verdict"].append("pod did not take the mob (too far? pod open? not carbon? "
                                          "re-try: walk it onto the pod tile, then close)")

    elif mode in ("lock", "unlock", "toggle_lock"):
        if not console_id:
            RESULT = {"ok": False, "note": "lock/unlock needs the console (no console in view)"}
        else:
            g = bot.goto(object_id=console_id)
            if g.failed and "already there" not in (g.text or ""):
                out["ok"] = False
            else:
                wid, row = read_console_row(console_id)
                if not wid:
                    out["ok"] = False
                    out["verdict"].append("console window did not open (powered?)")
                elif (row or {}).get("isScannerConnected") != 1:
                    out["ok"] = False
                    out["verdict"].append("console not linked to a scanner — connect_scanner")
                else:
                    a = sk.tgui_act(id=wid, action="toggle_lock")
                    out["act"] = (a.text or "")[:150]
                    time.sleep(1.2)
                    d2 = sk.tgui_window(id=wid, max_chars=9000).text or ""
                    dd2 = d2[d2.find('"data"'):d2.find('"data"') + 1200]
                    mm = re.search(r'"scannerLocked": ([0-9.]+)', dd2)
                    locked = float(mm.group(1)) if mm else None
                    out["locked_after"] = locked
                    out["ok"] = locked is not None and locked != (row or {}).get("scannerLocked")
                    if not out["ok"]:
                        out["verdict"].append("lock state did not change")
                    sk.tgui_send(id=wid, type="close")
    else:
        RESULT = {"ok": False, "note": "unknown mode %r (open/close/toggle/load/lock/unlock)" % mode}

if "RESULT" not in dir():
    RESULT = out  # normal path: report the accumulated out dict
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
