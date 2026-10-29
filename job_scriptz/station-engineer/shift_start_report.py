# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""The engineer's shift-start report: everything that matters about the power
plant in ONE envelope. Stand in/near the SMES room when you run it.

Run: run_script {script: ".../job_scriptz/station-engineer/shift_start_report.py",
                 args: {"smes_ids"?: [..], "computer"?: <NtOS console id>, "x"?, "y"?}}
All args optional: without them it surveys in view ("power storage|engineering
console") from the current tile. Reads: every SMES (charge %, output), AmpCheck
(supply/demand, 5 lowest-charge areas), NT CIMS via the console (integrity,
energy, temp). Verdict lines: engine_off / smes_low / cims_state / area_low /
console_missing. Composes engineering/smes_read + power_monitor_report +
cims_console patterns — run those individually for repairs.
"""
import re

opts = args or {}
out = {"smes": [], "power": {}, "cims": {}, "verdict": []}

def close_all():
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        sk.tgui_send(id=m.group(1), type="close")
        time.sleep(0.1)

def find_in_view():
    s = sk.search(query="power storage|engineering console", in_view=True,
                  page_size=30)
    t = s.text or ""
    smes, console = [], None
    for m in re.finditer(r'- obj (\d+) "([^"]+)" at (\d+),(\d+)', t):
        oid, name, x, y = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
        if "power storage" in name.lower():
            smes.append({"id": oid, "x": x, "y": y})
        elif "engineering console" in name.lower():
            console = {"id": oid, "x": x, "y": y}
    return smes, console

# 1) find the machines
smes_list = [{"id": int(i)} for i in (opts.get("smes_ids") or [])]
console = ({"id": int(opts["computer"])}
           if opts.get("computer") else None)
if not smes_list or not console:
    f_smes, f_console = find_in_view()
    if not smes_list:
        smes_list = f_smes
    if not console:
        console = f_console
out["found"] = {"smes": len(smes_list), "console": console and console["id"]}

# 2) read every SMES
for s in smes_list:
    g = bot.goto(object_id=s["id"])
    if g.failed and "already there" not in (g.text or ""):
        out["smes"].append(dict(s, ok=False, note="walk failed"))
        continue
    close_all()
    sk.click(object_id=s["id"])
    time.sleep(1.0)
    d = sk.tgui_window(id="tgui-window-1", max_chars=6000).text or ""
    def num(txt, pat):
        m = re.search(pat, txt)
        try:
            return float(m.group(1)) if m else None
        except ValueError:
            return None
    chg = num(d, r'"charge":\s*([0-9.]+)')
    cap = num(d, r'"capacity":\s*([0-9.eE+]+)')
    use = num(d, r'"outputUsed":\s*([0-9.eE+]+)')
    outp = bool(re.search(r'"outputAttempt":\s*1', d))
    row = dict(s, ok=chg is not None,
               pct=(round(100.0 * chg / cap, 1) if (chg is not None and cap) else None),
               output_w=use, outputting=outp)
    out["smes"].append(row)
    close_all()

# 3) AmpCheck + CIMS via the NtOS console
if console:
    if console.get("x") is not None:
        g = bot.goto(x=console["x"], y=console["y"])
    else:
        g = bot.goto(object_id=console["id"])
    if g.failed and "already there" not in (g.text or ""):
        out["verdict"].append("console unreachable: " + (g.text or "")[-60:])
    else:
        close_all()
        sk.click(object_id=console["id"])
        time.sleep(1.8)
        d = sk.tgui_window(id="tgui-window-1", max_chars=9000).text or ""
        iface = (re.search(r"interface: (\S+)", d) or [None, None]).group(1)
        # normalize to the desktop: any running program's window lacks the
        # programs list — PC_exit walks back to NtosMain
        for _ in range(3):
            if iface in ("NtosMain", "NtosPowerMonitor"):
                break
            sk.tgui_act(id="tgui-window-1", action="PC_exit")
            time.sleep(0.7)
            d = sk.tgui_window(id="tgui-window-1", max_chars=2500).text or ""
            iface = (re.search(r"interface: (\S+)", d) or [None, None]).group(1)
        out["iface"] = iface
        if iface == "NtosMain":
            sk.tgui_act(id="tgui-window-1", action="PC_runprogram",
                        params={"name": "ampcheck"})
            time.sleep(1.5)
            d = sk.tgui_window(id="tgui-window-1", max_chars=3000).text or ""
            iface = (re.search(r"interface: (\S+)", d) or [None, None]).group(1)
        if iface == "NtosPowerMonitor":
            for key in ("supply", "demand"):
                m = re.search(r'"%s":\s*"([^"]+)"' % key, d)
                if m:
                    out["power"][key] = m.group(1)
            t = sk.tgui_window(id="tgui-window-1", path="data.areas",
                               max_chars=60000).text or ""
            rows = [{"name": m.group(1), "charge": float(m.group(2))}
                    for m in re.finditer(
                        r'"name":\s*"([^"]+)",\s*\n?\s*"charge":\s*([\d.]+)', t)]
            rows.sort(key=lambda r: r["charge"])
            out["power"]["n_areas"] = len(rows)
            out["power"]["lowest"] = rows[:5]
            # switch programs: kill ampcheck, run ntcims
            sk.tgui_act(id="tgui-window-1", action="PC_killprogram",
                        params={"name": "ampcheck"})
            time.sleep(0.5)
            sk.tgui_act(id="tgui-window-1", action="PC_runprogram",
                        params={"name": "ntcims"})
            time.sleep(1.5)
            d2 = sk.tgui_window(id="tgui-window-1", max_chars=9000).text or ""
            i2 = d2.find("sm_data")
            chunk = d2[i2:i2 + 5000] if i2 > -1 else ""
            for key, pat in (("integrity", r'"integrity":\s*([0-9.]+)'),
                             ("energy", r'"internal_energy":\s*([0-9.eE+]+)'),
                             ("temp", r'"gas_temperature":\s*([0-9.]+)')):
                out["cims"][key] = num(chunk, pat)
            out["cims"]["ok"] = out["cims"]["integrity"] is not None
            sk.tgui_send(id="tgui-window-1", type="close")
        else:
            out["verdict"].append("console iface %s — no ampcheck/cims" % iface)

# 4) verdict
if not smes_list:
    out["verdict"].append("NO SMES in view — stand in the SMES room")
for s in out["smes"]:
    if s.get("pct") is not None and s["pct"] < 20:
        out["verdict"].append("SMES %s LOW (%s%%) — engine must run" %
                              (s["id"], s["pct"]))
sup = out["power"].get("supply")
if sup is not None:
    out["verdict"].append("grid feed %s" % sup)
c = out["cims"]
if c.get("energy") is not None:
    if c["energy"] > 0.1:
        out["verdict"].append("engine RUNNING (energy %s GeV)" % c["energy"])
    else:
        out["verdict"].append("engine COLD (energy 0) — start it: emitters + field")
if c.get("integrity") is not None:
    if c["integrity"] >= 99:
        out["verdict"].append("crystal healthy (%s%%)" % c["integrity"])
    else:
        out["verdict"].append("CRYSTAL DAMAGED (%s%%) — check CIMS/gases" % c["integrity"])
else:
    out["verdict"].append("CIMS unreadable (console? adjacency? hand empty?)")
low = [r for r in out["power"].get("lowest", []) if r["charge"] < 40]
if low:
    out["verdict"].append("areas draining: %s" %
                          ", ".join("%s %s%%" % (r["name"], int(r["charge"]))
                                    for r in low[:3]))
out["ok"] = bool(out["smes"]) or bool(out["power"])
RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
