# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Drive the reaction chamber (the chem heater): insert/eject a beaker, set
the target temperature, toggle power, adjust pH with its built-in buffers,
watch a reaction run.

Run: run_script {script: ".../job_scriptz/chemist/chem_heater.py",
                 args: {"chamber"?, "temp"?: K, "power"?: true|false,
                        "insert"?: true, "eject"?: true,
                        "ph"?: {"direction": "basic"|"acid", "units": 1-10},
                        "watch"?: seconds}}
chamber id optional (nearest "reaction chamber" in view otherwise).
insert needs a beaker in your active hand (empty hand first — a held item
click = use-on-machine). ph sets disp_vol {target: units} then presses the
buffer once (verified: basicBuffer pH 7->8 at 30u with 1u; the chamber holds
20u of each buffer, draw more with acidBuffer/basicBuffer {target: -100} from
a beaker that holds that buffer). watch polls currentTemp + activeReactions
quality. Verified live: temperature 300->500 act, power 0->1, buffer pH +1.
Overheat facts (skill §6/§8): Aiuri 315, Synthflesh 325, Multiver 410,
Inacusiate 500, Oculine 600 — the verdict flags target temps above those
when a matching reaction is listed.
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


def seg(d, key, n=800):
    i = d.find('"%s"' % key)
    return d[i:i + n] if i > -1 else ""


def num(seg_, key):
    m = re.search(r'"%s": (-?[\d.]+)' % key, seg_)
    return float(m.group(1)) if m else None


def read_all(d):
    dd = seg(d, "data", 2400)
    row = {"target_temp": num(dd, "targetTemp"), "current_temp": num(dd, "currentTemp"),
           "active": (num(dd, "isActive") or 0) == 1,
           "acid_buf": num(dd, "acidicBufferVol"), "basic_buf": num(dd, "basicBufferVol"),
           "disp_vol": num(dd, "dispenseVolume")}
    b = seg(dd, "beaker", 900)
    row["beaker"] = {"vol": num(b, "currentVolume"), "pH": num(b, "pH"),
                     "contents": re.findall(r'"name": "([^"]+)",\s*"volume": ([\d.]+)', b)}
    ar = seg(d, "activeReactions", 1600)
    rx = []
    for chunk in re.split(r'\{\s*"name"', ar)[1:]:
        rx.append({"name": (re.search(r'"([^"]+)"', chunk) or [None, "?"]).group(1),
                   "quality": num(chunk, "quality"),
                   "reacted": num(chunk, "reactedVol"), "target": num(chunk, "targetVol")})
    row["reactions"] = rx
    return row


OVERHEAT = {"Aiuri": 315, "Synthflesh": 325, "Multiver": 410,
            "Inacusiate": 500, "Oculine": 600}

# 1) find + open
cid = opts.get("chamber")
if not cid:
    s = sk.search(query="reaction chamber", in_view=True, page_size=10)
    best, bestd = None, None
    for m in re.finditer(r'- obj (\d+) "reaction chamber" at \d+,\d+(?:,\d+)? in (\S+) '
                         r'\(dx (-?\d+), dy (-?\d+)\)', s.text or ""):
        d2 = int(m.group(3)) ** 2 + int(m.group(4)) ** 2
        if bestd is None or d2 < bestd:
            cid, bestd = int(m.group(1)), d2
if not cid:
    out["verdict"].append("no reaction chamber in view")
    RESULT = out
else:
    out["chamber"] = cid
    g = bot.goto(object_id=int(cid))
    if g.failed and "already there" not in (g.text or ""):
        time.sleep(0.8)
        g = bot.goto(object_id=int(cid))
    if g.failed and "already there" not in (g.text or ""):
        out["verdict"].append("walk to chamber failed")
        RESULT = out
    else:
        empty_active_hand()
        close_all()
        time.sleep(0.4)
        sk.click(object_id=int(cid))
        time.sleep(1.8)
        w = sk.tgui_windows().text or ""
        wid = None
        for m in re.finditer(r"(tgui-window-\d+):", w):
            d = sk.tgui_window(id=m.group(1), max_chars=9000).text or ""
            if "closed: true" in d[:300]:
                continue
            if re.search(r"interface: ChemHeater\b", d):
                wid = m.group(1)
                break
        if not wid:
            out["verdict"].append("chamber window did not open (powered? empty hand?)")
            RESULT = out
        else:
            # 2) actions, each verified from its act answer
            if opts.get("insert"):
                ai = sk.tgui_act(id=wid, action="insert")
                ok = re.search(r'beaker: null -> \{', ai.text or "")
                out["inserted"] = bool(ok)
                if not ok:
                    out["verdict"].append("insert failed — beaker in your ACTIVE hand?")
            if opts.get("temp") is not None:
                t = max(0, min(1000, float(opts["temp"])))
                at = sk.tgui_act(id=wid, action="temperature", params={"target": t})
                m = re.search(r'targetTemp: ([\d.]+) -> ([\d.]+)', at.text or "")
                out["target_temp"] = float(m.group(2)) if m else None
                for nm, oh in OVERHEAT.items():
                    if re.search(r'"%s"' % nm, sk.tgui_window(id=wid, max_chars=9000).text or "") \
                            and t > oh:
                        out["verdict"].append("target %s K is above %s's overheat %s K"
                                              % (t, nm, oh))
            if "power" in opts:
                want = bool(opts.get("power"))
                d0 = sk.tgui_window(id=wid, max_chars=9000).text or ""
                cur = (num(seg(d0, "data", 400), "isActive") or 0) == 1
                if cur != want:
                    ap = sk.tgui_act(id=wid, action="power")
                    m = re.search(r'isActive: (\d) -> (\d)', ap.text or "")
                    out["power"] = (m and m.group(2) == "1") if m else want
                else:
                    out["power"] = cur
            ph = opts.get("ph")
            if ph:
                direction = ph.get("direction", "basic")
                units = max(1, min(10, int(ph.get("units", 1))))
                av = sk.tgui_act(id=wid, action="disp_vol", params={"target": units})
                ab = sk.tgui_act(id=wid, action=direction + "Buffer", params={"target": 1})
                pm = re.search(r'beaker\.pH: (-?[\d.]+) -> (-?[\d.]+)', ab.text or "")
                if pm:
                    out["ph"] = {"direction": direction, "from": float(pm.group(1)),
                                 "to": float(pm.group(2))}
                else:
                    out["verdict"].append("pH adjust: no pH change seen (beaker in? "
                                          "buffer empty? too far from the machine?)")
            # 3) watch
            watch = float(opts.get("watch", 2))
            d = sk.tgui_window(id=wid, max_chars=9000).text or ""
            row = read_all(d)
            if watch > 0 and row["reactions"]:
                for _ in range(int(watch)):
                    time.sleep(1.0)
                row2 = read_all(sk.tgui_window(id=wid, max_chars=9000).text or "")
                row["reactions"] = row2["reactions"]
                row["current_temp"] = row2["current_temp"]
            out["state"] = row
            for r in row["reactions"]:
                if r.get("quality") is not None and r["quality"] < 0.6:
                    out["verdict"].append("reaction %s purity %s — buffer the pH"
                                          % (r["name"], r["quality"]))
            if opts.get("eject"):
                ae = sk.tgui_act(id=wid, action="eject")
                out["ejected"] = bool(re.search(r'beaker: \{.* -> null', ae.text or ""))
            sk.tgui_send(id=wid, type="close")
            out["ok"] = True
            RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
