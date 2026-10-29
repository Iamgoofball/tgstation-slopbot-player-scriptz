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
{"ok": before is not None and after is None, "dropped": before, "now_active": after}
