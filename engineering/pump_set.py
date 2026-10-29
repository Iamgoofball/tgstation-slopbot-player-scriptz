"""Toggle/set one gas pump, valve, bypass or filter by NAME (must be in view).
Ctrl-click = on/off, alt-click = pressure to 4500 kPa (source-verified fork truth).

Run: run_script {script: ".../engineering/pump_set.py",
                 args: {"name": "Gas to Chamber", "on": true, "max": true}}
name is matched as exact obj name (prefix match ok). Returns {found, on_ok, max_ok}.
Verify the answer's data_changes lines; entries may be omitted when 0.
"""
import re
opts = args or {}
name = opts.get("name") or ""
if not name:
    raise ValueError("args: {'name': 'Gas to Chamber', 'on': true, 'max': true}")
want_on = opts.get("on", True)
want_max = opts.get("max", False)
out = {"name": name}

s = sk.search(query=name, in_view=True).text or ""
hit = None
for l in s.split("\n"):
    m = re.search(r'- obj (\d+) "([^"]*)"', l)
    if m and (m.group(2) == name or m.group(2).startswith(name)):
        hit = (int(m.group(1)), m.group(2))
        break
if not hit:
    raise SystemExit("'%s' not in view (walk closer first)" % name)
oid, found_name = hit
out["id"], out["found"] = oid, found_name

res = {"on_ok": False, "max_ok": False}
if want_on is not None:
    c = sk.click(object_id=oid, ctrl=True, expect_name=found_name)
    time.sleep(0.8)
    t = c.text or ""
    res["on_ok"] = bool(re.search(r"turned (on|off)|toggled", t, re.I))
    res["on_text"] = t[t.find("data_changes"):t.find("data_changes") + 150] if "data_changes" in t else ""
if want_max:
    c = sk.click(object_id=oid, alt=True, expect_name=found_name)
    time.sleep(0.8)
    t = c.text or ""
    res["max_ok"] = bool(re.search(r"4500|pressure output", t, re.I)) or "4500" in t
out.update(res)
out["ok"] = (res["on_ok"] or not want_on is not None) and (res["max_ok"] or not want_max)
out
