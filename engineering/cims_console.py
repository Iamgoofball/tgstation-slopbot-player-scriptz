# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Read the NT CIMS via the SMES-room NtOS computer — PDA-INDEPENDENT (the
PDA path in cims_read.py dies when the PDA battery dies; this console never
does). Walks to the computer (empty active hand REQUIRED), opens NtosMain,
runs the ntcims program, parses sm_data[0].

Run: run_script {script: ".../engineering/cims_console.py",
                 args: {"computer": <NtOS console obj id>}}
Required: {"computer": obj id of the NtOS engineering console (the one in the
SMES room — survey_machines.py finds it; ids change every round, never
hard-code). Optional: {"x","y"} stand-adjacent tile (buttons work only from
NEXT to the console: 2 tiles away it is VIEW-ONLY, 3-5 disabled).
Returns {integrity, energy, temp, temp_limit, moles, n2, o2, plasma, ok}.
Stable healthy N2 engine: integrity 100, temp <= ~85 K, 10-20 mol,
>=95% N2, o2 ~0. IMPORTANT: read TWICE (cims_watch.py) for trend —
single reads can't tell healing from destabilizing.
"""
import re
opts = args or {}
cid = opts.get("computer") or opts.get("id")
sx, sy = opts.get("x"), opts.get("y")
if not cid:
    raise ValueError("args: {'computer': obj_id} — ids change every round; "
                     "find the NtOS console with survey_machines.py first")
out = {"computer": cid}

# close stale windows first: a leftover Smes/APC window would be reused/misread
for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
    try:
        b = sk.tgui_window(id=m.group(1)).text or ""
        i = re.search(r"interface: (\S+)", b)
        if i and i.group(1) not in ("NtosMain", "NtosSupermatter"):
            sk.tgui_send(id=m.group(1), type="close")
            time.sleep(0.3)
    except Exception:
        pass

inv = (sk.inventory().text or "")
act = [l for l in inv.split("\n") if "active_hand" in l]
if act and "empty" not in act[0]:
    out["note"] = "active hand NOT empty — click may open nothing; trying anyway"

if sx is not None:
    bot.goto(x=sx, y=sy)
    time.sleep(0.4)
c = sk.click(object_id=cid, expect_name=None)
time.sleep(2.2)
d = (sk.tgui_window(id="tgui-window-1").text or "")
iface = (re.search(r"interface: (\S+)", d) or [None]).group(1) if re.search(r"interface: (\S+)", d) else None
out["iface"] = iface
if iface == "NtosMain":
    a = sk.tgui_act(id="tgui-window-1", action="PC_runprogram", params={"name": "ntcims"})
    time.sleep(2.0)
    d = (sk.tgui_window(id="tgui-window-1").text or "")
    iface = (re.search(r"interface: (\S+)", d) or [None]).group(1) if re.search(r"interface: (\S+)", d) else None
    out["iface"] = iface
if iface != "NtosSupermatter":
    raise SystemExit("CIMS did not open (iface=%s) — is the console the "
                     "NtOS one, and is the active hand empty?" % iface)
if "view-only" in d[:400]:
    out["view_only"] = True   # reads still work from 2 tiles; buttons don't

i = d.find("sm_data")
chunk = d[i:i + 5000] if i > -1 else ""
def num(pat):
    m = re.search(pat, chunk)
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return m.group(1)
out["integrity"] = num(r'"integrity":\s*([0-9.]+)')
out["energy"] = num(r'"internal_energy":\s*([0-9.eE+]+)')
out["temp"] = num(r'"gas_temperature":\s*([0-9.]+)')
out["temp_limit"] = num(r'"temp_limit":\s*([0-9.]+)')
out["moles"] = num(r'"gas_total_moles":\s*([0-9.]+)')
out["n2"] = num(r'"/datum/gas/nitrogen":\s*([0-9.eE+-]+)')
out["o2"] = num(r'"/datum/gas/oxygen":\s*([0-9.eE+-]+)')
out["plasma"] = num(r'"/datum/gas/plasma":\s*([0-9.eE+-]+)')
out["ok"] = out["integrity"] is not None

RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
