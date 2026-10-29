# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Drive ONE exosuit fabricator: survey it, list its designs, queue/print a
part, load sheets, manage the queue.

Run: run_script {script: ".../job_scriptz/roboticist/exofab_control.py",
                 args: {"mode": "status"|"list"|"build"|"insert"
                             |"clear_queue"|"del"|"stop",
                        "fab"?: <obj id>,      # else the first in view
                        "design"?: "Cyborg Head" (name substring) or
                                   "/datum/design/borg_head" (exact path),
                        "now"?: true,          # build immediately (default true)
                        "wait"?: true,         # poll until the print finishes
                        "sheet"?: <obj id> or "sheet_name"?,  # insert mode
                        "pattern"?: regex, "category"?: substring,  # list mode
                        "index"?: 0}}          # del mode (queue index)
Default mode "status" (walks adjacent + opens the window read-only).

Fork truths (live-verified):
  - OPENING the fab needs an EMPTY active hand; INSERTING sheets needs a
    sheet IN the active hand + adjacency (the insert says "N sheets were
    added to the ore silo"; fab data then shows the silo's amounts).
  - build {designs: [design path], now} - the design is resolved from
    static_data.designs (keys are /datum/design/* paths, values carry
    name/cost/categories/constructionTime); the answer's data_changes shows
    queue + processing; cost is deducted AT QUEUE TIME (borg head 250 iron:
    5000 -> 4750).
  - queue entries: jobId/designPath/processing/timeLeft (deciseconds);
    prints eject onto the fab tile or a NEIGHBOR (a borg head landed at
    (111,95) for the fab at (110,95) - scan the 3x3 around the fab).
  - stop_queue pauses, clear_queue empties, del_queue_part {index} removes
    one job (the UI shows index = queue position).
"""
import re

opts = args or {}
mode = (opts.get("mode") or "status").lower()
out = {"mode": mode, "verdict": []}


def active_obj():
    inv = sk.inventory().text or ""
    m = re.search(r"active_hand[^\n]*obj (\d+)", inv)
    return int(m.group(1)) if m else None


def in_hands(oid):
    return ("obj %d " % oid) in (sk.inventory().text or "")


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
    out["verdict"].append("could not free the active hand")
    return dropped


def find_fab():
    fid = opts.get("fab") and int(opts["fab"])
    s = sk.search(query="exosuit fabricator", in_view=True, page_size=60).text or ""
    for line in s.split("\n"):
        m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+).*?state=(fab-\w+)', line.strip())
        if m and (not fid or int(m.group(1)) == fid):
            return {"id": int(m.group(1)), "x": int(m.group(3)),
                    "y": int(m.group(4)), "state": m.group(5)}
    return None


def open_fab(fab):
    empty_active_hand()
    # the fab tile is DENSE: goto parks on a neighboring tile ("next to it")
    g = bot.goto(x=fab["x"], y=fab["y"], max_steps=40)
    out["walk"] = "arrived" in (g.text or "")
    sk.click(object_id=fab["id"])
    time.sleep(2.2)
    w = sk.tgui_windows(all=True).text or ""
    for mm in re.finditer(r"(  (tgui-window-\d+):\n(?:(?:    [^\n]*)\n)+)", w):
        blk = mm.group(1)
        if "ExosuitFabricator" in blk and "closed: true" not in blk:
            return mm.group(2)
    return None


def read_fab(wid):
    d = sk.tgui_window(id=wid, max_chars=9000).text or ""
    mats = {}
    for mm in re.finditer(r'"name": "([^"]+)",\s*"ref": "[^"]*",\s*"amount": (\d+)', d):
        if int(mm.group(2)) > 0:
            mats[mm.group(1)] = int(mm.group(2))
    q = re.search(r'"queue": (\[[^\]]*\])', d, re.S)
    jobs = []
    if q and q.group(1).strip() != "[]":
        for jm in re.finditer(r'"designPath": "([^"]+)"[^}]*?"timeLeft": (\d+)', q.group(1)):
            jobs.append({"design": jm.group(1), "timeLeft": int(jm.group(2))})
    p = re.search(r'"processing": (\d+)', d)
    return {"materials": mats, "queue": jobs,
            "processing": bool(p and int(p.group(1))), "_raw": d}


def designs(wid):
    d = sk.tgui_window(id=wid, max_chars=30000, path="static_data.designs").text or ""
    rows = {}
    for mm in re.finditer(r'"(/datum/design/[\w_]+)": \{\s*"name": "([^"]+)"', d):
        rows[mm.group(1)] = mm.group(2)
    return rows


fab = find_fab()
if not fab:
    RESULT = {"ok": False, "note": "no exosuit fabricator in view - stand in "
                                   "the Robotics Lab or pass args.fab = <id>"}
else:
    out["fab"] = fab
    wid = open_fab(fab)
    if not wid:
        RESULT = {"ok": False, "note": "fab %s window did not open (unpowered?)"
                  % fab["id"]}
    else:
        st = read_fab(wid)
        out["state"] = {k: v for k, v in st.items() if k != "_raw"}
        if mode == "status":
            out["ok"] = True
        elif mode == "list":
            rows = designs(wid)
            pat = opts.get("pattern") and re.compile(opts["pattern"], re.I)
            cat = (opts.get("category") or "").lower()
            hits = []
            for path, name in rows.items():
                if pat and not pat.search(name) and not pat.search(path):
                    continue
                hits.append({"path": path, "name": name})
            out["designs"] = hits[:60]
            out["total"] = len(rows)
            out["ok"] = True
        elif mode == "build":
            want = opts.get("design")
            if not want:
                out["ok"] = False
                out["verdict"].append("mode build needs args.design (name or path)")
            else:
                rows = designs(wid)
                path = want if want.startswith("/datum/") else None
                if not path:
                    for p, n in rows.items():
                        if want.lower() in n.lower():
                            path = p
                            break
                if not path:
                    out["ok"] = False
                    out["verdict"].append("design %r not found (%d known - use "
                                          "mode list)" % (want, len(rows)))
                else:
                    before_iron = st["materials"].get("iron", 0)
                    a = sk.tgui_act(id=wid, action="build",
                                    params={"designs": [path],
                                            "now": bool(opts.get("now", True))})
                    out["ui_act"] = (a.text or "")[:300]
                    time.sleep(1.4)
                    st2 = read_fab(wid)
                    out["state_after"] = {k: v for k, v in st2.items() if k != "_raw"}
                    out["queued"] = len(st2["queue"]) > len(st["queue"]) or st2["processing"]
                    out["ok"] = out["queued"]
                    if not out["queued"]:
                        out["verdict"].append("queue did not grow (materials? "
                                              "design already queued?)")
                    if out["queued"] and opts.get("wait"):
                        deadline = 100
                        while deadline:
                            time.sleep(4)
                            st3 = read_fab(wid)
                            if not st3["processing"] and not st3["queue"]:
                                break
                            deadline -= 1
                        out["printed"] = st3["processing"] is False
                        # find the fresh part near the fab
                        s = sk.search(query="", in_view=True, page_size=250).text or ""
                        for line in s.split("\n"):
                            mm = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+)', line.strip())
                            if mm and abs(int(mm.group(3)) - fab["x"]) <= 1 \
                                    and abs(int(mm.group(4)) - fab["y"]) <= 1:
                                out["fresh_near_fab"] = out.get("fresh_near_fab", [])
                                out["fresh_near_fab"].append(
                                    {"id": int(mm.group(1)), "name": mm.group(2),
                                     "x": int(mm.group(3)), "y": int(mm.group(4))})
        elif mode == "insert":
            # find the sheet (args.sheet id or first in-view stack matching
            # args.sheet_name), grab it, then click the fab WITH it in hand
            sid = opts.get("sheet") and int(opts["sheet"])
            if not sid:
                nm = opts.get("sheet_name") or "iron"
                s = sk.search(query="sheet", in_view=True, page_size=200).text or ""
                for line in s.split("\n"):
                    m = re.match(r'- obj (\d+) "[^"]*" at (\d+),(\d+).*?state=sheet-',
                                 line.strip())
                    if m and nm.lower() in line.lower():
                        sid = int(m.group(1))
                        break
            if not sid:
                out["ok"] = False
                out["verdict"].append("no sheet found - pass args.sheet = <id>")
            else:
                out["sheet"] = sid
                empty_active_hand()
                if not in_hands(sid):
                    x = y = None
                    s = sk.search(query="", in_view=True, page_size=250).text or ""
                    for line in s.split("\n"):
                        m = re.match(r'- obj (%d) "[^"]*" at (\d+),(\d+)' % sid,
                                     line.strip())
                        if m:
                            x, y = int(m.group(2)), int(m.group(3))
                    if x is None:
                        out["verdict"].append("sheet %s not locatable in view" % sid)
                    else:
                        bot.goto(x=x, y=y, max_steps=40)
                        sk.click(object_id=sid)
                        time.sleep(0.8)
                if in_hands(sid) and active_obj() != sid:
                    sk.key(key="X")
                    time.sleep(0.4)
                if active_obj() == sid:
                    before_mats = dict(st["materials"])
                    # dense fab tile: goto parks adjacent
                    g = bot.goto(x=fab["x"], y=fab["y"], max_steps=40)
                    c = sk.click(object_id=fab["id"])   # attackby = insert
                    time.sleep(2.2)
                    ch = _pull_chat(3)
                    added = re.search(r"(\d+) [\w ]*sheets? were added to the ore silo", ch)
                    out["silo_message"] = added and added.group(0)
                    # the sheet is consumed now (hand empty): re-open the fab
                    # window and compare the silo-linked amounts
                    sk.click(object_id=fab["id"])
                    time.sleep(2.0)
                    st2 = None
                    w = sk.tgui_windows(all=True).text or ""
                    for mm in re.finditer(r"(  (tgui-window-\d+):\n(?:(?:    [^\n]*)\n)+)", w):
                        blk = mm.group(1)
                        if "ExosuitFabricator" in blk and "closed: true" not in blk:
                            st2 = read_fab(mm.group(2))
                    grew = {}
                    if st2:
                        grew = {k: v for k, v in st2["materials"].items()
                                if v > before_mats.get(k, 0)}
                    out["materials_grew"] = grew
                    out["ok"] = bool(added) or bool(grew)
                    if not out["ok"]:
                        out["verdict"].append("no ore-silo message and no "
                                              "material growth - insert failed "
                                              "(adjacency? actually a sheet?)")
                else:
                    out["ok"] = False
                    out["verdict"].append("sheet did not reach the active hand")
        elif mode == "clear_queue":
            a = sk.tgui_act(id=wid, action="clear_queue")
            time.sleep(1.2)
            st2 = read_fab(wid)
            out["ok"] = not st2["queue"]
        elif mode == "del":
            idx = opts.get("index") or 0
            a = sk.tgui_act(id=wid, action="del_queue_part", params={"index": idx})
            time.sleep(1.2)
            st2 = read_fab(wid)
            out["ok"] = len(st2["queue"]) < len(st["queue"])
        elif mode == "stop":
            a = sk.tgui_act(id=wid, action="stop_queue")
            time.sleep(1.2)
            out["ok"] = True
        else:
            RESULT = {"ok": False, "note": "unknown mode %r" % mode}
        try:
            sk.tgui_send(id=wid, type="close")
        except Exception:
            pass

if "RESULT" not in dir():
    RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
