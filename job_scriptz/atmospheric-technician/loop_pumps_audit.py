# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Audit (and optionally fix) the atmos loop's critical pumps/mixer, the
shift-start checklist as one state-checked envelope.

Run: run_script {script: ".../job_scriptz/atmospheric-technician/loop_pumps_audit.py",
                 args: {"fix"?: true, "distro_pressure"?: 101}}
Walks the Atmospherics Pumping Room + mixer area (spots built in), opens every
matching pump/mixer tgui (AtmosPump {on, pressure} / AtmosMixer {on,
node1/node2 concentration}), and verdicts against the spec:
  "Air to Distro" ON (101 or distro_pressure), "Waste to Filter" ON,
  "Distro to Waste" OFF, "Distro Staging to Distro" OFF, air mixer ON 79/21.
fix: true → state-checked corrections (power to goal, pressure set). Filters
and the X-to-Pure pumps are reported when seen but not auto-touched.
Pump window needs an empty active hand; the audit swaps hands itself.
"""
import re

opts = args or {}
fix = bool(opts.get("fix"))
distro_goal = float(opts.get("distro_pressure", 101))
out = {"pumps": {}, "verdict": [], "fixed": []}

# name -> (goal_on, goal_pressure or None); None = report-only
SPEC = {
    "air to distro": (1, distro_goal),
    "waste to filter": (1, None),
    "distro to waste": (0, None),
    "distro staging to distro": (0, None),
    "distro staging to filter": (None, None),
    "n2 to airmix": (None, None),
    "o2 to airmix": (None, None),
}

def close_all():
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        sk.tgui_send(id=m.group(1), type="close")
        time.sleep(0.1)

def empty_active_hand():
    for _ in range(2):
        inv = sk.inventory().text or ""
        act = [l for l in inv.split("\n") if "active_hand" in l]
        if act and ("empty" in act[0] or "obj" not in act[0]):
            return True
        sk.key(key="X")
        time.sleep(0.4)
    inv = sk.inventory().text or ""
    act = [l for l in inv.split("\n") if "active_hand" in l]
    if act and "obj" in act[0]:
        sk.key(key="Q")
        time.sleep(0.4)
        return True
    return False

# 1) survey the two rooms
SPOTS = [[171, 130], [169, 128], [168, 120], [166, 118], [167, 112]]
seen = {}
for (sx, sy) in SPOTS:
    g = bot.goto(x=sx, y=sy)
    if g.failed and "already there" not in (g.text or ""):
        continue
    time.sleep(0.3)
    s = sk.search(query="to distro|to filter|to waste|to airmix|air mixer|"
                        "to pure|to engine|mix outlet", in_view=True, page_size=60)
    for m in re.finditer(r'- obj (\d+) "([^"]+)" at (\d+),(\d+)', s.text or ""):
        oid, name = int(m.group(1)), m.group(2)
        if name not in seen:
            seen[name] = oid
out["seen"] = sorted(seen)

# 2) read every machine in the audit + mixer
empty_active_hand()
targets = {n: i for n, i in seen.items()
           if n.lower() in SPEC
           or "air mixer" in n.lower()
           or "to airmix" in n.lower()}

def click_and_read(oid, expect_name, tries=2):
    """Open the machine's tgui and return its state text ONLY if some window's
    title matches — a stale window (or an admin panel from quickpower) can
    otherwise pass its data off as this machine's, under ANY window id."""
    for _ in range(tries):
        close_all()
        time.sleep(0.4)
        sk.click(object_id=oid)
        time.sleep(1.5)
        w = sk.tgui_windows().text or ""
        for m in re.finditer(r"(tgui-window-\d+):", w):
            d = sk.tgui_window(id=m.group(1), max_chars=4000).text or ""
            if "closed: true" in d[:300]:
                continue
            tm = re.search(r"title: ([^\n]+)", d)
            if tm and tm.group(1).strip() == expect_name:
                return d, m.group(1)
    return None, None

for name, oid in targets.items():
    key = name.lower()
    g = bot.goto(object_id=oid)
    if g.failed and "already there" not in (g.text or ""):
        out["pumps"][name] = {"id": oid, "ok": False,
                              "note": "unreachable (sealed pipe-access door?)"}
        continue
    d, wid = click_and_read(oid, name)
    if d is None:
        out["pumps"][name] = {"id": oid, "ok": False,
                              "note": "window did not open / title mismatch"}
        continue
    iface = (re.search(r"interface: (\S+)", d) or [None, None]).group(1)
    row = {"id": oid, "iface": iface}
    if iface == "AtmosPump":
        on = re.search(r'"on": (\d)', d)
        pr = re.search(r'"pressure": ([\d.]+)', d)
        row["on"] = int(on.group(1)) if on else None
        row["pressure"] = float(pr.group(1)) if pr else None
        goal_on, goal_p = SPEC.get(key, (None, None))
        if goal_on is not None and row["on"] != goal_on:
            out["verdict"].append("%s is %s — should be %s" %
                                  (name, "OFF" if row["on"] == 0 else "ON",
                                   "ON" if goal_on == 1 else "OFF"))
            if fix:
                sk.tgui_act(id=wid, action="power")
                time.sleep(0.6)
                d2 = sk.tgui_window(id=wid, max_chars=2000).text or ""
                row["on"] = int(re.search(r'"on": (\d)', d2).group(1))
                out["fixed"].append({name: "power -> %d" % row["on"]})
        if goal_p is not None and row["pressure"] is not None and abs(row["pressure"] - goal_p) > 1:
            out["verdict"].append("%s at %s kPa (goal %s)" %
                                  (name, row["pressure"], goal_p))
            if fix:
                sk.tgui_act(id=wid, action="pressure",
                            params={"pressure": goal_p})
                time.sleep(0.6)
                d2 = sk.tgui_window(id=wid, max_chars=2000).text or ""
                row["pressure"] = float(re.search(r'"pressure": ([\d.]+)', d2).group(1))
                out["fixed"].append({name: "pressure -> %s" % row["pressure"]})
    elif iface == "AtmosMixer":
        on = re.search(r'"on": (\d)', d)
        n1 = re.search(r'"node1_concentration": ([\d.]+)', d)
        n2 = re.search(r'"node2_concentration": ([\d.]+)', d)
        pr = re.search(r'"set_pressure": ([\d.]+)', d)
        row.update({"on": int(on.group(1)) if on else None,
                    "node1": float(n1.group(1)) if n1 else None,
                    "node2": float(n2.group(1)) if n2 else None,
                    "set_pressure": float(pr.group(1)) if pr else None})
        if row["on"] != 1:
            out["verdict"].append("air mixer OFF — distro starves")
        elif row["node1"] is not None and abs(row["node1"] - 79) > 2:
            out["verdict"].append("air mixer mix off-spec: N2 %s%% (goal 79)" % row["node1"])
    else:
        row["note"] = "unhandled iface " + str(iface)
    sk.tgui_send(id=wid, type="close")
    out["pumps"][name] = row

# 3) summary verdict
if not any(v.get("on") == 1 for v in out["pumps"].values() if "on" in v):
    out["verdict"].append("no pumps confirmed ON — survey may have missed them")
out["ok"] = bool(out["pumps"])
RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
