# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Mix a drink in a container via a ChemDispenser (bartender).

The LIVE-VERIFIED workflow (booze dispenser / soda dispenser both):
  1. hold the container in the ACTIVE hand (vend bottles land in an empty
     active hand; a container already held must be in the active hand)
  2. walk ADJACENT to the machine (in view is NOT in reach) and click it
  3. tgui_act insert {}   -> puts the active-hand container INTO the machine
  4. per dose: tgui_act amount {target: N}  (5/10/15/20/25/30/50)
               tgui_act dispense {reagent: "<spirit or mixer name>"}
  5. tgui_act eject {}    -> container comes back to the active hand
  6. close the window
Recipes auto-convert (e.g. vodka + orange juice 1:2 -> Screwdriver).

Run: run_script {script: ".../service/dispenser_mix.py",
                 args: {"machine": "booze dispenser",
                        "container": "shaker",
                        "doses": [{"reagent": "Vodka", "amount": 25}],
                        "say": "Screwdriver, fresh from the tap."}}
machine: name (substring ok, "booze dispenser" / "soda dispenser").
container: item to mix in (fetched by exact name if not held).
doses: list of {reagent, amount}; machine type must match the reagent
       (spirits on the booze dispenser, juices/water/ice/cola on the soda one).
Returns {ok, machine, container, doses_applied, contents, rev}.
"""
import re, time
opts = args or {}
machine_name = opts.get("machine") or ""
container_name = opts.get("container") or ""
doses = opts.get("doses") or []
if not machine_name or not container_name or not doses:
    raise ValueError('args: {"machine": "booze dispenser", "container": "shaker",'
                     ' "doses": [{"reagent": "Vodka", "amount": 25}], "say": "..."}')
out = {"ok": True, "machine": machine_name, "container": container_name,
       "doses_applied": []}


def _find(name, query, in_view=True, exact=False):
    s = (sk.search(query=query, in_view=in_view).text or "")
    pat = (r'- (?:obj|mob) (\d+) "([^"]*)"' if exact else
           r'- (?:obj|mob) (\d+) "([^"]*' + re.escape(name) + r'[^"]*)"')
    for m in re.finditer(pat, s):
        if exact and m.group(2) != name:
            continue
        if not exact and name not in m.group(2):
            continue
        p = re.search(r'at (\d+),(\d+)', s[m.start():])
        return (int(m.group(1)), m.group(2),
                (int(p.group(1)), int(p.group(2))) if p else None)
    return None, None, None


def _find_carried(name):
    """Where is this item, even if it is not on a floor tile? Patrons and
    crew PICK THINGS UP: an item that 'vanished' is often in a nearby mob's
    hand. Two checks: (1) search reports 'carried by <mob>' for held items;
    (2) EXAMINING a mob shows what they wear and hold in their hands - so
    sweep nearby mobs with examine when the search comes up empty. An
    inventory rustle sound in the sound log is the pocketing tell."""
    for in_view in (True, False):
        s = (sk.search(query=name, in_view=in_view).text or "")
        for m in re.finditer(r'- obj (\d+) "([^"]*%s[^"]*)"[^\n]*carried by ([^\n\)]+)'
                             % re.escape(name), s, re.I):
            return (int(m.group(1)), m.group(2), m.group(3).strip()[:60])
    # sweep the mobs in view: their examine lists worn + held items
    lk = sk.look().text or ""
    for m in re.finditer(r'- mob (\d+) "([^"]+)"', lk):
        ex = sk.examine(int(m.group(1)))
        exs = ex.text or ""
        for im in re.finditer(r'obj (\d+) "([^"]*)"', exs):
            if name.lower() in im.group(2).lower() and (
                    "hand" in exs[max(0, im.start() - 120):im.end() + 120].lower()):
                return (int(im.group(1)), im.group(2),
                        'held/worn by %s' % m.group(2))
    return None, None, None


def _hand_item():
    inv = (sk.inventory().text or "")
    act = [l for l in inv.split("\n") if "active_hand" in l]
    if act and "empty" in act[0]:
        return None
    m = re.search(r'obj (\d+) "([^"]+)"', act[0]) if act else None
    return m.group(2) if m else "unknown"


def _newest_window():
    """id of the newest open tgui window (the one a machine click opened)."""
    ws = sk.tgui_windows()
    ids = [k for k in (ws.text or "").split("\n") if k.strip().endswith(":")
           and k.strip().startswith("tgui-window")]
    return ids[-1].strip().rstrip(":") if ids else "tgui-window-1"


# ---- container in the ACTIVE hand ----
inv = (sk.inventory().text or "")
held = None
for m in re.finditer(r'- obj (\d+) "([^"]*)"[^\n]*in slot "(left|right) hand"', inv):
    if container_name.lower() in m.group(2).lower():
        held = (m.group(1), m.group(2))
if held is None:
    cid, cname, cpos = _find(container_name, container_name, True, exact=True)
    if not cid:
        cid, cname, cpos = _find(container_name, container_name, False, exact=True)
    if not cid:
        # not on any tile: someone may have pocketed it (rustle sound = a
        # mob moved it into a bag); check hands/bags before giving up
        cid, cname, carrier = _find_carried(container_name)
        if cid:
            raise RuntimeError('container "%s" is %s - ask for it back or '
                               'use another' % (container_name, carrier))
        raise RuntimeError("container not found: " + container_name)
    if cpos:
        bot.goto(x=cpos[0], y=cpos[1]); time.sleep(0.4)
    cid2, cname2, _ = _find(container_name, container_name, True, exact=True) or (cid, cname, cpos)
    if _hand_item() is not None:
        sk.key(key="X"); time.sleep(0.6)
        if _hand_item() is not None:
            raise RuntimeError("both hands full, cannot pick up " + container_name)
    sk.click(object_id=(cid2 or cid), expect_name=(cname2 or cname)[:40]); time.sleep(0.8)
    if container_name[:6].lower() not in (_hand_item() or "").lower():
        raise RuntimeError("container pickup failed, holding: " + str(_hand_item()))
else:
    if _hand_item() is None or container_name[:6].lower() not in (_hand_item() or "").lower():
        sk.key(key="X"); time.sleep(0.6)   # bring it to the active hand
out["container_held"] = _hand_item()

# ---- walk adjacent to the machine and open it (empty-ish click is fine:
#      the machine UI opens regardless of what the active hand holds) ----
mid, mname, mpos = _find(machine_name, machine_name, True)
if not mid:
    mid, mname, mpos = _find(machine_name, machine_name, False)
if not mid:
    raise RuntimeError("machine not found: " + machine_name)
if mpos:
    bot.goto(x=mpos[0], y=mpos[1]); time.sleep(0.4)   # goto lands adjacent
mid2, mname2, _ = _find(machine_name, machine_name, True) or (mid, mname, mpos)
sk.click(object_id=(mid2 or mid), expect_name=(mname2 or mname)[:40]); time.sleep(1.2)
wid = _newest_window()
out["window"] = wid
winfo = sk.tgui_windows()
if "tgui-window" not in (winfo.text or ""):
    raise RuntimeError("no ChemDispenser window opened (was the click adjacent?)")

# ---- insert the container ----
sk.tgui_act(wid, "insert"); time.sleep(0.8)

# ---- doses ----
for d in doses:
    reag = d.get("reagent") or ""
    amt = int(d.get("amount") or 25)
    if amt not in (5, 10, 15, 20, 25, 30, 50):
        amt = min((5, 10, 15, 20, 25, 30, 50), key=lambda v: abs(v - amt))
    sk.tgui_act(wid, "amount", {"target": amt}); time.sleep(0.6)
    sk.tgui_act(wid, "dispense", {"reagent": reag}); time.sleep(1.0)
    # live-verified: the tgui response wording does not reliably contain a
    # success token - the FINAL examine of the container is the real verdict
    out["doses_applied"].append({"reagent": reag, "amount": amt, "ok": True})

# ---- eject + close ----
sk.tgui_act(wid, "eject"); time.sleep(0.8)
sk.tgui_send(wid, "close"); time.sleep(0.4)

# ---- verify: find the container wherever it is, examine its reagents ----
# it may not be in hand after eject: someone nearby may have grabbed it
cid, cname, carrier = _find_carried(container_name)
if cid:
    ex = sk.examine(cid)
    out["contents"] = [l.strip()[:90] for l in (ex.text or "").split("\n")
                       if "units of" in l or "contains" in l]
    out["where"] = ("in hand" if container_name[:6].lower()
                    in (_hand_item() or "").lower()
                    else "carried by " + str(carrier))
if not cid:
    out["note"] = "container vanished after eject (was it picked up?)"
out["ok"] = bool(out.get("contents"))
if opts.get("say"):
    sk.say(opts.get("say")); time.sleep(0.8)

now = sk.status()
RESULT = dict(out, now=(now.get("you") or "")[:80], rev=now.rev)
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
