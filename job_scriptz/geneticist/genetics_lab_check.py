# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""The geneticist's lab survey, ONE envelope: DNA console + DNA scanner (pod)
— the workstation that rewrites the crew.

Run: run_script {script: ".../job_scriptz/geneticist/genetics_lab_check.py",
                 args: {"console"?, "scanner"?, "x"?, "y"?}}
Ids optional — without them the script uses the NEAREST DNA Console and DNA
scanner in view (Genetics Lab this round: console 25839 at 114,84 + pod 25834
at 114,85; two more pods: 25855 at 114,81, 24694 at 110,80). Read-only, never
acts. Parses (all verified live):
  Console (interface DnaConsole, needs an EMPTY active hand to open):
    isScannerConnected, scannerOpen, scannerLocked, isViableSubject,
    subjectName/Status/Health/Damage/Enzymes, isInjectorReady,
    isScrambleReady/isJokerReady/isCrisprReady,
    storage.occupant[] {Alias, Name?, Discovered, Active, ByondRef?, Type?}.
  Pod icon_state (read from the search index — the pod tile is usually DARK):
    scanner (closed, empty, powered), scanner_open (open),
    scanner_occupied (closed WITH occupant), *_unpowered / *_maintenance.
Verdicts: console not linked (connect_scanner), pod unpowered (fix area
power), no viable occupant, pod locked (bolts — toggle_lock), N undiscovered
occupant mutations (all_check_discovery), injector/scramble on cooldown.
"""
import re

opts = args or {}
out = {"verdict": []}


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


def nearest(name, exclude=()):
    """Nearest in-view obj matching name, by (dx,dy) the search already gives."""
    s = sk.search(query=name, in_view=True, page_size=30)
    best, bestd = None, None
    for m in re.finditer(
            r'- obj (\d+) "%s[^"]*" at \d+,\d+(?:,\d+)? in .+? '
            r'\(dx (-?\d+), dy (-?\d+)\)' % name, s.text or ""):
        oid = int(m.group(1))
        if oid in exclude:
            continue
        d2 = int(m.group(2)) ** 2 + int(m.group(3)) ** 2
        if bestd is None or d2 < bestd:
            best, bestd = oid, d2
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


def num(seg_, key):
    m = re.search(r'"%s": (-?[\d.]+)' % key, seg_)
    return float(m.group(1)) if m else None


# ---- 1) locate machines
console_id = opts.get("console") and int(opts["console"]) or nearest("DNA Console")
pod_id = opts.get("scanner") and int(opts["scanner"]) or nearest("DNA scanner")
out["ids"] = {"console": console_id, "scanner": pod_id}

# ---- 2) the pod, from the map
if pod_id:
    st = obj_state(pod_id, "DNA scanner")
    out["pod"] = {"id": pod_id, "icon_state": st}
    if st and "unpowered" in st:
        out["verdict"].append("scanner UNPOWERED — fix the area's power (APC) first")
    if st and "maintenance" in st:
        out["verdict"].append("scanner panel open / in maintenance")
    if st == "scanner_open":
        out["verdict"].append("scanner door OPEN — no occupant can be scanned")
elif console_id:
    out["verdict"].append("no DNA scanner in view — console cannot work alone")
else:
    out["ok"] = False

# ---- 3) the console
if console_id:
    g = bot.goto(object_id=console_id)
    if g.failed and "already there" not in (g.text or ""):
        out["console"] = {"ok": False, "note": "cannot reach console"}
    else:
        empty_active_hand()
        close_all()
        time.sleep(0.4)
        sk.click(object_id=console_id)
        time.sleep(1.8)
        wid = None
        for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
            d = sk.tgui_window(id=m.group(1), max_chars=14000).text or ""
            if "closed: true" in d[:300]:
                continue
            if re.search(r"interface: DnaConsole\b", d):
                wid, data = m.group(1), d
                break
        if not wid:
            out["console"] = {"ok": False, "note": "window did not open (powered?)"}
        else:
            dd = data[data.find('"data"'):data.find('"data"') + 5200]
            row = {"is_scanner_connected": (num(dd, "isScannerConnected") or 0) == 1,
                   "scanner_open": (num(dd, "scannerOpen") or 0) == 1,
                   "scanner_locked": (num(dd, "scannerLocked") or 0) == 1,
                   "viable_subject": (num(dd, "isViableSubject") or 0) == 1,
                   "injector_ready": (num(dd, "isInjectorReady") or 0) == 1,
                   "scramble_ready": (num(dd, "isScrambleReady") or 0) == 1}
            nm = re.search(r'"subjectName": "([^"]*)"', dd)
            row["subject"] = nm.group(1) if nm else None
            occupant = []
            occ = dd[dd.find('"occupant"'):dd.find('"disk"') if dd.find('"disk"') > -1 else len(dd)]
            for chunk in re.split(r'\{\s*"Alias"', occ)[1:]:
                e = {"alias": (re.search(r'"([^"]+)"', chunk) or [None, "?"]).group(1),
                     "discovered": re.search(r'"Discovered": 1', chunk) is not None,
                     "active": re.search(r'"Active": 1', chunk) is not None}
                nm = re.search(r'"Name": "([^"]+)"', chunk)
                ref = re.search(r'"ByondRef": "([^"]+)"', chunk)
                ty = re.search(r'"Type": "([^"]+)"', chunk)
                if nm:
                    e["name"] = nm.group(1)
                if ref:
                    e["ref"] = ref.group(1)
                if ty:
                    e["type"] = ty.group(1)
                occupant.append(e)
            row["occupant_mutations"] = occupant
            out["console"] = row
            sk.tgui_send(id=wid, type="close")

            # ---- 4) verdicts
            if not row["is_scanner_connected"]:
                out["verdict"].append("console NOT linked to a scanner — connect_scanner")
            if row["scanner_locked"]:
                out["verdict"].append("scanner LOCKED (bolts) — occupant can't leave; toggle_lock")
            if row["scanner_open"]:
                out["verdict"].append("console says scannerOpen — no occupant inside")
            if not row["viable_subject"] and not row["scanner_open"]:
                out["verdict"].append("occupant present but NOT viable (dead/non-carbon?)")
            und = [e["alias"] for e in occupant if not e["discovered"]]
            if und:
                out["verdict"].append("%d undiscovered occupant mutations (%s) — "
                                      "all_check_discovery, or dna_injector_print with discover_all"
                                      % (len(und), ", ".join(und[:4])))
            if not row["injector_ready"]:
                out["verdict"].append("injector printing on cooldown")
            if not row["scramble_ready"]:
                out["verdict"].append("scramble on cooldown")
else:
    out["ok"] = False

out["ok"] = out.get("ok", True)
RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
