# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""The atmos tech's shift check, ONE envelope: all three Gas Storage consoles.

Run: run_script {script: ".../job_scriptz/atmospheric-technician/atmos_shift_check.py",
                 args: {"monitoring"?: id, "station_alert"?: id, "atmos_alert"?: id, "x"?, "y"?}}
Optional ids override the auto-survey (search in view: "station atmospherics
monitoring", "station alert console", "atmospheric alert console"). Stand in
Atmospherics Gas Storage. Read-ONLY: distro/waste gasmix (pressure, temp, %O2),
StationAlertConsole alarms[] (Atmosphere/Fire/Power), AtmosAlertConsole
priority[]/minor[] zones. Verdict: distro_ok (101±10 kPa, 19-23% O2),
waste_empty (<5 kPa), alarms counted.
Gotcha: close ALL tgui windows first — a stale console window swallows the
next click and shows its own (view-only) data.
"""
import re

opts = args or {}
out = {"consoles": {}, "distro": {}, "waste": {}, "station_alarms": {},
       "atmos_alerts": {}, "verdict": []}

def close_all():
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        sk.tgui_send(id=m.group(1), type="close")
        time.sleep(0.1)

def read_window(wid, chars=8000):
    return sk.tgui_window(id=wid, max_chars=chars).text or ""

def iface_of(wid):
    d = read_window(wid, 400)
    m = re.search(r"interface: (\S+)", d)
    return m and m.group(1)

def goto_then_click(oid, x=None, y=None):
    g = bot.goto(object_id=oid) if x is None else bot.goto(x=x, y=y)
    if g.failed and "already there" not in (g.text or ""):
        return None, "walk failed: " + (g.text or "")[-80:]
    close_all()
    sk.click(object_id=oid)
    time.sleep(1.6)
    w = sk.tgui_windows().text or ""
    for m in re.finditer(r"(tgui-window-\d+):", w):
        b = sk.tgui_window(id=m.group(1), max_chars=300).text or ""
        if "closed: true" in b:
            continue
        i = re.search(r"interface: (\S+)", b)
        if i:
            return m.group(1), None
    return None, "no window opened"

# 1) find consoles
want = {"station atmospherics monitoring": opts.get("monitoring"),
        "station alert console": opts.get("station_alert"),
        "atmospheric alert console": opts.get("atmos_alert")}
found = {k: int(v) for k, v in want.items() if v}
if len(found) < 3:
    s = sk.search(query="alert|monitoring", in_view=True, page_size=60)
    for m in re.finditer(r'- obj (\d+) "([^"]+)" at (\d+),(\d+)', s.text or ""):
        oid, name = int(m.group(1)), m.group(2).lower()
        for key in want:
            if key in found or want[key]:
                continue
            if name == key:
                found[key] = oid
                break
out["found"] = found

# 2) station atmospherics monitoring: distro + waste gasmix
mid = found.get("station atmospherics monitoring")
if mid:
    wid, err = goto_then_click(mid)
    if wid:
        out["consoles"]["monitoring"] = iface_of(wid)
        d = read_window(wid, 12000)
        for ch in ("distro", "waste"):
            start = d.find('"id": "%s"' % ch)
            nxt = d.find('"id":', start + 10)
            seg = d[start:nxt if nxt > -1 else start + 4000]
            row = {}
            # temperature comes BEFORE pressure in the gasmix JSON
            for key, pat in (("temperature_k", r'"temperature": ([\d.]+)'),
                             ("pressure_kpa", r'"pressure": ([\d.]+)'),
                             ("total_moles", r'"total_moles": ([\d.]+)')):
                mm = re.search(pat, seg)
                if mm:
                    row[key] = float(mm.group(1))
            gases = re.findall(r'\[\s*\n\s*"(\w+)",\s*\n\s*"[^"]*",\s*\n\s*([\d.]+)', seg)
            tot = row.get("total_moles") or 1
            row["gases_pct"] = {g: round(100.0 * float(v) / tot, 1)
                                for g, v in gases[:6]}
            out[ch] = row
        sk.tgui_send(id=wid, type="close")
    else:
        out["verdict"].append("monitoring console: " + (err or "?"))
else:
    out["verdict"].append("monitoring console not found in view")

# 3) station alert console: Atmosphere/Fire/Power alarms
sid = found.get("station alert console")
if sid:
    wid, err = goto_then_click(sid)
    if wid:
        out["consoles"]["station_alert"] = iface_of(wid)
        d = read_window(wid, 9000)
        for cat in ("Atmosphere", "Fire", "Power"):
            mb = re.search(r'"name": "%s",\s*"alerts": \[([\s\S]{0,900}?)\]' % cat, d)
            zones = re.findall(r'"name": "([^"]+)"', mb.group(1)) if mb else []
            out["station_alarms"][cat] = zones
        sk.tgui_send(id=wid, type="close")
    else:
        out["verdict"].append("station alert console: " + (err or "?"))
else:
    out["verdict"].append("station alert console not found in view")

# 4) atmospheric alert console: priority/minor zones
aid = found.get("atmospheric alert console")
if aid:
    wid, err = goto_then_click(aid)
    if wid:
        out["consoles"]["atmos_alert"] = iface_of(wid)
        d = read_window(wid, 6000)
        pr = re.search(r'"priority": \[([^\]]*)\]', d)
        mi = re.search(r'"minor": \[([^\]]*)\]', d)
        out["atmos_alerts"]["priority"] = re.findall(r'"([^"]+)"', pr.group(1)) if pr else []
        out["atmos_alerts"]["minor"] = re.findall(r'"([^"]+)"', mi.group(1)) if mi else []
        sk.tgui_send(id=wid, type="close")
    else:
        out["verdict"].append("atmos alert console: " + (err or "?"))
else:
    out["verdict"].append("atmos alert console not found in view")

# 5) verdict
dp = out["distro"].get("pressure_kpa")
o2 = (out["distro"].get("gases_pct") or {}).get("o2")
if dp is not None:
    okp = 91 <= dp <= 111
    oko = o2 is not None and 19 <= o2 <= 23
    out["verdict"].append("distro %s kPa %s%% O2 — %s" %
                          (dp, o2, "OK" if (okp and oko) else "ABNORMAL"))
else:
    out["verdict"].append("distro unreadable")
wp = out["waste"].get("pressure_kpa")
if wp is not None:
    out["verdict"].append("waste %s kPa — %s" %
                          (wp, "OK (near empty)" if wp < 5 else "backed up?"))
pri = out["atmos_alerts"].get("priority") or []
if pri:
    out["verdict"].append("PRIORITY AIR ALERTS: %s — fix first" % ", ".join(pri))
for cat, zones in (out["station_alarms"] or {}).items():
    if zones:
        out["verdict"].append("%s alarms: %s" % (cat, ", ".join(zones)))
out["ok"] = bool(out["distro"] or out["station_alarms"] or out["atmos_alerts"])
RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
