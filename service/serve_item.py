# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Serve an item to a patron (Bartender): fetch by name, hand it over, verify.

Finds the item in view (or fetches it from a remembered tile), picks it up,
walks next to the patron (mob, found BY NAME), clicks them with the item in
the active hand - a plain click with an item on a mob GIVES it (help intent;
combat mode must be off) - and verifies by the hand emptying. Never hard-code
ids: item and mob are name args.

Run: run_script {script: ".../service/serve_item.py",
                 args: {"item": "space beer", "mob": "John Alcoholic",
                        "say": "Fresh one, on the house."}}
Returns {ok, item, mob, now, rev}.
"""
import re, time
opts = args or {}
item_name = opts.get("item")
mob_name = opts.get("mob")
line = opts.get("say") or ""
if not item_name or not mob_name:
    raise ValueError('args: {"item": "space beer", "mob": "John Alcoholic", "say": "..."}')
out = {"ok": True, "item": item_name, "mob": mob_name}


def _hand_item():
    inv = (sk.inventory().text or "")
    act = [l for l in inv.split("\n") if "active_hand" in l]
    if act and "empty" in act[0]:
        return None
    m = re.search(r'obj (\d+) "([^"]+)"', act[0]) if act else None
    return m.group(2) if m else "unknown"


def _find(name, query, in_view=True):
    s = (sk.search(query=query, in_view=in_view).text or "")
    m = re.search(r'- (?:obj|mob) (\d+) "([^"]*' + re.escape(name) + r'[^"]*)"', s)
    if not m:
        return None, None, None
    p = re.search(r'at (\d+),(\d+)', s)
    return (int(m.group(1)), m.group(2),
            (int(p.group(1)), int(p.group(2))) if p else None)


# ---- combat mode OFF (a held item clicked on a mob with combat on = attack) ----
st = (sk.status().text or "")
cm = [l for l in st.split("\n") if "combat" in l.lower()][:1]
if cm and "combat_off" not in cm[0]:
    for m in re.finditer(r'obj (\d+) "toggle combat mode"', sk.screen().text or ""):
        sk.click(object_id=int(m.group(1))); time.sleep(0.6); break
out["combat"] = [l.strip()[:60] for l in
                 [x for x in (sk.status().text or "").split("\n") if "combat" in x.lower()]][:1]

# ---- pick up the item (in view > known out of view) ----
iid, iname, ipos = _find(item_name, item_name, True)
if not iid:
    iid, iname, ipos = _find(item_name, item_name, False)
if not iid:
    raise RuntimeError("item not found: " + item_name)
# in view is NOT in reach: interaction range ~1 tile, so ALWAYS walk adjacent
if ipos:
    bot.goto(x=ipos[0], y=ipos[1]); time.sleep(0.4)   # goto falls back to a free tile
    iid, iname, ipos = _find(item_name, item_name, True) or (iid, iname, ipos)
if _hand_item() is not None:
    sk.key(key="X"); time.sleep(0.6)
    if _hand_item() is not None:
        raise RuntimeError("both hands full, cannot pick up " + item_name)
sk.click(object_id=iid, expect_name=(iname or item_name)[:40]); time.sleep(0.8)
if item_name[:6] not in (_hand_item() or "").lower():
    raise RuntimeError("pickup failed, holding: " + str(_hand_item()))

# ---- walk to the patron and hand it over ----
mid, mname, mpos = _find(mob_name, mob_name, True)
if not mid:
    mid, mname, mpos = _find(mob_name, mob_name, False)
if not mid:
    raise RuntimeError("patron not found: " + mob_name)
if mpos:
    bot.goto(x=mpos[0] - 1, y=mpos[1]); time.sleep(0.4)
mid2, _, _ = _find(mob_name, mob_name, True)   # re-find after the walk
if not mid2:
    raise RuntimeError("patron lost from view after walking: " + mob_name)
sk.click(object_id=mid2, kind="mob", expect_name=mname[:40]); time.sleep(1.0)
given = _hand_item() is None
if line:
    sk.say(line); time.sleep(0.8)
out["ok"] = given
if not given:
    out["detail"] = "item still in hand after the click (maybe full hands or intent)"

now = sk.status()
RESULT = dict(out, now=(now.get("you") or "")[:80], rev=now.rev)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
