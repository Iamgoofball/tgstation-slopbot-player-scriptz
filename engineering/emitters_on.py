# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Turn ON emitters one at a time, from beside/behind each (never from in
front â€” the beam does 30 burn per hit), with a SAFETY WATCHDOG between each:
reads chat + status, and ABORTS immediately if the supermatter starts
delaminating, anything explodes/floods, or the mob is hurt. THIS script
started our engine delam once â€” it now verifies after each emitter and stops
at the first sign of trouble.

Run: run_script {script: ".../engineering/emitters_on.py",
                 args: {"ids": [111, 222, 333]}}
Optional: {"off": true} turns emitters OFF instead (delam response: kill the
beams FIRST, then vent â€” waste scales with energy, so emitters off is always
step 1). {"verify": {"computer": <NtOS console id>}} adds a CIMS DELTA CHECK after the
toggles: reads the CIMS twice via the NtOS console {"computer": obj_id} and
asserts energy moved in the expected direction (ON -> rising, OFF -> falling). NEVER trust clicks
or icons alone: emitter icons look identical on/off, an interrupted click may
never land (unknown state), and a blind re-click TOGGLES BACK (this script
was present at both of our delam-track excursions for exactly these reasons).
If emitters won't fire when ON (no power): check cable + SMES,
maximize SMES, run a P.A.C.M.A.N. for kickstart power, or toss a 1-credit
holochip (alt-click ID) / *kiss the crystal through the glass â€” anything
hitting the crystal adds trickle energy. Diode disks (screwdriver the emitter
maint panel open, swap with crowbar) change each hit: Psychosyphoning
(psy+25%, âˆ’25 MeV) and Electrodisruptive (+0.25% integrity, âˆ’60 MeV) are the
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
    ch = re.sub(r"<[^>]+>", " ", _pull_chat())
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

# CIMS delta verification (ground truth > clicks > icons)
vf = opts.get("verify") or {}
if vf.get("computer"):
    import time as _t
    def _cims():
        d = (sk.tgui_window(id="tgui-window-1").text or "")
        if "NtosSupermatter" not in d:
            if vf.get("x") is not None:
                bot.goto(x=vf["x"], y=vf["y"]); _t.sleep(0.4)
            sk.click(object_id=vf["computer"], expect_name=None); _t.sleep(2.2)
            d = (sk.tgui_window(id="tgui-window-1").text or "")
            if "NtosMain" in d:
                sk.tgui_act(id="tgui-window-1", action="PC_runprogram",
                            params={"name": "ntcims"}); _t.sleep(2.0)
                d = (sk.tgui_window(id="tgui-window-1").text or "")
        i = d.find("sm_data")
        ch2 = d[i:i + 5000] if i > -1 else ""
        m = re.search(r'"internal_energy":\s*([0-9.eE+]+)', ch2)
        return float(m.group(1)) if m else None
    e0 = _cims()
    _t.sleep(float(opts.get("gap_s", 12)))
    e1 = _cims()
    out["cims"] = {"energy_a": e0, "energy_b": e1,
                   "delta": (e1 - e0) if (e0 is not None and e1 is not None) else None}
    if out["cims"]["delta"] is not None:
        want_up = not turn_off
        out["cims"]["ok"] = (out["cims"]["delta"] > 1) if want_up else (out["cims"]["delta"] < -1)
    else:
        out["cims"]["ok"] = None   # unreadable -> agent must check manually
    out["ok"] = out["ok"] and bool(out["cims"]["ok"])
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
