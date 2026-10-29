# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
_p = _os.path.join(_d, '..', 'common', 'watch_prelude.py')
if not _os.path.exists(_p):   # exec'd from a job_scriptz/<job> wrapper: one level deeper
    _p = _os.path.join(_d, '..', '..', 'common', 'watch_prelude.py')
exec(open(_p, encoding='utf-8').read())
precheck()
"""Generic driver for every tgui "Fabricator" lathe: department protolathe,
circuit imprinter, department techfabs (Cargo/Medical/Security/Service/...)
- NOT the exosuit fabricator (that is the ExosuitFabricator interface, the
roboticist job script drives it).

Run: run_script {script: ".../machines/fabricator_control.py",
                 args: {"mode": "status"|"list"|"build"|"insert"|"eject",
                        "machine"?: "department protolathe",  # name substring or obj id
                        "design"?: "screwdriver",             # name/path substring, or exact path
                        "amount"?: 1,
                        "wait"?: true,                        # poll the build to completion
                        "sheet"?: <obj id> or "sheet_name"?,  # insert mode
                        "mat"?: "glass", "amount_mat"?: 500}} # eject mode
Default mode "status". The machine is found in view, else via the known
index (its stale line still carries coords + the area name) and walked to.

Fork truths (live-verified on the department protolathe, Science):
  - The shared ORE SILO feeds every fab: materials[].amount is station-wide;
    inserting sheets says "N sheets were added to the ore silo"; 1 sheet =
    SHEET_MATERIAL_AMOUNT (100) units.
  - OPENING needs an EMPTY ACTIVE hand; INSERTING needs the sheet in the
    ACTIVE hand + adjacency (machine tiles are DENSE - bot.goto parks
    adjacent, "taken by ...: next to it").
  - build {design_path, amount} verifies via data_changes busy 0->1 (and a
    lathe_print sound); prints eject onto the machine tile or a neighbor -
    scan the 3x3 for the fresh item. Cost is deducted as it prints.
  - data model: data.materials[{name, ref, amount}], data.busy,
    data.onHold, data.queue, data.materialMaximum (the fab's own store cap,
    7500 on the Science protolathe), static_data.designs.*.path
    (SHEET_MATERIAL_AMOUNT = 100).
  - remove_mat {amount, ref} ejects units of one material back to sheets
    (the ref comes from data.materials[].ref) - not yet live-verified.
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
                out["verdict"].append("dropped to free the active hand: %s "
                                      "(recollect them later!)" % dropped)
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


def find_machine():
    want = opts.get("machine")
    rows = []
    for in_view in (True, False):
        s = sk.search(query=want or "fabricator", in_view=in_view,
                      page_size=80).text or ""
        for line in s.split("\n"):
            m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+)(?:,(\d+))?.*?'
                         r'in ([^("]+)', line.strip())
            if not m:
                continue
            stale = "left the view" in line or "last seen" in line
            if in_view and stale:
                continue
            name = m.group(2)
            if want:
                if str(want).isdigit():
                    if int(m.group(1)) != int(want):
                        continue
                elif want.lower() not in name.lower():
                    continue
            elif "fabricator" not in name.lower():
                continue
            rows.append({"id": int(m.group(1)), "name": name,
                         "x": int(m.group(3)), "y": int(m.group(4)),
                         "area": (m.group(6) or "").strip(),
                         "stale": stale})
        if rows:
            return rows[0]
    return None


def walk_to_machine(m):
    empty_active_hand()
    g = bot.goto(x=m["x"], y=m["y"], max_steps=60)   # dense tile: parks adjacent
    ok = "arrived" in (g.text or "")
    if not ok and m.get("area"):
        g2 = sk.walk_to(area=m["area"], max_steps=120)
        ok = "arrived" in (g2.text or "") or "already" in (g2.text or "")
    out["walk"] = ok
    return ok


def open_machine(mid, mname):
    empty_active_hand()
    c = sk.click(object_id=mid, expect_name=mname)
    time.sleep(2.4)
    w = sk.tgui_windows(all=True).text or ""
    for mm in re.finditer(r"(  (tgui-window-\d+):\n(?:(?:    [^\n]*)\n)+)", w):
        blk = mm.group(1)
        if "Fabricator" in blk and "closed: true" not in blk and \
                "ExosuitFabricator" not in blk:
            obj = re.search(r"object: obj (\d+)", blk)
            if obj and int(obj.group(1)) != mid:
                continue   # another machine's window
            return mm.group(2)
    return None


def read_fab(wid):
    d = sk.tgui_window(id=wid, max_chars=5000).text or ""
    mats = {}
    for mm in re.finditer(r'"name": "([^"]+)",\s*"ref": "([^"]+)",'
                          r'\s*"amount": (\d+)', d):
        mats[mm.group(1)] = {"ref": mm.group(2), "amount": int(mm.group(3))}
    b = re.search(r'"busy": (\d+)', d)
    h = re.search(r'"onHold": (null|true|false)', d)
    q = re.search(r'"queue": (\[[^\]]*\])', d, re.S)
    cap = re.search(r'"materialMaximum": (\d+)', d)
    return {"materials": mats,
            "busy": bool(b and int(b.group(1))),
            "onHold": h and h.group(1),
            "queue_raw": q and q.group(1)[:300],
            "materialMaximum": cap and int(cap.group(1)),
            "_raw": d}


def read_designs(wid):
    d = sk.tgui_window(id=wid, path="static_data.designs",
                       max_chars=40000).text or ""
    rows = []
    for mm in re.finditer(r'"path": "(/datum/design/[\w_]+)"', d):
        rows.append(mm.group(1))
    # pair each path with its name (the dump lists fields per design)
    named = {}
    for mm in re.finditer(r'"name": "([^"]+)",\s*(?:"[^"]*:\s*)?"path": '
                          r'"(/datum/design/[\w_]+)"', d):
        named[mm.group(2)] = mm.group(1)
    if not named:
        for p in rows:
            named[p] = p.split("/")[-1]
    return named


machine = find_machine()
if not machine:
    RESULT = {"ok": False, "note": "no matching fabricator - pass args.machine "
                                   "(name substring or obj id) and stand nearby"}
else:
    out["machine"] = {k: machine[k] for k in ("id", "name", "x", "y", "area")}
    if not walk_to_machine(machine):
        out["verdict"].append("could not reach %s" % machine["name"])
    wid = open_machine(machine["id"], machine["name"])
    if not wid:
        RESULT = {"ok": False, "note": "fabricator %s window did not open "
                  "(unpowered? empty active hand?)" % machine["id"]}
    else:
        st = read_fab(wid)
        out["state"] = {k: v for k, v in st.items() if k != "_raw"}
        if mode == "status":
            out["ok"] = True
        elif mode == "list":
            named = read_designs(wid)
            pat = opts.get("pattern") and re.compile(opts["pattern"], re.I)
            hits = [{"path": p, "name": n} for p, n in named.items()
                    if not pat or pat.search(n) or pat.search(p)]
            out["designs"] = hits[:80]
            out["total"] = len(named)
            out["ok"] = True
        elif mode == "build":
            want = opts.get("design")
            if not want:
                out["ok"] = False
                out["verdict"].append("mode build needs args.design")
            else:
                named = read_designs(wid)
                path = want if want.startswith("/datum/") else None
                if not path:
                    for p, n in named.items():
                        if want.lower() in n.lower() or want.lower() in p.lower():
                            path = p
                            break
                if not path:
                    out["ok"] = False
                    out["verdict"].append("design %r not found (%d known - "
                                          "use mode list)" % (want, len(named)))
                else:
                    amount = int(opts.get("amount") or 1)
                    a = sk.tgui_act(id=wid, action="build",
                                    params={"design_path": path,
                                            "amount": amount})
                    out["ui_act"] = (a.text or "")[:400]
                    time.sleep(2.0)
                    st2 = read_fab(wid)
                    # verify via the act's data_changes (busy 0->1, or the
                    # queue growing when another job is already printing) -
                    # a fast print may be DONE by the time we re-read (busy
                    # back to 0), so the post-sleep busy alone lies
                    t_act = a.text or ""
                    out["busy_started"] = bool(re.search(r"busy: \d+ -> \d+", t_act)) \
                        or bool(re.search(r"queue: list of \d+ -> \d+", t_act)) \
                        or st2["busy"]
                    out["ok"] = out["busy_started"]
                    if not out["ok"]:
                        out["verdict"].append("build did not start (materials? "
                                              "design unavailable?)")
                    if out["ok"] and opts.get("wait"):
                        deadline = 40
                        while deadline:
                            time.sleep(3)
                            st3 = read_fab(wid)
                            if not st3["busy"]:
                                break
                            deadline -= 1
                        # view lines, not search lines: "- x,y (dx, dy) ...: obj ID "name" ..."
                        v = sk.view(page_size=400).text or ""
                        fresh = []
                        for line in v.split("\n"):
                            vm = re.match(r'- (\d+),(\d+) \(dx -?\d+, dy -?\d+\)',
                                          line.strip())
                            if not vm:
                                continue
                            vx, vy = int(vm.group(1)), int(vm.group(2))
                            if abs(vx - machine["x"]) > 1 or \
                                    abs(vy - machine["y"]) > 1:
                                continue
                            for om in re.finditer(r'obj (\d+) "([^"]*)"', line):
                                fresh.append({"id": int(om.group(1)),
                                              "name": om.group(2),
                                              "x": vx, "y": vy})
                        out["printed_nearby"] = fresh[:20]
        elif mode == "insert":
            sid = opts.get("sheet") and int(opts["sheet"])
            if not sid:
                nm = opts.get("sheet_name") or "iron"
                s = sk.search(query="sheet", in_view=True, page_size=200).text or ""
                for line in s.split("\n"):
                    m = re.match(r'- obj (\d+) "[^"]*" at (\d+),(\d+).*?'
                                 r'state=sheet-', line.strip())
                    if m and "left the view" not in line \
                            and nm.lower() in line.lower():
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
                    # bare obj ids are NOT searchable text (search matches
                    # name/icon_state only) - find the sheet by name/icon in
                    # the view, then the known index, and match args.sheet
                    nm = opts.get("sheet_name") or "sheet"
                    for scope in ({"in_view": True, "page_size": 60},
                                  {"page_size": 60}):
                        s = sk.search(query=nm, **scope).text or ""
                        for line in s.split("\n"):
                            m = re.match(r'- obj (\d+) "[^"]*" at (\d+),(\d+)'
                                         r'.*?state=sheet-', line.strip())
                            if m and int(m.group(1)) == sid \
                                    and "left the view" not in line:
                                x, y = int(m.group(2)), int(m.group(3))
                        if x is not None:
                            break
                    if x is None:
                        out["verdict"].append("sheet %s not in view" % sid)
                    else:
                        bot.goto(x=x, y=y, max_steps=40)
                        sk.click(object_id=sid)
                        time.sleep(0.9)
                if in_hands(sid) and active_obj() != sid:
                    sk.key(key="X")
                    time.sleep(0.4)
                if active_obj() == sid:
                    before = {k: v["amount"] for k, v in st["materials"].items()}
                    # the pickup moved us to the sheet's tile: walk BACK to
                    # the machine (dense: parks adjacent) with the sheet
                    # still in the active hand, then click = attackby insert
                    g = bot.goto(x=machine["x"], y=machine["y"], max_steps=60)
                    out["walk_back"] = "arrived" in (g.text or "")
                    c = sk.click(object_id=machine["id"])
                    time.sleep(2.4)
                    ch = _pull_chat(3) + " | " + (c.text or "")
                    added = re.search(r"(\d+) [\w ]*sheets? were added to "
                                      r"the ore silo", ch)
                    out["silo_message"] = added and added.group(0)
                    # re-open to compare silo amounts (the window may have
                    # dropped out of range during the sheet walk)
                    st2 = None
                    w = sk.tgui_windows(all=True).text or ""
                    for mm in re.finditer(r"(  (tgui-window-\d+):\n"
                                          r"(?:(?:    [^\n]*)\n)+)", w):
                        blk = mm.group(1)
                        if "Fabricator" in blk and "closed: true" not in blk \
                                and "ExosuitFabricator" not in blk:
                            st2 = read_fab(mm.group(2))
                    if st2 is None:
                        sk.click(object_id=machine["id"])
                        time.sleep(2.0)
                        st2 = read_fab(wid)
                    grew = {}
                    if st2:
                        grew = {k: v["amount"] for k, v in st2["materials"].items()
                                if v["amount"] > before.get(k, 0)}
                    out["materials_grew"] = grew
                    out["ok"] = bool(added) or bool(grew)
                    if not out["ok"]:
                        out["verdict"].append("no ore-silo message and no "
                                              "growth - insert failed")
                else:
                    out["ok"] = False
                    out["verdict"].append("sheet did not reach the active hand")
        elif mode == "eject":
            mat = opts.get("mat")
            n = int(opts.get("amount_mat") or 100)
            if not mat or mat not in st["materials"]:
                out["ok"] = False
                out["verdict"].append("mode eject needs args.mat from %s"
                                      % sorted(st["materials"]))
            else:
                a = sk.tgui_act(id=wid, action="remove_mat",
                                params={"amount": n,
                                        "ref": st["materials"][mat]["ref"]})
                out["ui_act"] = (a.text or "")[:250]
                time.sleep(1.5)
                st2 = read_fab(wid)
                out["amount_now"] = st2["materials"].get(mat, {}).get("amount")
                out["ok"] = out["amount_now"] is not None \
                    and out["amount_now"] < st["materials"][mat]["amount"]
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
