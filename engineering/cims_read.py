# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Read the Supermatter via NT CIMS (PDA program, tgui — no chat parsing).
Opens the PDA (NtOS), runs the "ntcims" program, refreshes, parses sm_data[0].

Run: run_script {script: ".../engineering/cims_read.py",
                 args: {"pda": <obj id>}}     # PDA object id (ids change every round)
Returns {integrity, energy_gev, temp, temp_limit, moles, n2_pct, o2_pct,
plasma_pct, zap_mw, factors, ok}. Healthy stable N2 engine: integrity 100,
energy 1.3-1.6 GeV, temp 70-85 K, 10-20 mol, >=95% N2.
Note: the PDA must be reachable (held or pocketed); the script puts it in the
active hand and presses Z, then restores nothing (leave it in hand).
"""
import re
opts = args or {}
pda = opts.get("pda")
if not pda:
    inv0 = (sk.inventory().text or "")
    m = re.search(r"obj (\d+) \"[^\"]*pda", inv0, re.I)
    if not m:
        raise ValueError("args: {'pda': obj_id} — ids change every round; "
                         "no PDA found in inventory")
    pda = int(m.group(1))
out = {}
inv = (sk.inventory().text or "")
pl = [l for l in inv.split("\n") if "pda" in l.lower()]
if not pl:
    # PDA not on the mob: open the backpack and click it out
    bpk = opts.get("backpack")
    if not bpk:
        m = re.search(r"obj (\d+) \"[^\"]*backpack", inv, re.I)
        bpk = int(m.group(1)) if m else None
    if not bpk:
        raise SystemExit("PDA not worn and no backpack found — pass args {'pda': id, 'backpack': id}")
    sk.click(object_id=bpk, alt=True, expect_name="backpack")
    time.sleep(1.0)
    c = sk.click(object_id=pda, expect_name=None)
    time.sleep(0.6)
    inv = (sk.inventory().text or "")
    pl = [l for l in inv.split("\n") if "pda" in l.lower()]
if not pl:
    raise SystemExit("PDA not found (worn/hand/backpack)")
if pl and "handactive" not in pl[0]:
    sk.key(key="X"); time.sleep(0.4)
if "hand" not in pl[0]:
    sk.key(key="X"); time.sleep(0.4)   # get it into the active hand if worn
sk.key(key="Z"); time.sleep(1.5)
wins = (sk.tgui_windows().text or "")
pw = None
cims = None
def scan(wins):
    pw = cims = None
    for m in re.finditer(r"tgui-window-\d+:", wins):
        wid = m.group(0).rstrip(":")
        d = sk.tgui_window(id=wid).text or ""
        if "NtosMain" in d:
            pw = wid
        if "NtosSupermatter" in d:
            cims = wid
    return pw, cims
for attempt in range(2):
    pw, cims = scan(wins)
    if pw or cims:
        break
    sk.key(key="Z"); time.sleep(1.5)
    wins = (sk.tgui_windows().text or "")
if not cims and not pw:
    raise SystemExit("PDA window not open")
# find CIMS window (may already be running)
if not cims:
    sk.tgui_act(id=pw, action="PC_runprogram", params={"name": "ntcims"})
    time.sleep(1.5)
    wins = (sk.tgui_windows().text or "")
    for m in re.finditer(r"tgui-window-(\d+):", wins):
        d = sk.tgui_window(id=m.group(1)).text or ""
        if "NtosSupermatter" in d:
            cims = m.group(1); break
if not cims:
    raise SystemExit("NT CIMS did not open")
sk.tgui_act(id=cims, action="PRG_refresh")
time.sleep(1.2)
d = (sk.tgui_window(id=cims).text or "")
m = re.search(r"state: \|\n([\s\S]*)", d)
raw = m.group(1) if m else d
out["raw_len"] = len(raw)
# pull sm_data via path read (cleaner than regex over the JSON blob)
sd = (sk.tgui_window(id=cims, path="data.sm_data").text or "")
blk = sd
def fnum(pat, txt=blk):
    mm = re.search(pat, txt)
    return float(mm.group(1)) if mm else None
out["integrity"] = fnum(r'"integrity": ([\d.]+)')
en = fnum(r'"internal_energy": ([\d.eE+-]+)')
unit = re.search(r'"internal_energy_unit": "([^"]+)"', blk)
mult = {" eV": 1e-9, " kJ": 1e-6, " MeV": 1e-3, " GeV": 1.0}.get(unit.group(1) if unit else " eV", 1e-9)
out["energy_gev"] = en * mult if en is not None else None
out["temp"] = fnum(r'"gas_temperature": ([\d.]+)')
out["temp_limit"] = fnum(r'"temp_limit": ([\d.]+)')
out["moles"] = fnum(r'"gas_total_moles": ([\d.]+)')
n2 = fnum(r'"\/datum\/gas\/nitrogen": ([\d.]+)')
o2 = fnum(r'"\/datum\/gas\/oxygen": ([\d.]+)')
pl_ = fnum(r'"\/datum\/gas\/plasma": ([\d.]+)')
out["n2_pct"] = n2 * 100 if n2 is not None else None
out["o2_pct"] = o2 * 100 if o2 is not None else None
out["plasma_pct"] = pl_ * 100 if pl_ is not None else None
zt = fnum(r'"zap_transmission": ([\d.eE+-]+)')
zu = re.search(r'"zap_transmission_unit": "([^"]+)"', blk)
out["zap_mw"] = zt * {" W": 1e-6, " kW": 1e-3, " MW": 1.0}.get(zu.group(1) if zu else " W", 1e-6) if zt is not None else None
out["factors"] = sorted(set(re.findall(r'"name": "([^"]+)"', blk)))[:8]
out["ok"] = out["integrity"] is not None
# Guide thresholds (supermatter_setup_guide.txt): charge delam >5000 MeV
# internal energy, singularity delam >1800 moles, plasma+O2 combust at
# 373.15 K (the practical limit, below the 626 K damage limit).
out["flags"] = []
if out["energy_gev"] is not None and out["energy_gev"] >= 5.0:
    out["flags"].append("CHARGE_DELAM_RISK energy>=5 GeV")
if out["moles"] is not None and out["moles"] >= 1800:
    out["flags"].append("SINGULARITY_DELAM_RISK moles>=1800")
if out["temp"] is not None and out["temp"] >= 373.15:
    out["flags"].append("COMBUSTION_TEMP plasma/O2 burns at 373 K")
if out["integrity"] is not None and out["integrity"] <= 40:
    out["flags"].append("ANOMALY_RANGE integrity<=40%: flux+grav anomalies")
if out["integrity"] is not None and out["integrity"] <= 0:
    out["flags"].append("DELAM_COUNTDOWN 30s window; RUN on 15s broadcast")
# tidy: put the PDA back into the backpack so hands stay free
inv = (sk.inventory().text or "")
pl = [l for l in inv.split("\n") if "pda" in l.lower() and "hand" in l]
if pl:
    if "handactive" not in pl[0]:
        sk.key(key="X"); time.sleep(0.3)
    bpk = (args or {}).get("backpack")
    if not bpk:
        m = re.search(r"obj (\d+) \"[^\"]*backpack", inv, re.I)
        bpk = int(m.group(1)) if m else None
    if bpk:
        sk.click(object_id=bpk, expect_name="backpack")
    time.sleep(0.6)
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
