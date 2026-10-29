"""Turn ON emitters one at a time, from beside/behind each (never from in
front — the beam does 30 burn per hit), with a SAFETY WATCHDOG between each:
reads chat + status, and ABORTS immediately if the supermatter starts
delaminating, anything explodes/floods, or the mob is hurt. THIS script
started our engine delam once — it now verifies after each emitter and stops
at the first sign of trouble.

Run: run_script {script: ".../engineering/emitters_on.py",
                 args: {"ids": [111, 222, 333]}}
Optional: {"off": true} turns emitters OFF instead (delam response: kill the
beams FIRST, then vent — waste scales with energy, so emitters off is always
step 1). If emitters won't fire when ON (no power): check cable + SMES,
maximize SMES, run a P.A.C.M.A.N. for kickstart power, or toss a 1-credit
holochip (alt-click ID) / *kiss the crystal through the glass — anything
hitting the crystal adds trickle energy. Diode disks (screwdriver the emitter
maint panel open, swap with crowbar) change each hit: Psychosyphoning
(psy+25%, −25 MeV) and Electrodisruptive (+0.25% integrity, −60 MeV) are the
safe picks.
Returns per-emitter {id, on/off result, chat_danger?}. The agent MUST read the
returned chat digest and re-check CIMS before walking anywhere near the chamber.
"""
import re
opts = args or {}
ids = opts.get("ids") or []
turn_off = opts.get("off")
if not ids:
    raise ValueError("args: {'ids': [emitter obj ids], 'off'?: bool}")

DANGER = (r"delaminat|integrity|countdown|blast|explod|detonat|flood|fire|"
          r"electroc|shock|causality|warning|emergency|toxin")
def watch(tag=""):
    ch = re.sub(r"<[^>]+>", " ", sk.read_chat(wait_s=1).text or "")
    hits = re.findall(r"[^\n]{0,70}(?:%s)[^\n]{0,70}" % DANGER, ch, re.I)
    st = (sk.status().text or "")
    dead = "ghost" in st[:120]
    if hits or dead:
        raise SystemExit("ABORT danger %s: %s | status: %s" % (tag, hits[-2:], st[:100]))

watch("start")
out = {"emitters": []}
for oid in ids:
    c = sk.click(object_id=oid, expect_name="emitter")
    time.sleep(1.0)
    t = (c.text or "")
    msg = re.search(r"You turn (on|off)[^\\n]{0,20}", t)
    e = sk.examine(object_id=oid).text or ""
    rec = {"id": oid,
           "click": msg.group(0) if msg else t[:60],
           "beam": "Emitting one beam" in e,
           "no_power": "glowing faintly" in e}
    out["emitters"].append(rec)
    watch("emitter %s" % oid)     # ABORT remaining emitters on any danger sign
out["ok"] = all(x.get("beam") or x.get("off") or turn_off for x in out["emitters"]) if out["emitters"] else False
out
