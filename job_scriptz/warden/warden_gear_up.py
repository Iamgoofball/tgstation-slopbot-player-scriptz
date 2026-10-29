# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'),
          encoding='utf-8').read())
precheck()
"""Gear up from the warden's locker in Brig Control: unlock + open it, take
the shift kit (Type 5 laser gun, box of flashbangs, box of spare zipties,
security door remote) into the backpack, close the locker. Re-run safe:
already-taken items are skipped, the locker state is checked first.

Run: run_script {script: ".../job_scriptz/warden/warden_gear_up.py",
                 args: {"locker"?: <obj id>, "x"?, "y"?,   # else auto-find
                        "bp"?: <backpack obj id>,          # else slot "back"
                        "say"?: true}}                     # :s check-in
Warden's locker on MetaStation: 23163 at (105,165) in Brig Control (dense -
walk ADJACENT to it, clicks beyond 1 tile are silently ignored - learned the
hard way: 3 clicks "nothing visible happened" from 2 tiles away).

Locker stock (this round, left in place): loaded security belt (pepperspray,
cuffs, flashbang, flash, stunbaton overlays - the spawn PDA occupies my belt
slot), compact combat shotgun, holobarrier projector, bandolier, seclite,
warden's garment bag, security radio headset, jumbo dog bone (McGriff's).

Fork truths (live-verified):
  - The warden's locker unlocks + opens with two ADJACENT empty-hand clicks,
    same as the secoff locker (1st = unlock, 2nd = open; contents spill onto
    the locker's tile line as "- obj NNNN" entries).
  - Verify pickups via STATUS `active_hand:` (the inventory tool read can
    RACE a fresh click and report stale empty hands; status after a settle
    sleep is reliable). A click with a FULL hand is an in-hand USE of what
    you hold - for a laser gun that is a fire risk: always empty the hand
    (store or drop) before the next pickup click.
  - E hotkey = quick-equip; Shift+E draws the belt's first item.
"""
import re

opts = args or {}
out = {"taken": [], "verdict": []}

KIT = [("Type 5 laser", r"laser gun"),
       ("flashbangs", r"box of flashbangs"),
       ("zipties", r"box of spare zi?pties|zipties"),
       ("door remote", r"security door remote")]


def read_status():
    time.sleep(0.9)
    return (sk.status().text or "")


def active_hand(t=None):
    t = t or read_status()
    m = re.search(r"active_hand: (left|right) hand: (.*)", t)
    if not m:
        return None
    item = m.group(2).split("\n")[0].strip()
    return {"hand": m.group(1), "item": item,
            "empty": item.startswith("empty")}


def read_inventory():
    time.sleep(0.9)
    return (sk.inventory().text or "")


def slot_of(oid):
    for l in read_inventory().split("\n"):
        m = re.match(r'- obj (\d+) "([^"]*)".*in slot "([^"]*)"', l.strip())
        if m and int(m.group(1)) == oid:
            return m.group(3)
    return None


def empty_hand_via(bp):
    """Store the held item in the backpack, or drop it as a last resort."""
    ah = active_hand()
    if not ah or ah["empty"]:
        return True
    if bp:
        sk.click(object_id=bp)
        time.sleep(1.2)
        ah = active_hand()
        if not ah or ah["empty"]:
            return True
    sk.key(key="Q")
    time.sleep(0.7)
    ah = active_hand()
    return not ah or ah["empty"]


def find_locker():
    lid = opts.get("locker")
    lx, ly = opts.get("x"), opts.get("y")
    if lid and lx is not None:
        return lid, lx, ly
    s = sk.search(query="warden's locker", kind="obj",
                  page_size=5).text or ""
    for l in s.split("\n"):
        m = re.match(r"- obj (\d+) \"warden's locker\" at (\d+),(\d+)",
                     l.strip())
        if m:
            return (lid or int(m.group(1)), int(m.group(2)),
                    int(m.group(3)))
    return (lid, lx, ly)


def locker_state(lid, lx, ly):
    t = (sk.tile(lx, ly, all=True).text or "")
    line = next((l for l in t.split("\n") if ("obj %d " % lid) in l), "")
    locked = "[locked]" in line
    opened = "[warden_open]" in line or "sec_open" in line
    return {"line": line.strip()[:180], "locked": locked, "open": opened}


# ---- locate + approach
lid, lx, ly = find_locker()
if not lid or lx is None:
    RESULT = {"ok": False, "note": "warden's locker not found"}
else:
    out["locker"] = {"id": lid, "x": lx, "y": ly}
    g = bot.goto(x=lx, y=ly, max_steps=40)
    out["walk"] = "arrived" in (g.text or "")
    st = read_status()
    my = re.search(r"at (\d+),(\d+),\d+", st)
    myx, myy = (int(my.group(1)), int(my.group(2))) if my else (None, None)
    out["adjacent"] = myx is not None and abs(myx - lx) <= 1 and \
        abs(myy - ly) <= 1
    if not out["adjacent"]:
        out["verdict"].append("NOT adjacent to the locker at (%d,%d) - "
                              "clicks beyond 1 tile are ignored"
                              % (lx, ly))

    # ---- backpack id (fall back to arg)
    bp = opts.get("bp")
    if not bp:
        m = re.search(r'- obj (\d+) "[^"]*backpack".*in slot "back"',
                      read_inventory())
        bp = int(m.group(1)) if m else None
    out["backpack"] = bp

    # ---- open the locker if needed
    state = locker_state(lid, lx, ly)
    out["state_before"] = state
    if not state["open"]:
        empty_hand_via(bp)
        sk.click(object_id=lid)
        time.sleep(1.4)
        state = locker_state(lid, lx, ly)
        if not state["open"] and state["locked"]:
            sk.click(object_id=lid)   # still locked: unlock click
            time.sleep(1.4)
            state = locker_state(lid, lx, ly)
        if not state["open"]:
            sk.click(object_id=lid)   # unlocked but closed: open click
            time.sleep(1.4)
            state = locker_state(lid, lx, ly)
        out["opened"] = state["open"]
        if not state["open"]:
            out["verdict"].append("locker did not open - see state")

    # ---- take the kit
    if state["open"]:
        t = (sk.tile(lx, ly, all=True).text or "")
        items = {}
        for l in t.split("\n"):
            m = re.match(r'- obj (\d+) "([^"]*)"', l.strip())
            if m:
                items[int(m.group(1))] = m.group(2)
        for label, pat in KIT:
            # skip if already on me (re-run safety)
            inv = read_inventory()
            held_or_worn = any(
                re.match(r'- obj (\d+) "([^"]*)".*in slot "([^"]*)"',
                         l.strip()) and re.search(pat, l, re.I)
                for l in inv.split("\n"))
            if held_or_worn:
                out["taken"].append({"item": label, "skipped": True})
                continue
            oid = next((i for i, n in items.items() if re.search(pat, n, re.I)),
                       None)
            if not oid:
                out["verdict"].append("%s: not in the locker" % label)
                continue
            ok = False
            for attempt in (1, 2):
                empty_hand_via(bp)
                sk.click(object_id=oid)
                ah = active_hand()
                if ah and not ah["empty"] and str(oid) in ah["item"]:
                    if bp:
                        sk.click(object_id=bp)
                        time.sleep(1.2)
                        ah = active_hand()
                        ok = not ah or ah["empty"]
                    else:
                        ok = True   # left in hand on purpose
                    break
                time.sleep(1.0)
            out["taken"].append({"item": label, "id": oid, "stored": ok})
            if not ok:
                out["verdict"].append("%s (obj %d) not stored - check the "
                                      "hand/backpack" % (label, oid))
        # ---- close the locker with empty hands
        empty_hand_via(bp)
        sk.click(object_id=lid)
        time.sleep(1.4)
        state2 = locker_state(lid, lx, ly)
        out["closed"] = not state2["open"]
        out["state_after"] = state2
        if not out["closed"]:
            out["verdict"].append("locker still open - close it by hand")

    # ---- radio check-in
    if opts.get("say", True):
        try:
            sk.say(text="Warden on shift. Brig and Armory under watch.",
                   radio="security")
            time.sleep(0.6)
            out["said"] = True
        except Exception as exc:
            out["verdict"].append("radio say failed: %s" % exc)

RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
