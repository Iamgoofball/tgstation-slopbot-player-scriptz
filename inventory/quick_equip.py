# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Quick-equip the held item with the E hotkey, then verify where it went.
IMPORTANT TRUTH: quick-equip does NOT swap with an occupied slot — if the
target slot is taken, the game STORES the item into an available inventory
object (backpack, belt, pockets) instead. The item can silently vanish into
your bag. This script finds out where it went.

Run: run_script {script: ".../inventory/quick_equip.py",
                 args: {"expect": "radiation hood"}}
Optional args: {"key": "E"} (default), {"slot_regex": "head"} to verify a
specific slot.
Returns {ok, where: "slot <name>" | "stored in <item>" | "hand" | "unknown",
         line} — check `where` before doing anything else with the item.
"""
import re
opts = args or {}
expect = opts.get("expect")
eqkey = opts.get("key", "E")
slot_re = opts.get("slot_regex")

def state():
    return sk.inventory().text or ""

before = state()
sk.key(key=eqkey)
import time
time.sleep(0.9)
after = state()

out = {}
# did the item move to a worn slot?
for l in after.split("\n"):
    if expect and expect.lower() in l.lower() and "slot \"" in l and "hand" not in l:
        m = re.search(r"in slot \"([^\"]+)\"", l)
        if m and (not slot_re or re.search(slot_re, m.group(1), re.I)):
            out["ok"] = True
            out["where"] = "slot " + m.group(1)
            out["line"] = l[:100]
            break
if "ok" not in out:
    # did it end up in a container?
    act = sk.screen().text or ""
    held = None
    for l in after.split("\n"):
        if expect and expect.lower() in l.lower() and "hand" in l:
            held = l
    if not held:
        out["where"] = "unknown (not in hands or worn slots) — check open containers"
        out["ok"] = False
    else:
        out["where"] = "hand (quick-equip did nothing useful)"
        out["ok"] = False
        out["line"] = held[:100]
    # NOTE: quick-equip with an occupied slot STORES the item into a container
    # (backpack first). Open the container (alt-click) to get it back.
out["slot_was"] = re.findall(r"in slot \"([^\"]+)\"", before)
out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": out, "end_check": END_CHECK}
