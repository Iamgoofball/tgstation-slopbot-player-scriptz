# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'),
          encoding='utf-8').read())
precheck()
"""Gear up from a security officer's locker in the Security Locker Room
(Gear Room): unlock + open the locker, free the belt slot (PDA -> backpack),
wear the security belt, the HUDSunglasses, attach the seclite to the helmet,
stash the enhanced retrieval gloves in the backpack, close the locker, draw
+ turn on the stun baton. Re-run safe: worn steps are skipped.

Run: run_script {script: ".../job_scriptz/security-officer/security_gear_up.py",
                 args: {"locker"?: <obj id>, "x"?, "y"?,   # locker to use
                        "say"?: true}}                     # :s check-in at the end
Stand in the Security Locker Room (MetaStation: officer lockers along x=110,
y=174-177; nearest the middle is 24420 at (110,177)).

Fork truths (live-verified this round, mob 2897):
  - **E hotkey = quick-equip** the active-hand item. NEVER click a HELD item's
    id to equip: the driver resolves it to the item's STALE FLOOR position and
    the click lands on whatever is there now - it stuffed my belt into the
    open locker twice.
  - Belt wear needs the belt slot EMPTY first (no auto-swap on this fork):
    click the worn PDA (belt slots are always-visible HUD icons -> id clicks
    resolve fine) to take it, click the worn BACKPACK id to store it, then
    wear the belt with E.
  - Hidden worn slots (head/eyes/suit/ears/...) have NO on-screen icon until
    the inventory HUD is EXPANDED: click the HUD "toggle" button (find its id
    in the inventory note: `click the HUD button "toggle" (obj NNNN)`).
    Only then does the helmet's slot icon exist for the seclite attach.
  - Locker: 1st click = UNLOCK, 2nd = OPEN; contents appear as a "menu obj
    ..." list on the locker's tile line - click a listed obj id to take it.
    Clicking the locker WITH a held item = the item goes INTO the locker -
    empty both hands before every locker click.
  - Shift+E draws the belt's FIRST item (if the PDA sits in the belt slot it
    draws the PDA - free the slot first). Z toggles the baton; icon_state
    `stunbaton_active` = ON (the examine text does NOT say "turned on" -
    check the icon or the charge line).
  - Keep the spawn security gloves ON (25% faster cuffing); the enhanced
    retrieval gloves from the locker go to the backpack as spares.
  - The spawn kit already covers: armor vest, helmet, jackboots, bowman
    headset, uniform, gloves, mindshield, disabler (suit storage), cuffs +
    flash (pockets).
"""
import re

opts = args or {}
out = {"worn": {}, "verdict": []}


def inv_lines():
    return (sk.inventory().text or "").split("\n")


def slot_of(oid):
    for l in inv_lines():
        m = re.match(r'- obj (\d+) "([^"]*)".*in slot "([^"]*)"', l.strip())
        if m and int(m.group(1)) == oid:
            return m.group(3)
    for l in inv_lines():
        m = re.match(r'- obj (\d+) "([^"]*)"', l.strip())
        if m and int(m.group(1)) == oid:
            return "on me (hidden)"
    return None


def find_in_slot(slot_pat, name_pat=""):
    for l in inv_lines():
        m = re.match(r'- obj (\d+) "([^"]*)".*in slot "([^"]*)"', l.strip())
        if m and re.search(slot_pat, m.group(3)) and \
                re.search(name_pat, m.group(2), re.I):
            return {"id": int(m.group(1)), "name": m.group(2)}
    return None


def active_obj():
    for l in inv_lines():
        if "lhandactive" in l:
            m = re.match(r"- obj (\d+)", l.strip())
            if m:
                return int(m.group(1))
    return None


def empty_hands():
    n = 0
    while active_obj() is not None and n < 2:
        sk.key(key="Q")
        time.sleep(0.5)
        n += 1
    return active_obj() is None


def equip_active():
    """E hotkey: quick-equip the active-hand item to its slot."""
    sk.key(key="E")
    time.sleep(1.0)


def pickup(oid, x, y):
    """Click a floor/menu item with an empty active hand; returns the hand."""
    if slot_of(oid) in ("left hand", "right hand"):
        return slot_of(oid)
    empty_hands()
    g = bot.goto(x=x, y=y, max_steps=40)   # dense tiles park adjacent
    if "arrived" not in (g.text or ""):
        out["verdict"].append("goto %d,%d failed for obj %d" % (x, y, oid))
    c = sk.click(object_id=oid)
    time.sleep(1.0)
    return slot_of(oid)


def store_active_in(oid):
    """Click a worn storage item's id (visible HUD icon) to store the
    active-hand item."""
    if active_obj() is None:
        return False
    sk.click(object_id=oid)
    time.sleep(1.0)
    return active_obj() is None


def expand_inventory():
    """Click the HUD 'toggle' button so hidden worn slots get on-screen
    icons; returns True when previously-hidden slots show 'in slot'."""
    inv = sk.inventory().text or ""
    m = re.search(r'button "toggle" \(obj (\d+)\)', inv)
    hid_before = inv.count("not shown on screen")
    if m:
        sk.click(object_id=int(m.group(1)))
        time.sleep(1.0)
    inv2 = sk.inventory().text or ""
    out["hud_expanded"] = inv2.count("in slot") > inv.count("in slot") or \
        hid_before > 0 and inv2.count("not shown on screen") < hid_before
    return out["hud_expanded"]


# ---- locate the locker
lx, ly = opts.get("x"), opts.get("y")
locker = opts.get("locker")
if lx is None:
    s = sk.search(query="security officer's locker", page_size=10).text or ""
    for line in s.split("\n"):
        m = re.match(r"- obj (\d+) \"security officer's locker\" at (\d+),(\d+)",
                     line.strip())
        if m:
            locker = locker or int(m.group(1))
            lx, ly = int(m.group(2)), int(m.group(3))
            break
if lx is None:
    RESULT = {"ok": False, "note": "no security officer's locker found"}
else:
    out["locker"] = {"id": locker, "x": lx, "y": ly}
    g = bot.goto(x=lx, y=ly, max_steps=60)
    out["walk"] = "arrived" in (g.text or "")

    expand_inventory()

    belt_worn = find_in_slot("belt", "security belt")
    if not belt_worn:
        # open the locker (unlock, then open); empty hands first
        empty_hands()
        c = sk.click(object_id=locker)
        time.sleep(1.4)
        t = sk.tile(lx, ly, all=True).text or ""
        lkl = [l for l in t.split("\n") if str(locker) in l]
        if not (lkl and "menu obj" in lkl[0]):
            sk.click(object_id=locker)
            time.sleep(1.4)
        out["locker_opened"] = True

        # 1) free the belt slot: PDA out -> backpack
        pda = find_in_slot("belt|pocket", "pda|personal") or \
            find_in_slot("belt", "")
        if pda and re.search(r"pda|personal", pda["name"], re.I):
            sk.click(object_id=pda["id"])       # worn PDA: visible HUD icon
            time.sleep(1.0)
            if slot_of(pda["id"]) in ("left hand", "right hand"):
                bp = find_in_slot("back", "backpack")
                out["pda_stored"] = store_active_in(bp["id"]) if bp else False
                if not out["pda_stored"]:
                    out["verdict"].append("PDA could not be stored - belt "
                                          "wear will fail")
        # 2) security belt -> wear with E
        belt_id = belt = None
        s = sk.search(query="security belt", in_view=True,
                      page_size=20).text or ""
        for line in s.split("\n"):
            m = re.match(r"- obj (\d+) \"security belt\" at (\d+),(\d+)",
                         line.strip())
            if m:
                belt = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if belt and pickup(belt[0], belt[1], belt[2]) in ("left hand",
                                                         "right hand"):
            if active_obj() != belt[0]:
                sk.key(key="X")
                time.sleep(0.4)
            equip_active()
            out["worn"]["belt"] = find_in_slot("belt", "security belt")
            if not out["worn"]["belt"]:
                out["verdict"].append("E did not equip the security belt")
        else:
            out["verdict"].append("no security belt found in the locker")
        # 3) HUDSunglasses -> eyes with E
        hud = None
        s = sk.search(query="HUDSunglasses", in_view=True,
                      page_size=20).text or ""
        for line in s.split("\n"):
            m = re.match(r"- obj (\d+) \"[^\"]*HUDSunglasses\" at (\d+),(\d+)",
                         line.strip())
            if m:
                hud = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if hud and pickup(hud[0], hud[1], hud[2]) in ("left hand",
                                                     "right hand"):
            if active_obj() != hud[0]:
                sk.key(key="X")
                time.sleep(0.4)
            equip_active()
            out["worn"]["eyes"] = find_in_slot("eyes", "HUD")
            if not out["worn"]["eyes"]:
                out["verdict"].append("HUDSunglasses did not equip")
        else:
            out["verdict"].append("no HUDSunglasses found")
        # 4) seclite -> helmet (needs the expanded HUD slot icon)
        helm = find_in_slot("head", "helmet")
        sec = None
        s = sk.search(query="seclite", in_view=True, page_size=20).text or ""
        for line in s.split("\n"):
            m = re.match(r"- obj (\d+) \"seclite\" at (\d+),(\d+)", line.strip())
            if m:
                sec = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if helm and sec and pickup(sec[0], sec[1], sec[2]) in ("left hand",
                                                              "right hand"):
            if active_obj() != sec[0]:
                sk.key(key="X")
                time.sleep(0.4)
            e0 = sk.examine(object_id=helm["id"]).text or ""
            sk.click(object_id=helm["id"])
            time.sleep(1.2)
            e1 = sk.examine(object_id=helm["id"]).text or ""
            out["worn"]["seclite"] = "mounting point for a seclite" not in e1
            if not out["worn"]["seclite"] and \
                    "mounting point for a seclite" not in e0:
                out["worn"]["seclite"] = True   # was attached already
            if not out["worn"]["seclite"]:
                out["verdict"].append("seclite did not attach (helmet slot "
                                      "icon click failed)")
        else:
            out["verdict"].append("no seclite or helmet for the attach step")
        # 5) enhanced retrieval gloves -> backpack (keep the spawn gloves on)
        rg = None
        s = sk.search(query="retrieval", in_view=True, page_size=20).text or ""
        for line in s.split("\n"):
            m = re.match(r"- obj (\d+) \"[^\"]*retrieval[^\"]*\" at (\d+),(\d+)",
                         line.strip())
            if m:
                rg = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if rg and pickup(rg[0], rg[1], rg[2]) in ("left hand", "right hand"):
            bp = find_in_slot("back", "backpack")
            if active_obj() != rg[0]:
                sk.key(key="X")
                time.sleep(0.4)
            out["retrieval_gloves_stored"] = store_active_in(bp["id"]) \
                if bp else False
        # 6) close the locker with EMPTY hands
        if out.get("locker_opened"):
            empty_hands()
            sk.click(object_id=locker)
            time.sleep(1.4)
            t = sk.tile(lx, ly, all=True).text or ""
            lkl = [l for l in t.split("\n") if str(locker) in l]
            out["locker_closed"] = bool(lkl) and "menu obj" not in lkl[0] \
                and "sec_open" not in lkl[0]
            if not out["locker_closed"]:
                out["verdict"].append("locker still open - close it by hand")
    else:
        out["worn"]["belt"] = belt_worn

    # 7) stun baton: draw + ON (icon check, not the examine text)
    held = active_obj()
    baton = held and "baton" in (sk.examine(object_id=held).text or "").lower()
    if not baton:
        empty_hands()
        sk.key(key="Shift+E")
        time.sleep(0.9)
        held = active_obj()
        baton = held and "baton" in \
            (sk.examine(object_id=held).text or "").lower()
    if baton:
        inv = sk.inventory().text or ""
        if "stunbaton_active" not in inv:
            sk.key(key="Z")
            time.sleep(0.7)
            inv = sk.inventory().text or ""
        out["baton"] = {"id": held,
                        "on": "stunbaton_active" in inv,
                        "charge": re.search(r"(\d+)% charge",
                                            sk.examine(object_id=held).text
                                            or "") and
                        int(re.search(r"(\d+)% charge",
                                      sk.examine(object_id=held).text
                                      or "").group(1))}
    else:
        out["verdict"].append("no baton drawn from the belt")

    # 8) radio check-in
    if opts.get("say", True):
        try:
            sk.say(text="Security Officer on shift, geared up. Patrolling "
                        "the brig.", radio="security")
            time.sleep(0.6)
            out["said"] = True
        except Exception as exc:
            out["verdict"].append("radio say failed: %s" % exc)

    out["inventory"] = [l.strip()[:100] for l in inv_lines()
                        if l.strip().startswith("- obj")]

if "RESULT" not in dir():
    RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
