# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Drive the R&D Console (interface Techweb): read points, research a techweb
node, manage the server queue, lock the console.

Run: run_script {script: ".../job_scriptz/scientist/rdconsole_research.py",
                 args: {"mode": "status"|"research"|"enqueue"|"dequeue"|"lock",
                        "console"?: <obj id>,        # else the R&D Console in view
                        "node"?: "/datum/techweb_node/energy_manipulation"}}
Default mode "status". Node paths are /datum/techweb_node/* slugs (the
scientist guide lists the shift's priorities; the console's own node list
comes through as bare ids - pass the path, the game resolves it).

Fork truths (live-verified):
  - data.points {"General Research": X} grows PASSIVELY (+1/sec,
    points_last_tick) - never verify research by the points delta alone.
  - researchNode {node_path} verifies via the console's chat line
    "Successfully researched <Name>." (floating text + game say). Failures
    say "insufficient points" / "already researched" - the script surfaces
    the console's exact answer.
  - A successful research also UNLOCKS experiments (data.experiments grows,
    static_data.experiment_metadata.<id> appears).
  - enqueueNode/dequeueNode {node_path} verify via the ACT's data_changes
    ("queue_nodes: list of N -> M" - flat pairs: a node id + the researcher
    name, so ONE queued node moves the length by 2). Enqueue only accepts
    AVAILABLE nodes; failures say "Node enqueue failed: Either no techweb is
    found, node is already researched or is not available!". The queue
    empties itself again fast (the server autoresearches queued nodes) -
    leave useful nodes queued and let it work.
  - toggleLock flips data.locked (0 = open console, 1 = locked - do not
    leave it locked).
  - Opening needs an EMPTY ACTIVE hand (a held item attackbys the console).
"""
import re

opts = args or {}
mode = (opts.get("mode") or "status").lower()
out = {"mode": mode, "verdict": []}


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
    out["verdict"].append("could not free the active hand")
    return dropped


def find_console():
    cid = opts.get("console")
    for in_view in (True, False):
        s = sk.search(query="R&D Console", in_view=in_view, page_size=30).text or ""
        for line in s.split("\n"):
            m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+).*?in ([^("]+)',
                         line.strip())
            if not m:
                continue
            stale = "left the view" in line or "last seen" in line
            if in_view and stale:
                continue
            if cid and int(m.group(1)) != int(cid):
                continue
            return {"id": int(m.group(1)), "name": m.group(2),
                    "x": int(m.group(3)), "y": int(m.group(4)),
                    "area": (m.group(5) or "").strip()}
    return None


def open_console(cons):
    empty_active_hand()
    g = bot.goto(x=cons["x"], y=cons["y"], max_steps=60)  # dense: parks adjacent
    out["walk"] = "arrived" in (g.text or "")
    c = sk.click(object_id=cons["id"], expect_name=cons["name"])
    time.sleep(2.4)
    w = sk.tgui_windows(all=True).text or ""
    for mm in re.finditer(r"(  (tgui-window-\d+):\n(?:(?:    [^\n]*)\n)+)", w):
        blk = mm.group(1)
        if "Techweb" in blk and "closed: true" not in blk:
            obj = re.search(r"object: obj (\d+)", blk)
            if obj and int(obj.group(1)) != cons["id"]:
                continue
            return mm.group(2)
    return None


def read_console(wid):
    d = sk.tgui_window(id=wid, max_chars=6000).text or ""
    pts = re.search(r'"points":\s*\{\s*"([^"]+)":\s*([0-9.]+)', d)
    tick = re.search(r'"points_last_tick":\s*\{\s*"([^"]+)":\s*([0-9.]+)', d)
    q = re.search(r'"queue_nodes": (\[[^\]]*\])', d, re.S)
    exps = re.search(r'"experiments":', d)
    sec = re.search(r'"sec_protocols": (\d+)', d)
    lock = re.search(r'"locked": (\d+)', d)
    return {"points": {pts.group(1): float(pts.group(2))} if pts else None,
            "per_tick": {tick.group(1): float(tick.group(2))} if tick else None,
            "queue": (q.group(1) if q else "[]"),
            "has_experiments": bool(exps),
            "sec_protocols": sec and int(sec.group(1)),
            "locked": bool(lock and int(lock.group(1))),
            "_raw": d}


cons = find_console()
if not cons:
    RESULT = {"ok": False, "note": "no R&D Console in view/known - stand in "
                                   "the lab or pass args.console = <id>"}
else:
    out["console"] = {k: cons[k] for k in ("id", "name", "x", "y", "area")}
    wid = open_console(cons)
    if not wid:
        RESULT = {"ok": False, "note": "console window did not open "
                  "(unpowered? empty active hand needed?)"}
    else:
        st = read_console(wid)
        out["state"] = {k: v for k, v in st.items() if k != "_raw"}
        if mode == "status":
            if st["points"] and list(st["points"].values())[0] > 500:
                out["verdict"].append("%.0f points banked - spend them "
                                      "(research/enqueue nodes)" %
                                      list(st["points"].values())[0])
            out["ok"] = True
        elif mode in ("research", "enqueue", "dequeue"):
            node = opts.get("node")
            if not node:
                out["ok"] = False
                out["verdict"].append("mode %s needs args.node (a "
                                      "/datum/techweb_node/* path)" % mode)
            else:
                act = {"research": "researchNode", "enqueue": "enqueueNode",
                       "dequeue": "dequeueNode"}[mode]
                a = sk.tgui_act(id=wid, action=act, params={"node_path": node})
                t = a.text or ""
                out["ui_act"] = t[:400]
                ok_line = re.search(r"Successfully researched [^.]+\.", t)
                fail_line = re.search(r"Node \w+ failed[^.\n]*", t)
                out["console_said"] = (ok_line or fail_line) and \
                    (ok_line or fail_line).group(0)
                if mode == "research":
                    out["ok"] = bool(ok_line)
                else:
                    # verify via the ACT's data_changes: "queue_nodes: list of
                    # N -> M" - a post-sleep window read lies (the queue
                    # serializes collapsed to node ids + researcher names, and
                    # the server's autoresearch can consume an entry within
                    # seconds)
                    q = re.search(r"queue_nodes: list of (\d+) -> (\d+)", t)
                    if q:
                        out["queue_moved"] = {"from": int(q.group(1)),
                                              "to": int(q.group(2))}
                    if fail_line:
                        out["ok"] = False
                        out["verdict"].append("console refused: %s - the node "
                                              "must be AVAILABLE (prereqs "
                                              "researched, itself not)"
                                              % fail_line.group(0))
                    else:
                        delta = int(q.group(2)) - int(q.group(1)) if q else None
                        out["ok"] = delta is not None and \
                            ((mode == "enqueue" and delta > 0) or
                             (mode == "dequeue" and delta < 0))
                        if not out["ok"]:
                            out["verdict"].append("queue did not move as "
                                                  "expected - was the node "
                                                  "queued at all?")
                if not out["ok"] and not out.get("console_said"):
                    out["verdict"].append("console gave no success line - see "
                                          "ui_act")
        elif mode == "lock":
            a = sk.tgui_act(id=wid, action="toggleLock")
            time.sleep(1.2)
            st2 = read_console(wid)
            out["locked_after"] = st2["locked"]
            out["ok"] = st2["locked"] != st["locked"]
            if st2["locked"]:
                out["verdict"].append("console left LOCKED - unlock before "
                                      "leaving (toggleLock again)")
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
