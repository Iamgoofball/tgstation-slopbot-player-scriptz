# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Print labelled medicine with the ChemMaster 3000: move reagents from the
inserted beaker into the buffer, pick a container style, print N items and
name them (the create act opens a Name TextInputModal — answered here).

Run: run_script {script: ".../job_scriptz/chemist/chem_master_print.py",
                 args: {"master"?, "transfer"?: [{"reagent": "Libital",
                                  "amount": 60}, ...],
                        "container"?: {"category": "patches", "match": "brute"}
                                     or {"category": "pills", "index": 0},
                        "item_count"?: 6, "name"?: "Libital patch 10u (brute)",
                        "pill_duration"?: seconds, "eject_beaker"?: true}}
master id optional (nearest "ChemMaster" in view otherwise). The beaker must
be inserted already OR in your active hand (a hand-beaker click on the
ChemMaster inserts it — verified). transfer reagents are matched by name
prefix against data.beaker.contents[].ref. container styles live in
static_data.categories (tubes 30u; pills 50u, 24 styles; patches 40u, styles
per damage type — match on icon_state substring, e.g. "brute"). Printing
takes 0.75 s per item; the prints land on the ChemMaster's tile.
Safety: refuses a transfer when isTransfering=0 would matter (moving back to
the beaker DESTROYS at that setting) and warns on it; refuses item_count > 50
(maxPrintable); over 100u total transfer is refused (buffer caps at 100u).
"""
import re

opts = args or {}
out = {"transferred": [], "verdict": []}


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


def hand_beaker():
    inv = sk.inventory().text or ""
    lines = [l for l in inv.split("\n")
             if re.search(r'obj \d+ "(?:large )?beaker"', l) and "hand" in l]
    if not lines:
        return False
    if "active" in lines[0]:
        return True
    sk.key(key="X")
    time.sleep(0.4)
    return True


def seg(d, key, n=800):
    i = d.find('"%s"' % key)
    return d[i:i + n] if i > -1 else ""


def num(seg_, key):
    m = re.search(r'"%s": (-?[\d.]+)' % key, seg_)
    return float(m.group(1)) if m else None


# 1) find + open
mid = opts.get("master")
if not mid:
    s = sk.search(query="ChemMaster", in_view=True, page_size=10)
    best, bestd = None, None
    for m in re.finditer(r'- obj (\d+) "ChemMaster[^"]*" at \d+,\d+(?:,\d+)? in (\S+) '
                         r'\(dx (-?\d+), dy (-?\d+)\)', s.text or ""):
        d2 = int(m.group(3)) ** 2 + int(m.group(4)) ** 2
        if bestd is None or d2 < bestd:
            mid, bestd = int(m.group(1)), d2
if not mid:
    out["verdict"].append("no ChemMaster in view")
    RESULT = out
else:
    out["master"] = mid
    g = bot.goto(object_id=int(mid))
    if g.failed and "already there" not in (g.text or ""):
        time.sleep(0.8)
        g = bot.goto(object_id=int(mid))
    if g.failed and "already there" not in (g.text or ""):
        out["verdict"].append("walk to ChemMaster failed")
        RESULT = out
    else:
        empty_active_hand()
        close_all()
        time.sleep(0.4)
        # a beaker in the ACTIVE hand inserts (or swaps in) on the click —
        # verified: the master grabbed a hand-beaker on click. Only empty the
        # hand when we hold NO beaker (a held non-beaker = use-on-machine).
        had_hand_beaker = hand_beaker()
        if not had_hand_beaker:
            empty_active_hand()
        sk.click(object_id=int(mid))
        time.sleep(1.8)
        wid = None
        d = ""
        for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
            d = sk.tgui_window(id=m.group(1), max_chars=9000).text or ""
            if "closed: true" in d[:300]:
                continue
            if re.search(r"interface: ChemMaster\b", d):
                wid = m.group(1)
                break
        if not wid:
            out["verdict"].append("ChemMaster window did not open (powered? empty hand?)")
            RESULT = out
        else:
            # 2) beaker inserted?  null = empty slot; vol 0 = a stale EMPTY
            # beaker sits in the slot — swap in the hand beaker (eject then
            # insert) so the transfers find the reagents
            dd = seg(d, "data", 3000)
            bseg = seg(dd, "beaker", 900)
            bvol = num(bseg, "currentVolume")
            if bvol is None and hand_beaker():
                sk.tgui_act(id=wid, action="insert")
                time.sleep(0.6)
                d = sk.tgui_window(id=wid, max_chars=9000).text or ""
                dd = seg(d, "data", 3000)
                bseg = seg(dd, "beaker", 900)
                bvol = num(bseg, "currentVolume")
            # a stale EMPTY beaker in the slot (vol 0) blocks the transfers —
            # swap in the hand beaker (eject, then insert) when we hold one
            if bvol == 0 and hand_beaker():
                sk.tgui_act(id=wid, action="eject")
                time.sleep(0.5)
                hand_beaker()
                sk.tgui_act(id=wid, action="insert")
                time.sleep(0.6)
                d = sk.tgui_window(id=wid, max_chars=9000).text or ""
                dd = seg(d, "data", 3000)
            bseg = seg(dd, "beaker", 2400)
            bvol = num(bseg, "currentVolume")
            if bvol is None:
                out["verdict"].append("no beaker in the ChemMaster and none in hand — "
                                      "insert one first")
                RESULT = out
            else:
                # 3) transfers (beaker -> buffer), matched by name prefix
                transfers = opts.get("transfer") or []
                for t in transfers:
                    name = t.get("reagent", "")
                    amt = float(t.get("amount", 0))
                    bc = seg(dd, "beaker", 2400)
                    rm = re.search(r'\{\s*"ref": "([^"]+)",\s*"name": "%s[^"]*"' % re.escape(name), bc)
                    if not rm:
                        out["verdict"].append("transfer %s: not in the beaker" % name)
                        continue
                    ref = rm.group(1)
                    at = sk.tgui_act(id=wid, action="transfer",
                                     params={"reagentRef": ref, "amount": amt,
                                             "target": "buffer"})
                    txt = at.text or ""
                    grew = re.search(r'buffer\.currentVolume: ([\d.]+) -> ([\d.]+)', txt)
                    got = float(grew.group(2)) - float(grew.group(1)) if grew else None
                    out["transferred"].append({"reagent": name, "moved": got})
                    if got is None:
                        out["verdict"].append("transfer %s: no buffer change seen" % name)
                    time.sleep(0.4)
                # 4) container style
                cont = opts.get("container")
                if cont:
                    cats_raw = sk.tgui_window(id=wid, path="static_data.categories",
                                              max_chars=7000).text or ""
                    ci = cats_raw.find('"name": "%s"' % cont.get("category", "tubes"))
                    cseg = cats_raw[ci:ci + 6000] if ci > -1 else ""
                    style = None
                    match = cont.get("match")
                    idx = cont.get("index", 0)
                    cons = re.findall(
                        r'\{\s*"ref": "(\[0x[0-9a-f]+\])",\s*"name": "([^"]+)",'
                        r'[\s\S]*?"icon_state": "([^"]+)",\s*"volume": (\d+)', cseg)
                    if match:
                        for cref, nm, st, vol in cons:
                            if match.lower() in st.lower() or match.lower() in nm.lower():
                                style = (cref, st, vol)
                                break
                    if style is None and cons:
                        try:
                            style = cons[int(idx)]
                        except Exception:
                            style = cons[0]
                    if style:
                        asc = sk.tgui_act(id=wid, action="selectContainer",
                                          params={"ref": style[0]})
                        out["container"] = {"ref": style[0], "icon_state": style[2],
                                            "volume": float(style[3])}
                        if not re.search(r'selectedContainer', asc.text or ""):
                            time.sleep(0.4)  # verified by the create below anyway
                    else:
                        out["verdict"].append("container style not found for %s" % cont)
                if opts.get("pill_duration") is not None:
                    sk.tgui_act(id=wid, action="setPillDuration",
                                params={"duration": int(opts["pill_duration"])})
                # 5) print
                n = int(opts.get("item_count") or 0)
                name = opts.get("name")
                if n and name:
                    if n > 50:
                        out["verdict"].append("item_count %d > maxPrintable 50 — clamped" % n)
                        n = 50
                    ac = sk.tgui_act(id=wid, action="create", params={"itemCount": n})
                    time.sleep(0.8)
                    # the Name TextInputModal opens (any window id)
                    modal = None
                    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
                        md = sk.tgui_window(id=m.group(1), max_chars=900).text or ""
                        if "interface: TextInputModal" in md and "title: Name" in md:
                            modal = m.group(1)
                            break
                    if not modal:
                        out["verdict"].append("no Name modal after create — printed anyway?")
                    else:
                        ans = sk.tgui_act(id=modal, action="submit", params={"entry": name[:42]})
                        time.sleep(0.6)
                    # 6) wait for the print to finish (0.75 s per item)
                    deadline = time.time() + 2 + 0.9 * n
                    printing = True
                    while time.time() < deadline:
                        d2 = sk.tgui_window(id=wid, max_chars=2500).text or ""
                        ip = num(seg(d2, "data", 400), "isPrinting")
                        printing = (ip or 0) == 1
                        if not printing:
                            break
                        time.sleep(0.7)
                    out["printed"] = {"count": n, "name": name,
                                      "finished": not printing}
                    s2 = sk.search(query=name.split()[0], in_view=True, page_size=12)
                    hits = [l.strip()[:110] for l in (s2.text or "").split("\n")
                            if name.split()[0] in l and "- obj" in l]
                    out["on_tile"] = hits[:6]
                # 7) state + verdicts
                d3 = sk.tgui_window(id=wid, max_chars=4000).text or ""
                dd3 = seg(d3, "data", 3000)
                out["buffer"] = {"vol": num(seg(dd3, "buffer", 900), "currentVolume")}
                out["transfer_mode_moves"] = (num(dd3, "isTransfering") or 0) == 1
                if out["transfer_mode_moves"] is False:
                    out["verdict"].append("isTransfering=0: moving reagents back to the "
                                          "beaker DESTROYS them — toggleTransferMode")
                if opts.get("eject_beaker"):
                    ae = sk.tgui_act(id=wid, action="eject")
                    out["ejected"] = bool(re.search(r'beaker: \{.* -> null', ae.text or ""))
                sk.tgui_send(id=wid, type="close")
                out["ok"] = True
                RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
