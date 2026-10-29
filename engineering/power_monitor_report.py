# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Read the engineering console's AmpCheck: supply vs demand + the per-area APC
table (149 entries: name, charge %, load, channel states). Read-ONLY.

Run: run_script {script: ".../engineering/power_monitor_report.py",
                 args: {"computer": <NtOS console obj id>, "x"?, "y"?, "limit"?: 12}}
`computer` = the Power Monitoring room's engineering console (survey_machines
finds it; ids change every round). MUST stand adjacent (x,y optional stand tile).
Returns {supply, demand, stored, lowest: [{name, charge}...], n_areas, ok}.
Gotchas: close EVERY tgui window first (a stale Smes window at tgui-window-1
swallows the click); read the table via tgui_window path:"data.areas", the
state block only summarizes it ("list of 149").
"""
import re

opts = args or {}
cid = opts.get("computer") or opts.get("id")
sx, sy = opts.get("x"), opts.get("y")
limit = int(opts.get("limit", 12))
prog = opts.get("program") or "ampcheck"
if not cid:
    raise ValueError("args: {'computer': obj_id} — find it with survey_machines.py")
out = {"computer": cid}

# close every tgui window: a stale window reuses tgui-window-1 and misreads
wins = sk.tgui_windows().text or ""
closed = 0
for m in re.finditer(r"(tgui-window-\d+):", wins):
    sk.tgui_send(id=m.group(1), type="close")
    closed += 1
    time.sleep(0.1)
out["closed_windows"] = closed

if sx is not None and sy is not None:
    g = bot.goto(x=sx, y=sy)
    if g.failed:
        print("stand-tile walk failed: %s" % (g.text or "")[-100:])
    time.sleep(0.3)
sk.click(object_id=int(cid))
time.sleep(1.5)

wid = None
iface = None
for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
    b = sk.tgui_window(id=m.group(1), max_chars=600).text or ""
    i = re.search(r"interface: (\S+)", b)
    if i and i.group(1) in ("NtosMain", "NtosPowerMonitor"):
        wid, iface = m.group(1), i.group(1)
        break
out["window"], out["iface"] = wid, iface
if wid is None:
    out["ok"] = False
    out["note"] = "console did not open an NtOS window (adjacent? powered?)"
else:
    if iface == "NtosMain":
        sk.tgui_act(id=wid, action="PC_runprogram", params={"name": prog})
        time.sleep(1.5)
        b = sk.tgui_window(id=wid, max_chars=1500).text or ""
        iface = (re.search(r"interface: (\S+)", b) or [None, None]).group(1)
        out["iface"] = iface
    if iface != "NtosPowerMonitor":
        out["ok"] = False
        out["note"] = "program %r did not open NtosPowerMonitor (got %s)" % (prog, iface)
    else:
        d = sk.tgui_window(id=wid, max_chars=3000).text or ""
        for key in ("supply", "demand", "stored", "interval", "attached"):
            mm = re.search(r'"%s":\s*"?([^",\n]+)"?' % key, d)
            if mm:
                out[key] = mm.group(1)
        # the per-area APC table, read by PATH (the state block hides it)
        t = sk.tgui_window(id=wid, path="data.areas", max_chars=60000).text or ""
        rows = []
        for m in re.finditer(
                r'"name":\s*"([^"]+)",\s*\n?\s*"charge":\s*([\d.]+)', t):
            rows.append({"name": m.group(1), "charge": float(m.group(2))})
        out["n_areas"] = len(rows)
        rows.sort(key=lambda r: r["charge"])
        out["lowest"] = rows[:limit]
        out["high_eqp_off"] = [r["name"] for r in rows if r["charge"] is not None][:0]
        out["ok"] = len(rows) > 0
        sk.tgui_send(id=wid, type="close")

RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
