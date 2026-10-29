# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""One-envelope R&D LAB survey (read-only): the R&D console (points, queue,
experiments), the department protolathe + circuit imprinter + any department
techfab (materials from the shared ore silo, busy, queue via their Fabricator
tgui), the destructive analyzer, the Experi-Scanner, sheets on the lab
tables, and the brain-computer interface chamber (Experimentation Lab).
Verdicts tell you what the shift needs.

Run: run_script {script: ".../job_scriptz/scientist/rd_lab_check.py",
                 args: {"no_walk"?: true}}   # survey from where you stand
Stand in/near the R&D lab (MetaStation: R&D Console at (125,104),
protolathe at (125,102), circuit imprinter at (124,102), destructive
analyzer at (124,104), iron+glass sheets on the table at (122,102)).

Fork truths (live-verified):
  - Machines are DENSE and the lab is a MAZE from the lobby (windowed west
    shutters, firelocked north): the known-index lines still carry coords -
    the script walks via goto with the machine's own area name as fallback.
  - The R&D console (Techweb tgui) reads points (+1/sec passive) and queue;
    the lathes (Fabricator tgui) read materials/busy/queue.
  - The Experi-Scanner is the "experimental destructive scanner" (a tube);
    it may lie in the Science Lobby, not the lab - the known index finds it.
  - Opening ANY machine needs an EMPTY ACTIVE hand.
"""
import re

opts = args or {}
out = {"console": None, "lathes": [], "analyzer": None, "experi_scanner": None,
       "sheets": [], "bci_chamber": None, "verdict": []}


def active_obj():
    inv = sk.inventory().text or ""
    m = re.search(r"active_hand[^\n]*obj (\d+)", inv)
    return int(m.group(1)) if m else None


def empty_active_hand():
    dropped = []
    for attempt in range(3):
        inv = sk.inventory().text or ""
        act = [l for l in inv.split("\n") if "active_hand" in l]
        if act and ("empty" in act[0] or "obj" not in act[0]):
            if dropped:
                out["verdict"].append("dropped to free the active hand: %s" % dropped)
            return dropped
        if attempt == 0:
            sk.key(key="X")
            time.sleep(0.4)
        else:
            m = re.search(r"active_hand[^\n]*obj (\d+)", inv)
            if m:
                sk.key(key="Q")
                time.sleep(0.5)
                dropped.append(int(m.group(1)))
    return dropped


def search_rows(q, limit=60):
    rows = []
    for in_view in (True, False):
        s = sk.search(query=q, in_view=in_view, page_size=limit).text or ""
        for line in s.split("\n"):
            m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+).*?in ([^("]+)',
                         line.strip())
            if m:
                stale = "left the view" in line or "last seen" in line
                rows.append({"id": int(m.group(1)), "name": m.group(2),
                             "x": int(m.group(3)), "y": int(m.group(4)),
                             "area": (m.group(5) or "").strip(), "stale": stale})
        if rows and in_view:
            return rows
    return rows


def walk_to(row):
    if opts.get("no_walk"):
        return not row["stale"]
    empty_active_hand()
    g = bot.goto(x=row["x"], y=row["y"], max_steps=60)
    if "arrived" in (g.text or ""):
        return True
    if row.get("area"):
        g2 = sk.walk_to(area=row["area"], max_steps=120)
        return "arrived" in (g2.text or "") or "already" in (g2.text or "")
    return False


def open_tgui(mid, mname, iface):
    empty_active_hand()
    sk.click(object_id=mid, expect_name=mname)
    time.sleep(2.4)
    w = sk.tgui_windows(all=True).text or ""
    for mm in re.finditer(r"(  (tgui-window-\d+):\n(?:(?:    [^\n]*)\n)+)", w):
        blk = mm.group(1)
        if iface in blk and "closed: true" not in blk:
            obj = re.search(r"object: obj (\d+)", blk)
            if obj and int(obj.group(1)) != mid:
                continue
            return mm.group(2)
    return None


def close(wid):
    try:
        sk.tgui_send(id=wid, type="close")
    except Exception:
        pass


# ---- 1. R&D console
for r in search_rows("R&D Console", 10):
    if r["stale"]:
        continue
    if not walk_to(r):
        out["verdict"].append("could not reach the R&D console")
        break
    wid = open_tgui(r["id"], r["name"], "Techweb")
    if not wid:
        out["verdict"].append("R&D console window did not open")
        break
    d = sk.tgui_window(id=wid, max_chars=5000).text or ""
    pts = re.search(r'"points":\s*\{\s*"([^"]+)":\s*([0-9.]+)', d)
    q = re.search(r'"queue_nodes": (\[[^\]]*\])', d, re.S)
    sec = re.search(r'"sec_protocols": (\d+)', d)
    lock = re.search(r'"locked": (\d+)', d)
    exp_ids = re.findall(r'"(\d+)":\s*\{\s*"name": "([^"]+)"', d)
    out["console"] = {"id": r["id"],
                      "points": {pts.group(1): float(pts.group(2))} if pts else None,
                      "queue": (q.group(1) if q else "[]"),
                      "sec_protocols": sec and int(sec.group(1)),
                      "locked": bool(lock and int(lock.group(1))),
                      "experiments_known": len(exp_ids)}
    close(wid)
    break

# ---- 2. lathes: protolathe, circuit imprinter, department techfabs
seen = set()
for r in (search_rows("department protolathe", 20) +
          search_rows("circuit imprinter", 20) +
          search_rows("department techfab", 20)):
    if r["id"] in seen:
        continue
    seen.add(r["id"])
    if not walk_to(r):
        if r["stale"]:
            out["verdict"].append("%s not reachable (known at %s,%s)"
                                  % (r["name"], r["x"], r["y"]))
            continue
        # in view but the walk failed: try the click anyway (may be adjacent)
    wid = open_tgui(r["id"], r["name"], "Fabricator")
    if not wid:
        out["lathes"].append({"id": r["id"], "name": r["name"],
                              "error": "window did not open"})
        continue
    d = sk.tgui_window(id=wid, max_chars=4000).text or ""
    mats = {}
    for mm in re.finditer(r'"name": "([^"]+)",\s*"ref": "[^"]*",'
                          r'\s*"amount": (\d+)', d):
        if int(mm.group(2)) > 0:
            mats[mm.group(1)] = int(mm.group(2))
    b = re.search(r'"busy": (\d+)', d)
    h = re.search(r'"onHold": (null|true|false)', d)
    entry = {"id": r["id"], "name": r["name"], "x": r["x"], "y": r["y"],
             "materials": mats, "busy": bool(b and int(b.group(1))),
             "onHold": h and h.group(1)}
    out["lathes"].append(entry)
    close(wid)

# ---- 3. destructive analyzer (what's inside?)
for r in search_rows("destructive analyzer", 10):
    if r["stale"]:
        continue
    e = sk.examine(object_id=r["id"]).text or ""
    out["analyzer"] = {"id": r["id"], "x": r["x"], "y": r["y"],
                       "examine_lines": [l.strip()[:120] for l in e.split("\n")
                                         if l.strip().startswith("- ")][1:6]}
    break

# ---- 4. Experi-Scanner (may be anywhere; known index finds it)
for r in search_rows("experimental destructive scanner", 10):
    out["experi_scanner"] = {"id": r["id"], "name": r["name"],
                             "x": r["x"], "y": r["y"], "area": r["area"],
                             "in_view": not r["stale"]}
    break

# ---- 5. sheets on the lab tables (in view only)
s = sk.search(query="sheet", in_view=True, page_size=120).text or ""
for line in s.split("\n"):
    m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+).*?state=sheet-',
                 line.strip())
    if m and "left the view" not in line:
        out["sheets"].append({"id": int(m.group(1)), "name": m.group(2),
                              "x": int(m.group(3)), "y": int(m.group(4))})

# ---- 6. brain-computer interface chamber (Experimentation Lab)
for r in search_rows("brain-computer interface", 10):
    out["bci_chamber"] = {"id": r["id"], "x": r["x"], "y": r["y"],
                          "area": r["area"]}
    break

# ---- verdicts
if out["console"]:
    pts = out["console"].get("points") or {}
    v = list(pts.values())
    if v and v[0] > 500:
        out["verdict"].append("%.0f points banked on the console - research "
                              "or enqueue nodes NOW" % v[0])
    if out["console"]["locked"]:
        out["verdict"].append("console LOCKED - unlock it (toggleLock)")
for l in out["lathes"]:
    if l.get("error"):
        continue
    if not l["materials"]:
        out["verdict"].append("%s has NO materials - insert metal/glass "
                              "sheets" % l["name"])
    if l["busy"]:
        out["verdict"].append("%s is printing" % l["name"])
    if l.get("onHold") == "true":
        out["verdict"].append("%s is ON HOLD - resume it" % l["name"])
if out["experi_scanner"] and out["experi_scanner"].get("area") != "Research and Development":
    out["verdict"].append("Experi-Scanner is in the %s at (%s,%s) - bring it "
                          "to the lab for experiments"
                          % (out["experi_scanner"]["area"],
                             out["experi_scanner"]["x"],
                             out["experi_scanner"]["y"]))
if not out["sheets"]:
    out["verdict"].append("no sheets in view - the imprinter needs glass")
RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
