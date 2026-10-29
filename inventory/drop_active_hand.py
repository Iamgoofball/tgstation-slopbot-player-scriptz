# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Drop whatever the active hand holds (key Q) and verify it went.

Run: run_script {script: ".../inventory/drop_active_hand.py"}"""
def active():
    t = (sk.inventory().text or "")
    for l in t.split("\n"):
        if "handactive" in l:
            return l.strip()[:100]
    return None
before = active()
sk.key(key="Q")
time.sleep(0.4)
after = active()
RESULT = ({"ok": before is not None and after is None, "dropped": before, "now_active": after})

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
