# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Run ONE radial-menu surgery op on a mob: ensure the tool is in the active
hand, (optionally re-drape), click the patient, parse the radial from the click
answer, click the op button immediately, wait, verify via chat.

Run: run_script {script: "E:/byond_agent_test/tgstation-slopbot-player-scriptz/medical/surgery.py",
                 args: {"mob": 20, "expect_name": "Parabellum Phillips",
                        "tool": "hemostat", "op": "graft coronary bypass"}}
Optional: {"drape": true} to re-apply surgical drapes first (prep expires after
~2-3 min of game time — drape before every op in a long chain), {"wait": s} to
override the op duration.

Fork truths baked in: the radial only appears in the CLICK ANSWER
(`menu_opened:` + `- obj <id> "<op>"` lines) — menus are not searchable screen
objects afterwards. Click the choice id from the SAME answer at once; menus
close on move/timeout and their ids go stale. "he is dead!" floating text means
the ACTIVE hand held the wrong item (medkit/stack), not that surgery refused.
"already performing surgery!" means wait, don't re-click. tend-wounds
(hemostat) LOOPS until brute = 0 and blocks all other surgery meanwhile.
"""
import re

opts = args or {}
mob = opts.get("mob"); name = opts.get("expect_name") or ""
tool = (opts.get("tool") or "").lower()
op = opts.get("op") or ""
drape = bool(opts.get("drape"))
if mob is None or not op:
    raise ValueError("args: {'mob': id, 'expect_name': 'name', 'tool': 'hemostat|scalpel|saw|screwdriver|cautery|drapes', 'op': 'radial op name', 'drape': bool?}")

# op durations (seconds) from the source; override with wait
DUR = {"incise": 4, "retract": 4, "clamp": 4, "saw": 8, "incise organs": 4,
       "graft coronary bypass": 11, "remove heart": 7, "remove lungs": 7,
       "remove liver": 7, "remove stomach": 7, "mend skin incision": 4,
       "brain surgery": 12, "repair brain": 12}
wait = float(opts.get("wait") or DUR.get(op.lower(), 6))
out = {"mob": mob, "op": op, "tool": tool, "wait": wait}

# --- re-find the patient (client forgets out-of-view mobs; skip ghosts) ---
m0 = re.search(r"mob (\d+)", sk.status().get("you") or "")
me = int(m0.group(1)) if m0 else None
if name:
    s = sk.search(query=name, kind="mob", all_things=True).text or ""
    for l in s.split("\n"):
        mm = re.search(r"mob (\d+) \"" + re.escape(name), l)
        if mm and int(mm.group(1)) != me and "ghost" not in l and "invisible" not in l:
            if int(mm.group(1)) != mob:
                out["refound_as"] = int(mm.group(1)); mob = int(mm.group(1))
            break

def hands():
    return (sk.inventory().text or "").split("\n")

def hand_with(substr):
    for l in hands():
        if substr in l and "in slot" in l and "hand" in l:
            active = "handactive" in l
            return ("active" if active else "other"), l
    return None, None

def pick_from_world(substr):
    s = sk.search(query=substr, all_things=True).text or ""
    m = re.search('obj (\\d+) "' + re.escape(substr) + '" (at|\\[screen)', s)
    if m:
        sk.click(object_id=int(m.group(1)), expect_name=substr); time.sleep(0.6)
    return hand_with(substr)[0] is not None

def ensure_active(substr):
    """Make `substr` the active-hand item: activate its hand, or pick it up."""
    where, _ = hand_with(substr)
    if where == "active":
        return True
    if where == "other":
        sk.key(key="X"); time.sleep(0.4)   # X swaps: other hand's item becomes active
        return hand_with(substr)[0] == "active"
    # not held: free the active hand (Q drops) then pick up
    for l in hands():
        if "handactive" in l and "in slot" in l:
            sk.key(key="Q"); time.sleep(0.4); break
    return pick_from_world(substr)

out["tool_ready"] = bool(ensure_active(tool)) if tool else True
if drape:
    dr = ("drapes" if not tool or tool != "drapes" else tool)
    out["drape_ready"] = bool(ensure_active("surgical drapes"))
    c = sk.click(object_id=mob, expect_name=name or None); time.sleep(1.5)
    out["drape_click"] = "Prepare" in (c.text or "") or "drapes" in (c.text or "")
    if tool and tool != "drapes":
        out["tool_ready"] = bool(ensure_active(tool))

if not out["tool_ready"]:
    raise SystemExit("tool '%s' not in hands and not findable in view" % tool)

bot.goto(object_id=mob, expect_name=name or None, adjacent=True)
time.sleep(0.3)

# --- open the radial and click the chosen op in the same breath ---
c = sk.click(object_id=mob, expect_name=name or None)
time.sleep(2.0)
t = c.text or ""
ids = dict((n, int(i)) for i, n in re.findall('- obj (\\d+) "([^"]+)"', t))
out["menu_opened"] = "menu_opened" in t
out["menu_closed"] = "menu_closed" in t
out["choices"] = list(ids)
out["blocked"] = "already performing" in t

target = ids.get(op)
if "menu_opened" not in t:
    out["ok"] = False
    out["stage"] = "menu did not open (prep expired? wrong tool? wrong zone?); click answer tail"
    out["tail"] = t[-200:]
elif target is None:
    out["ok"] = False
    out["stage"] = "op not in this radial (already done, one-shot consumed, or state missing)"
else:
    cb = sk.click(object_id=target, expect_name=op)
    time.sleep(1.0)
    out["btn_clicked"] = ("clicked: obj %d" % target) in (cb.text or "")
    time.sleep(wait)
    ch = _pull_chat(2)
    out["chat"] = [l[:140] for l in ch.split("\n")
                   if re.search(r"succeed|fail|begin|surger|remov|graft|repair", l, re.I)][:6]
    out["ok"] = bool(out["chat"])
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
