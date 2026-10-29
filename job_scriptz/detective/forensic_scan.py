# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'),
          encoding='utf-8').read())
precheck()
"""Forensic scanner driver: scan ONE target (object or mob) and read the
ForensicScanner log window (prints / fibers / blood DNA). Optionally print
a paper report or clear the logs.

Run: run_script {script: ".../job_scriptz/detective/forensic_scan.py",
                 args: {"target": <obj or mob id>}       # or:
                 args: {"target_name": "Space Cigarettes packet",  # obj or mob
                        "x"?: tile, "y"?: tile,          # walk fallback
                        "wait_s"?: 13,                   # analysis time
                        "print"?: true,                  # paper report
                        "clear"?: true}}                 # wipe logs after

Fork truths (live-verified):
  - Scan = click the target WITH the scanner in the ACTIVE hand ("You scan
    X. The scanner is now analysing the results..." + a scan sound). The
    result lands in the scanner's log ~10-15 s later. Works on objects AND
    mobs (verified: a body scans like anything else).
  - A pristine target yields an entry with EMPTY dataEntries - "nothing
    found (clean target)" is a VALID result, not a failure (verified on an
    untouched packet + an unwounded body). Traces appear once the target
    has been handled or bled: the same parser reads prints (an md5-ish
    hash) + fibers ("Material from a brown trenchcoat.") off a handled
    backpack.
  - In-hand click on the scanner opens the ForensicScanner tgui:
    actions `clear`, `delete {index}`, `print`; data.logs[] = entries
    {scanTarget, scanTime, dataEntries[{category, data{}}]}; categories:
    Prints (Fingerprints, md5-ish hashes when unidentified), Fibers
    ("Material from a brown trenchcoat."), Blood.
  - A held scanner is an ACTIVE TOOL: clicking the worn backpack with it
    SCANS the backpack instead of storing it - store/retrieve with DRAG
    (sk.drag / the drag tool: scanner -> backpack id), not clicks.
  - To take it out: EMPTY-hand click the worn backpack (opens the storage
    panel), click the scanner's SCREEN icon inside, then close the panel
    via the panel's "close" screen button (never click the backpack with
    the scanner in hand).
  - The X hotkey swaps hands - a scanner in the NON-active hand needs only
    a swap, not retrieval. NEVER open a records console with the scanner
    held: item-in-hand = attackby (it scan-sweeps the console).
  - Dark tiles: scanning works in the dark; the log window warns "too dark
    to read!" but opens anyway.
"""
import json
import re

opts = args or {}
out = {"verdict": []}


def norm(t):
    return (t or "").replace("\\n", "\n")


def active_obj():
    for l in norm(sk.inventory().text or "").split("\n"):
        if "lhandactive" in l:
            m = re.match(r"- obj (\d+) \"([^\"]*)\"", l.strip())
            if m:
                return int(m.group(1)), m.group(2)
    return None, None


def find_worn_backpack():
    for l in norm(sk.inventory().text or "").split("\n"):
        m = re.match(r"- obj (\d+) \"([^\"]*)\".*in slot \"back\"",
                     l.strip())
        if m:
            return int(m.group(1)), m.group(2)
    return None, None


def screen_click_back(close_after=True):
    """Empty-hand: open the worn backpack, click the first 'forensic
    scanner' SCREEN icon into the active hand, close the panel."""
    bp_id, bp_name = find_worn_backpack()
    if not bp_id:
        out["verdict"].append("no worn backpack found")
        return False
    ao, _ = active_obj()
    if ao is not None:
        out["verdict"].append("active hand not empty - cannot open the "
                              "backpack panel safely")
        return False
    sk.click(object_id=bp_id)
    time.sleep(1.2)
    s = norm(sk.search(query="forensic scanner", page_size=8).text or "")
    shot = None
    for l in s.split("\n"):
        m = re.match(r"- obj (\d+) \"forensic scanner\" \[screen ", l.strip())
        if m:
            shot = int(m.group(1))
            break
    if not shot:
        out["verdict"].append("no forensic scanner inside the backpack")
        sk.click(object_id=bp_id)
        time.sleep(1.0)
        return False
    sk.click(object_id=shot)
    time.sleep(1.0)
    ao, nm = active_obj()
    got = ao is not None and "forensic scanner" in (nm or "")
    if got and close_after:
        s2 = norm(sk.search(query="close", page_size=10).text or "")
        for l in s2.split("\n"):
            m = re.match(r"- obj (\d+) \"close\" \[screen ", l.strip())
            if m:
                sk.click(object_id=int(m.group(1)))
                time.sleep(0.8)
                break
    return got


def scanner_in_hands():
    for l in norm(sk.inventory().text or "").split("\n"):
        m = re.match(r"- obj (\d+) \"([^\"]*)\"", l.strip())
        if m and "forensic scanner" in m.group(2) and \
                re.search(r"in slot \"(left|right) hand\"", l):
            return int(m.group(1))
    return None


def ensure_scanner_in_hand():
    ao, nm = active_obj()
    if ao is not None and "forensic scanner" in (nm or ""):
        return ao
    # already carried in a hand? swap hands to make it the active one
    hid = scanner_in_hands()
    if hid:
        sk.key(key="X")
        time.sleep(0.7)
        ao, nm = active_obj()
        if ao is not None and "forensic scanner" in (nm or ""):
            return ao
    # free the active hand (best effort: store whatever it holds), then
    # take the scanner out of the backpack via its open panel
    ao, nm = active_obj()
    if ao is not None:
        bp_id, _ = find_worn_backpack()
        if bp_id:
            sk.click(object_id=bp_id)
            time.sleep(1.0)
    if screen_click_back():
        ao, nm = active_obj()
        if ao is not None and "forensic scanner" in (nm or ""):
            return ao
    return None


def find_target():
    """Resolve the scan target - an obj OR a mob (scanning a suspect's
    body reads their prints/fibers/blood like anything else)."""
    tid = opts.get("target")
    tname = opts.get("target_name")
    if tid:
        for kind in ("obj", "mob"):
            s = norm(sk.search(query=tname or "", kind=kind,
                               page_size=20).text or "")
            for l in s.split("\n"):
                m = re.match(r"- %s (\d+) \"([^\"]*)\" at (\d+),(\d+)"
                             % kind, l.strip())
                if m and int(m.group(1)) == tid:
                    return {"kind": kind, "id": tid, "name": m.group(2),
                            "x": int(m.group(3)), "y": int(m.group(4))}
        return {"kind": "mob", "id": tid, "name": None,
                "x": None, "y": None}
    if tname:
        for kind in ("obj", "mob"):
            s = norm(sk.search(query=tname, kind=kind,
                               page_size=8).text or "")
            for l in s.split("\n"):
                m = re.match(r"- %s (\d+) \"([^\"]*)\" at (\d+),(\d+)"
                             % kind, l.strip())
                if m and re.search(tname, m.group(2), re.I) and \
                        "left the view" not in l:
                    return {"kind": kind, "id": int(m.group(1)),
                            "name": m.group(2),
                            "x": int(m.group(3)), "y": int(m.group(4))}
    return None


def scanner_logs(wid):
    """data.logs comes back as `items: N` + a pretty-printed JSON array
    (value: | block) - slice first '[' .. last ']' and loads it whole."""
    w = norm(sk.tgui_window(id=wid, path="data.logs",
                            max_chars=20000).text or "")
    i, j = w.find("["), w.rfind("]")
    if i < 0 or j <= i:
        return []
    try:
        arr = json.loads(w[i:j + 1])
        return [e for e in arr if isinstance(e, dict) and "scanTarget" in e]
    except Exception:
        return []


def open_scanner_window(sid):
    sk.click(object_id=sid)   # in-hand use
    time.sleep(1.8)
    wins = norm(sk.tgui_windows(all=True).text or "")
    for m in re.finditer(r"  (tgui-window-\d+):\n((?:    [^\n]*\n)+)", wins):
        if "ForensicScanner" in m.group(2) and \
                "closed: true" not in m.group(2):
            return m.group(1)
    return None


def close_window(wid):
    try:
        sk.tgui_send(id=wid, type="close")
        time.sleep(0.6)
    except Exception:
        pass


# ---- 1) scanner in the active hand
sid = ensure_scanner_in_hand()
if not sid:
    out["ok"] = False
    out["note"] = "no forensic scanner in hand or backpack"
else:
    out["scanner"] = sid
    # ---- 2) find + approach the target
    tgt = find_target()
    if not tgt:
        out["ok"] = False
        out["note"] = "target not found - pass target id or target_name"
    else:
        out["target"] = tgt
        if not opts.get("no_walk") and tgt.get("x"):
            g = bot.goto(x=tgt["x"], y=tgt["y"], max_steps=60)
            out["walk"] = "arrived" in (g.text or "")
        # ---- 3) scan it
        c = norm(sk.click(object_id=tgt["id"]).text or "")
        out["scan_click"] = c[:220]
        fired = "You scan" in c or "analysing" in c
        if not fired:
            out["verdict"].append("the click did not start a scan (check "
                                  "adjacency + that the scanner is the "
                                  "ACTIVE hand)")
        time.sleep(opts.get("wait_s", 13))
        # ---- 4) read the log window
        wid = open_scanner_window(sid)
        if not wid:
            out["ok"] = False
            out["note"] = ("ForensicScanner window did not open "
                           "(in-hand click failed)")
        else:
            out["wid"] = wid
            logs = scanner_logs(wid)
            out["log_count"] = len(logs)
            last = logs[-1] if logs else None
            out["last_scan"] = last
            if last and tgt.get("name") and \
                    tgt["name"].lower() in str(last.get("scanTarget", "")).lower():
                out["matched"] = True
                entries = last.get("dataEntries") or []
                out["findings"] = [("%s: %s" % (e.get("category"),
                                                ", ".join("%s" % k for k in
                                                          (e.get("data") or {}).keys())))
                                   for e in entries]
                out["verdict"].append(
                    "scan of %s: %s" % (last.get("scanTarget"),
                                        "; ".join(out["findings"]) or
                                        "nothing found (clean target)"))
            else:
                out["verdict"].append("last log entry did not match the "
                                      "target yet (analysis may still be "
                                      "running - raise wait_s)")
            if opts.get("print"):
                a = norm(sk.tgui_act(id=wid, action="print").text or "")
                out["print"] = a[:180]
            if opts.get("clear"):
                a = norm(sk.tgui_act(id=wid, action="clear").text or "")
                out["clear"] = a[:180]
            close_window(wid)
            out["ok"] = bool(out.get("matched"))

RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
