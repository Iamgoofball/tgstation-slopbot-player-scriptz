# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Recharge every SMES on the station via the admin Secrets panel (action quickpower).

Run: run_script {script: ".../admin_scriptz/quickpower.py"}
Announces a "Power Systems Nominal / All SMESs recharged" CC update to everyone
on the station (verified in test round). Admin-only; fine on a dev server, use
judgement elsewhere. Guard: only run when power is actually low — it is noisy.
'force': true skips the noisy-button warning.
"""
import re
opts = args or {}
if not opts.get("force"):
    RESULT = {"ok": False, "aborted": "noisy CC announcement; pass force:true when power is really low"}
else:
    # find an already-open Secrets panel, else open it
    wins = sk.tgui_windows().text or ""
    m = re.search(r"tgui-window-\d+:\n(?:\s{4}[^\n]*\n)*?\s{4}interface: Secrets", wins)
    if not m:
        sk.command(line="Secrets")
        time.sleep(0.8)
        wins = sk.tgui_windows().text or ""
        m = re.search(r"tgui-window-\d+:\n(?:\s{4}[^\n]*\n)*?\s{4}interface: Secrets", wins)
    if not m:
        raise SystemExit("Secrets panel did not open")
    wid = re.search(r"(tgui-window-\d+)", m.group(0)).group(1)
    a = sk.tgui_act(id=wid, action="quickpower")
    t = (a.text or "")
    time.sleep(0.6)
    RESULT = {"ok": "recharged" in t.lower(), "announced": "Power Systems Nominal" in t,
              "note": "all SMES recharged via Secrets quickpower"}

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
