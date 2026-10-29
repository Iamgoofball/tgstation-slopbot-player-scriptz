# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Take a SPECIFIC tool from a surgery tray (RMB opens the picker; LMB grabs a
random tool — avoid LMB unless you feel lucky).

Run: run_script {script: ".../machines/tray_take.py",
                 args: {"tray_id": 82051, "expect_name": "surgery tray", "tool": "circular saw"}}
Needs an empty hand (auto_drop=true drops the active item first).
"""
import re
opts = args or {}
tid, tname, tool = opts.get("tray_id"), opts.get("expect_name"), opts.get("tool")
if tid is None or not tool:
    raise ValueError("args: {'tray_id': id, 'expect_name': 'surgery tray', 'tool': 'circular saw'}")
inv = (sk.inventory().text or "")
if "handactive" in inv and opts.get("auto_drop"):
    sk.key(key="Q")
    time.sleep(0.3)
inv = (sk.inventory().text or "")
if "handactive" in inv:
    raise ValueError("active hand not empty; drop something first")
sk.click(object_id=tid, expect_name=tname, right=True)  # RMB = specific-tool UI
time.sleep(0.6)
lines = (sk.screen(page_size=60).text or "").split("\n")
target = None
for l in lines:
    m = re.match(r"- obj (\d+) \"([^\"]*)\"", l)
    if m and tool.lower() in m.group(2).lower():
        target = int(m.group(1))
        break
if target is None:
    {"ok": False, "detail": "tool not on tray UI", "seen": [l[2:70] for l in lines if l.startswith("- obj")][:10]}
else:
    sk.click(object_id=target, expect_name=None)
    time.sleep(0.4)
    inv = (sk.inventory().text or "")
    got = [l.strip()[:90] for l in inv.split("\n") if str(target) in l]
    {"ok": bool(got), "tool": tool, "id": target, "slot": (got[0] if got else None)}

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
