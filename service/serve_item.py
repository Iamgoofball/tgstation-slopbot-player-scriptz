# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Serve an item to a patron (Bartender): fetch by name, then offer it.

Two serve modes:
- default: walk next to the patron, press G (the OFFER hotkey) while holding
  the item. NEVER a plain click - a click with an item in hand USES the item
  on the mob (throw/splash/pour/strike).
- {"table": true}: set the item on a table (name via "table_name", default
  "table") next to the patron instead of handing it over.

Item found by name - exact match preferred ("space beer", not "broken space
beer"), in view first, then from remembered tiles. Verified by the hand
emptying (+ the item being on the table in table mode). Patrons can REFUSE
an offer; read the chat tail, never repeat, stow the item and move on.

Run: run_script {script: ".../service/serve_item.py",
                 args: {"item": "space beer", "mob": "John Alcoholic",
                        "say": "Fresh one, on the house."}}
Table mode: args: {"item": "...", "table": true, "say": "..."}
Returns {ok, item, mob, now, rev}.
"""
import re, time
opts = args or {}
item_name = opts.get("item")
mob_name = opts.get("mob")
table_mode = bool(opts.get("table"))
line = opts.get("say") or ""
if not item_name or (not mob_name and not table_mode):
    raise ValueError('args: {"item": "space beer", "mob": "John Alcoholic", "say": "..."} '
                     'or {"item": "...", "table": true} to set it on a table')
out = {"ok": True, "item": item_name, "mob": mob_name}


def _hand_item():
    inv = (sk.inventory().text or "")
    act = [l for l in inv.split("\n") if "active_hand" in l]
    if act and "empty" in act[0]:
        return None
    m = re.search(r'obj (\d+) "([^"]+)"', act[0]) if act else None
    return m.group(2) if m else "unknown"


def _held_somewhere(name):
    """True if the item is already in EITHER hand (active or not). Parses the
    "- obj N \"name\" [state]: in slot \"left/right hand\"" lines directly -
    a regex OR chain missed names that carry a state suffix (e.g. a drink
    renamed to its recipe, \"Screwdriver\" [screwdriverglass])."""
    inv = (sk.inventory().text or "")
    for m in re.finditer(r'- obj (\d+) "([^"]*)"[^\n]*in slot "(left|right) hand"', inv):
        if name.lower() in m.group(2).lower():
            return True
    return False


def _late_acceptance(name):
    """True if the chat log already shows the patron taking this item
    ('X takes NAME from Y'). An offer can land LONG after the 'did not
    transfer' verdict - the patron's acceptance arrives between runs.
    Never re-offer an accepted drink."""
    log = "\n".join(_RAW_LOG)
    return bool(re.search(r'takes[^\n]*%s[^\n]*from|%s[^\n]*from' % (re.escape(name), re.escape(name)), log, re.I))


def _find(name, query, in_view=True, exact=False):
    s = (sk.search(query=query, in_view=in_view).text or "")
    pat = (r'- (?:obj|mob) (\d+) "([^"]*)"' if exact else
           r'- (?:obj|mob) (\d+) "([^"]*' + re.escape(name) + r'[^"]*)"')
    for m in re.finditer(pat, s):
        if exact and m.group(2) != name:      # "broken space beer" != "space beer"
            continue
        if not exact and name not in m.group(2):
            continue
        p = re.search(r'at (\d+),(\d+)', s[m.start():])
        return (int(m.group(1)), m.group(2),
                (int(p.group(1)), int(p.group(2))) if p else None)
    return None, None, None


# ---- combat mode OFF (a held item clicked on a mob with combat on = attack) ----
st = (sk.status().text or "")
cm = [l for l in st.split("\n") if "combat" in l.lower()][:1]
if cm and "combat_off" not in cm[0]:
    for m in re.finditer(r'obj (\d+) "toggle combat mode"', sk.screen().text or ""):
        sk.click(object_id=int(m.group(1))); time.sleep(0.6); break
out["combat"] = [l.strip()[:60] for l in
                 [x for x in (sk.status().text or "").split("\n") if "combat" in x.lower()]][:1]

# ---- pick up the item: EXACT name wins at any distance; substring only
#      as a last resort. A near "broken space beer" must not beat a far
#      "space beer" - that is how John got TWO broken bottles. ----
held = _hand_item()
if _held_somewhere(item_name):
    holding = True
    if held is None or item_name[:6] not in (held or "").lower():
        sk.key(key="X"); time.sleep(0.6)   # bring it to the active hand
    held = _hand_item()
else:
    holding = False
if not holding:
    iid, iname, ipos = _find(item_name, item_name, True, exact=True)
    if not iid:
        iid, iname, ipos = _find(item_name, item_name, False, exact=True)
    if not iid:
        iid, iname, ipos = _find(item_name, item_name, True)
    if not iid:
        iid, iname, ipos = _find(item_name, item_name, False)
    if not iid:
        raise RuntimeError("item not found: " + item_name)
    if "broken" in iname.lower() and "broken" not in item_name.lower():
        raise RuntimeError('refusing to fetch "%s" for "%s" (exact stock exhausted?)'
                           % (iname, item_name))
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
if _late_acceptance(item_name) and not opts.get("table"):
    raise RuntimeError("%s was already taken from us (check chat before "
                       "re-serving; accepted offers land late)" % item_name)
out["item_held"] = (held if holding else _hand_item()) or item_name

# ---- serve: table mode (set it on a table next to them) or G offer ----
if opts.get("table"):
    tbl = _find(opts.get("table_name") or "table", opts.get("table_name") or "table", True)
    if not tbl[0]:
        raise RuntimeError("no table in view to set the item on")
    bot.goto(x=tbl[2][0], y=tbl[2][1]); time.sleep(0.4)   # goto falls back adjacent
    tbl2 = _find(opts.get("table_name") or "table", opts.get("table_name") or "table", True)
    sk.click(object_id=(tbl2[0] or tbl[0]), expect_name=None); time.sleep(1.0)
    placed = _hand_item() is None
    on_table = bool(_find(item_name, item_name, True)[0])
    out["ok"] = placed and on_table
    if not out["ok"]:
        out["detail"] = "hand still full or item not on the table after the click"
else:
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
    sk.key(key="G"); time.sleep(1.0)   # OFFER hotkey; NEVER a click (uses the item on them)
    out["ok"] = _hand_item() is None
    if not out["ok"]:
        out["detail"] = ("offer did not transfer: patron may refuse, have full "
                         "hands, or be too far; read the chat tail")
if line:
    sk.say(line); time.sleep(0.8)

now = sk.status()
RESULT = dict(out, now=(now.get("you") or "")[:80], rev=now.rev)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
