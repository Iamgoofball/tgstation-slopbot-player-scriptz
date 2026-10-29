# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Read the CIMS TWICE (via the NtOS console, cims_console logic) and return
the delta + trend verdict. A single CIMS read cannot tell healing from
destabilizing; deltas are the ground truth (icon states are useless: emitter
'on' and 'off' look identical, and crystal warnings lag).

Run: run_script {script: ".../engineering/cims_watch.py",
                 args: {"computer": <NtOS console obj id>}}
Optional: {"gap_s": 20 (default), "x","y": stand-adjacent tile}.
Required: computer — ids change every round; find the NtOS console with
survey_machines.py first.
Returns {a, b, delta, trend, ok} — trend is one of:
  "healing"        integrity rising
  "stable"         integrity flat, temp under limit
  "destabilizing"  integrity falling OR temp > temp_limit -> ACT: cut beams,
                   then siphon (scrubbing val:0), see engineering/index.md
"""
import re, time
opts = args or {}
cid = opts.get("computer")
if not cid:
    raise ValueError("args: {'computer': obj_id} — ids change every round")
sx, sy = opts.get("x"), opts.get("y")
gap = float(opts.get("gap_s", 20))


def read_cims():
    d = (sk.tgui_window(id="tgui-window-1").text or "")
    iface = (re.search(r"interface: (\S+)", d) or [None]).group(1) \
        if re.search(r"interface: (\S+)", d) else None
    if iface != "NtosSupermatter":
        if sx is not None:
            bot.goto(x=sx, y=sy); time.sleep(0.4)
        sk.click(object_id=cid, expect_name=None); time.sleep(2.2)
        d = (sk.tgui_window(id="tgui-window-1").text or "")
        iface = (re.search(r"interface: (\S+)", d) or [None]).group(1) \
            if re.search(r"interface: (\S+)", d) else None
        if iface == "NtosMain":
            sk.tgui_act(id="tgui-window-1", action="PC_runprogram",
                        params={"name": "ntcims"}); time.sleep(2.0)
            d = (sk.tgui_window(id="tgui-window-1").text or "")
    i = d.find("sm_data")
    chunk = d[i:i + 5000] if i > -1 else ""
    def num(pat):
        m = re.search(pat, chunk)
        return float(m.group(1)) if m else None
    return {"integrity": num(r'"integrity":\s*([0-9.]+)'),
            "energy": num(r'"internal_energy":\s*([0-9.eE+]+)'),
            "temp": num(r'"gas_temperature":\s*([0-9.]+)'),
            "temp_limit": num(r'"temp_limit":\s*([0-9.]+)'),
            "moles": num(r'"gas_total_moles":\s*([0-9.]+)')}


a = read_cims()
time.sleep(gap)
b = read_cims()
out = {"a": a, "b": b}
if a["integrity"] is not None and b["integrity"] is not None:
    out["delta"] = {k: (b[k] - a[k]) if (a.get(k) is not None and b.get(k) is not None)
                    else None for k in a}
    di = out["delta"]["integrity"]
    temp_bad = b["temp"] is not None and b["temp_limit"] and b["temp"] > b["temp_limit"]
    if di is not None and di > 0.5:
        out["trend"] = "healing"
    elif temp_bad or (di is not None and di < -0.5):
        out["trend"] = "destabilizing"
    else:
        out["trend"] = "stable"
else:
    out["trend"] = "unreadable"

RESULT = out

END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
