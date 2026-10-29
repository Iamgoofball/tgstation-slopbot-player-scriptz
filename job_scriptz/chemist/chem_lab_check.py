# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""The chemist's lab survey, ONE envelope: chem dispenser + reaction chamber
(chem heater) + ChemMaster 3000 — the workstation that heals the station.

Run: run_script {script: ".../job_scriptz/chemist/chem_lab_check.py",
                 args: {"dispenser"?, "chamber"?, "master"?,
                        "x"?, "y"?, "reactions_wait"?: seconds}}
Ids optional — without them the script surveys the NEAREST of each machine
in view (the Pharmacy has two workstations: south = dispenser/chamber/master
at 103,101 / 102,99 / 103,99; north-east = 104,106 / 102,106 / 104,105 this
round). Read-only EXCEPT it never acts. Parses (all verified live):
  ChemDispenser: data.displayedUnits/maxUnits (energy), amount, beaker
    {currentVolume, pH, contents[]}; chemicals[] (25 dispensables).
  ChemHeater: targetTemp/currentTemp/isActive, beaker, acidicBufferVol/
    basicBufferVol/dispenseVolume, activeReactions[] {name, quality, danger,
    overheat, reactedVol, targetVol}.
  ChemMaster: beaker/buffer {contents[] name/volume/purity/overdose},
    isPrinting, isTransfering, selectedContainerCategory.
Verdicts: dispenser energy < 20%, chamber OFF with reactions pending, any
active reaction quality < 0.6 (purity dropping — buffer the pH), a danger
flag on a reaction, ChemMaster isTransfering 0 (transfer mode DESTROYS
reagents — toggleTransferMode!), chamber buffers < 5u.
"""
import re

opts = args or {}
wait_s = float(opts.get("reactions_wait", 3))
out = {"machines": {}, "verdict": []}


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


def open_machine(oid, iface):
    g = bot.goto(object_id=oid)
    if g.failed and "already there" not in (g.text or ""):
        return None, None
    empty_active_hand()
    close_all()
    time.sleep(0.4)
    sk.click(object_id=oid)
    time.sleep(1.8)
    w = sk.tgui_windows().text or ""
    for m in re.finditer(r"(tgui-window-\d+):", w):
        d = sk.tgui_window(id=m.group(1), max_chars=12000).text or ""
        if "closed: true" in d[:300]:
            continue
        if re.search(r"interface: %s\b" % iface, d):
            return m.group(1), d
    return None, None


def seg(d, key, n=700):
    i = d.find('"%s"' % key)
    return d[i:i + n] if i > -1 else ""


def num(seg_, key):
    m = re.search(r'"%s": (-?[\d.]+)' % key, seg_)
    return float(m.group(1)) if m else None


# ---- 1) locate the three machines
ids = {k: opts.get(k) for k in ("dispenser", "chamber", "master")}
if not ids["dispenser"]:
    ids["dispenser"] = nearest("chem dispenser")
if not ids["master"]:
    ids["master"] = nearest("ChemMaster")
if not ids["chamber"]:
    ids["chamber"] = nearest("reaction chamber")
out["ids"] = ids

# ---- 2) dispenser
if ids["dispenser"]:
    wid, d = open_machine(int(ids["dispenser"]), "ChemDispenser")
    if d:
        row = {"energy": num(seg(d, "data", 400), "displayedUnits"),
               "max_energy": num(seg(d, "data", 400), "displayedMaxUnits"),
               "amount": num(seg(d, "data", 400), "amount")}
        b = seg(d, "beaker", 800)
        row["beaker"] = {"vol": num(b, "currentVolume"), "pH": num(b, "pH"),
                         "contents": re.findall(r'"name": "([^"]+)",\s*"volume": ([\d.]+)', b)}
        out["machines"]["dispenser"] = row
        sk.tgui_send(id=wid, type="close")
    else:
        out["machines"]["dispenser"] = {"ok": False, "note": "window did not open"}

# ---- 3) reaction chamber
if ids["chamber"]:
    wid, d = open_machine(int(ids["chamber"]), "ChemHeater")
    if d:
        dd = seg(d, "data", 2200)
        row = {"target_temp": num(dd, "targetTemp"), "current_temp": num(dd, "currentTemp"),
               "active": (num(dd, "isActive") or 0) == 1,
               "acid_buf": num(dd, "acidicBufferVol"), "basic_buf": num(dd, "basicBufferVol")}
        b = seg(dd, "beaker", 800)
        row["beaker"] = {"vol": num(b, "currentVolume"), "pH": num(b, "pH"),
                         "contents": re.findall(r'"name": "([^"]+)",\s*"volume": ([\d.]+)', b)}
        ar = seg(d, "activeReactions", 1600)
        rx = []
        for chunk in re.split(r'\{\s*"name"', ar)[1:]:
            rx.append({"name": (re.search(r'"([^"]+)"', chunk) or [None, "?"]).group(1),
                       "quality": num(chunk, "quality"), "danger": re.search(r'"danger": (?!null|0)', chunk) is not None,
                       "reacted": num(chunk, "reactedVol"), "target": num(chunk, "targetVol")})
        row["reactions"] = rx
        out["machines"]["chamber"] = row
        if rx and wait_s > 0:
            time.sleep(wait_s)
            d2 = sk.tgui_window(id=wid, max_chars=6000).text or ""
            ar2 = seg(d2, "activeReactions", 1600)
            for chunk, old in zip(re.split(r'\{\s*"name"', ar2)[1:], rx):
                q = num(chunk, "quality")
                if q is not None:
                    old["quality_after_%ds" % int(wait_s)] = q
        sk.tgui_send(id=wid, type="close")
    else:
        out["machines"]["chamber"] = {"ok": False, "note": "window did not open"}

# ---- 4) ChemMaster
if ids["master"]:
    wid, d = open_machine(int(ids["master"]), "ChemMaster")
    if d:
        dd = seg(d, "data", 4000)
        row = {"is_printing": (num(dd, "isPrinting") or 0) == 1,
               "transfer_mode_moves": (num(dd, "isTransfering") or 0) == 1,
               "container": re.search(r'"selectedContainerCategory": "([^"]+)"', dd).group(1)
               if re.search(r'"selectedContainerCategory": "([^"]+)"', dd) else None}
        for key in ("beaker", "buffer"):
            c = seg(dd, key, 1600)
            row[key] = {"vol": num(c, "currentVolume"),
                        "contents": re.findall(r'"name": "([^"]+)",\s*"volume": ([\d.]+)', c)}
        out["machines"]["master"] = row
        sk.tgui_send(id=wid, type="close")
    else:
        out["machines"]["master"] = {"ok": False, "note": "window did not open"}

# ---- 5) verdicts
disp = out["machines"].get("dispenser") or {}
if disp.get("max_energy") and disp.get("energy") is not None:
    pct = 100.0 * disp["energy"] / disp["max_energy"]
    if pct < 20:
        out["verdict"].append("dispenser energy LOW: %d%%" % pct)
ch = out["machines"].get("chamber") or {}
if ch.get("reactions") and not ch.get("active"):
    out["verdict"].append("chamber OFF with reactions pending — power it")
for r in ch.get("reactions", []):
    if r.get("danger"):
        out["verdict"].append("reaction %s has a DANGER flag — watch temp" % r["name"])
    q = r.get("quality")
    q2 = r.get("quality_after_%ds" % int(wait_s))
    if (q is not None and q < 0.6) or (q2 is not None and q2 < 0.6):
        out["verdict"].append("reaction %s purity %s (<0.6) — buffer the pH"
                              % (r["name"], q2 if q2 is not None else q))
if ch.get("current_temp") is not None and ch.get("target_temp") is not None \
        and ch.get("active") and abs(ch["current_temp"] - ch["target_temp"]) > 100:
    out["verdict"].append("chamber heating %s -> %s K" % (ch["current_temp"], ch["target_temp"]))
for bk in ("acid_buf", "basic_buf"):
    if ch.get(bk) is not None and ch[bk] < 5:
        out["verdict"].append("chamber %s low (%su) — draw from a buffer bottle" % (bk, ch[bk]))
mst = out["machines"].get("master") or {}
if mst.get("transfer_mode_moves") is False:
    out["verdict"].append("ChemMaster isTransfering=0: transfers to beaker DESTROY "
                          "reagents — toggleTransferMode before moving anything back")
out["ok"] = any((v or {}).get("ok", True) for v in out["machines"].values())
RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
