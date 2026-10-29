# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""EMERGENCY delamination response, one envelope. Order matters (learned the
hard way â€” Lennox Fields RIP):
1. Kill the beams (emitters off) â€” stops new energy instantly.
2. Air alarm -> panic siphon (vents OFF, scrubbers siphon hard) + widenet.
3. Open the N2 canister valves (cold nitrogen flood cools the chamber).
4. Verify CIMS trend; return {integrity_trend} so the agent can decide
   flee vs fight. ABORTS the moment chat shows the countdown (then RUN).

Run: run_script {script: ".../engineering/delam_response.py",
                 args: {"emitters": [<id>, <id>, <id>],
                        "alarm": <chamber alarm id>, "canisters": [<id>, <id>]}}
All ids are args — never hard-coded (ids change every round). Guide facts
(supermatter_setup_guide.txt):
at 0% integrity the crystal has a **30 s window in which it can still heal**
(it keeps taking damage; it must climb back above 0), but the common-channel
broadcast says **15 seconds** â€” treat 15 s as the realistic window. After this
script the agent MUST read the result and, if integrity is still falling and
no countdown yet, either repeat it or physically RUN (sk.move away 10+ tiles)
â€” the blast is ~37 tiles with O2 in the chamber. Delam type at 0% depends on
state: >5000 MeV â†’ tesla ball; >1800 moles â†’ singularity; 40/40 hyper+anti-nob
â‰¥270 mol â†’ resonance cascade (cims_read.py flags all three).
"""
import re
opts = args or {}
emitters = opts.get("emitters") or []
alarm = opts.get("alarm")
canisters = opts.get("canisters") or []
if not (emitters or alarm or canisters):
    raise ValueError("args: {'emitters': [...], 'alarm': id, 'canisters': [...]}")
out = {"done": []}
DANGER = r"delaminat|countdown|causality|blast|explod"
def watch(tag):
    ch = re.sub(r"<[^>]+>", " ", _pull_chat())
    hits = re.findall(r"[^\n]{0,70}(?:%s)[^\n]{0,70}" % DANGER, ch, re.I)
    if hits:
        out["COUNTDOWN_OR_BLAST"] = hits[-2:]
        raise SystemExit("RUN NOW: %s" % hits[-1])

# 1. emitters off
for oid in emitters:
    try:
        c = sk.click(object_id=oid, expect_name="emitter")
        time.sleep(0.8)
        out["done"].append("emitter %s: %s" % (oid, ((re.search(r"You turn (on|off)", c.text or "") or [0, "?"])[1] if re.search(r"You turn (on|off)", c.text or "") else "?")))
    except Exception as ex:
        out["done"].append("emitter %s: %s" % (oid, str(ex)[:40]))
    watch("after emitter %s" % oid)

# 2. panic siphon + widenet scrubbers via air alarm
if alarm:
    bot.goto(object_id=alarm, adjacent=True); time.sleep(0.25)
    sk.click(object_id=alarm, expect_name="Air Alarm"); time.sleep(1.4)
    wins = (sk.tgui_windows().text or "")
    aw = None
    for m in re.finditer(r"tgui-window-\d+:", wins):
        wid = m.group(0).rstrip(":")
        d = sk.tgui_window(id=wid).text or ""
        if "AirAlarm" in d:
            aw = wid; break
    if aw:
        a = sk.tgui_act(id=aw, action="mode", params={"mode": "/datum/air_alarm_mode/panic_siphon"})
        time.sleep(0.5)
        out["done"].append("panic_siphon")
        d = sk.tgui_window(id=aw, path="data.scrubbers").text or ""
        for ref, oid in re.findall(r'"refID": "([^"]+)" \(= obj (\d+)', d):
            sk.tgui_act(id=aw, action="widenet", params={"ref": ref, "val": 1})
            time.sleep(0.3)
        out["done"].append("widenet x%d" % len(re.findall(r"refID", d)))
        sk.tgui_send(id=aw, type="close")
    watch("after alarm")

# 3. open N2 canister valves
for cid in canisters:
    try:
        bot.goto(object_id=cid, adjacent=True); time.sleep(0.25)
        for cand in [k.strip().rstrip(":") for k in (sk.tgui_windows().text or "").split("\n") if "tgui-window" in k]:
            try: sk.tgui_send(id=cand, type="close")
            except Exception: pass
        sk.click(object_id=cid, expect_name="canister"); time.sleep(1.2)
        wins = (sk.tgui_windows().text or "")
        win = None
        for m in re.finditer(r"tgui-window-\d+:", wins):
            wid = m.group(0).rstrip(":")
            d = sk.tgui_window(id=wid).text or ""
            if "Canister" in d:
                win = wid; break
        if win:
            vo0 = re.search(r'"valveOpen": (\d)', sk.tgui_window(id=win).text or "")
            if not vo0 or vo0.group(1) == "0":
                sk.tgui_act(id=win, action="valve", params={}); time.sleep(0.4)
            vo = re.search(r'"valveOpen": (\d)', sk.tgui_window(id=win).text or "")
            out["done"].append("canister %s valveOpen=%s" % (cid, vo.group(1) if vo else "?"))
            sk.tgui_send(id=win, type="close")
    except Exception as ex:
        out["done"].append("canister %s: %s" % (cid, str(ex)[:40]))
    watch("after canister %s" % cid)

out["next"] = "agent: re-run cims_read.py; if integrity still falling and no countdown -> flee 10+ tiles (sk.move) away from the crystal NOW"
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
