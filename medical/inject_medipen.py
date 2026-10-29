# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Inject a medipen into self (default) or a target mob; verify via chat.

Run: run_script {script: "E:/byond_agent_test/tgstation-slopbot-player-scriptz/medical/inject_medipen.py",
                 args: {"pen": 123, "mob": 2892}}   # pen/mob optional (auto-find / self)
Epipen stops heart-rot (proved live: heart "failing" -> stopped). Medipens are
single-use; spent ones rename to "empty medipen".
"""
import re
opts = args or {}
pen = opts.get("pen")
mob = opts.get("mob")

pid = pen
if pid is None:
    inv = sk.inventory().text or ""
    for l in inv.split("\n"):
        ll = l.lower()
        if "medipen" in ll and "empty" not in ll:
            m = re.search(r"obj (\d+)", l)
            if m:
                pid = int(m.group(1)); break
if pid is None:
    raise SystemExit("no usable medipen in hands (pass args.pen with an id)")

inv = sk.inventory().text or ""
if "handactive" not in [l for l in inv.split("\n") if str(pid) in l and "handactive" in l]:
    if any(str(pid) in l for l in inv.split("\n")):
        sk.key(key="X"); time.sleep(0.3)  # make the pen's hand active

target = mob
if target is None:
    m = re.search(r"mob (\d+)", sk.status().get("you") or "")
    target = int(m.group(1)) if m else None
if target is None:
    raise SystemExit("cannot resolve self mob id from status")

c = sk.click(object_id=target, expect_name=None)
t = c.text or ""
time.sleep(0.8)
RESULT = ({"ok": bool(re.search(r"inject|administer|stabs", t, re.I)),
 "pen": pid, "target": target, "chat": t[-140:]})

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
