# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Control ONE morgue unit (or a body bag on its tray): open/close the tray,
toggle the beeper, open/close a body bag, re-bag a corpse.

Run: run_script {script: ".../job_scriptz/coroner/morgue_tray_control.py",
                 args: {"mode": "status"|"open"|"close"|"beep_on"|"beep_off"
                              |"beep"|"open_bag"|"close_bag"|"bag_body",
                        "id": <morgue unit obj id>,   # unit modes
                        "bag": <body bag obj id>,     # *_bag / bag_body modes
                        "body": <mob id>}}            # bag_body mode
Default mode "status" (read-only).

Fork truths (morgue.dm + live):
  open/close - EMPTY-HAND LMB on the unit toggles the tray: open spawns a
    "morgue tray" (morguet, dense) on the tile NORTH of the unit; click again
    retracts it and everything on that tile (corpse, bag) rides back inside.
    Verified by icon_state (morgue0 = open) + tray object.
  beep - ALT-click toggles the speaker ("The speaker is enabled/disabled",
    read back via examine). beep_on/beep_off no-op if already in the state.
  bags - a labeled bag rides the tray; EMPTY-HAND LMB on the bag toggles it
    open (overlay bodybag_open on the tile line) / closed.
  bag_body - close the bag (click), then DRAG the corpse onto the closed bag
    (mouse_drop) - that is how a body goes into a bag; verify the body tile.
"""
import re

opts = args or {}
mode = (opts.get("mode") or "status").lower()
out = {"mode": mode, "verdict": []}


def empty_active_hand():
    """Free the active hand: X-swap first, then Q-drop if both hands are full.
    Returns the list of dropped obj ids."""
    dropped = []
    for attempt in range(3):
        inv = sk.inventory().text or ""
        act = [l for l in inv.split("\n") if "active_hand" in l]
        if act and ("empty" in act[0] or "obj" not in act[0]):
            if dropped:
                out["verdict"].append("dropped to free the active hand: %s" % dropped)
            return dropped
        if attempt == 0:
            sk.key(key="X")
            time.sleep(0.4)
        else:
            m = re.search(r'active_hand[^\n]*obj (\d+)', inv)
            if m:
                sk.key(key="Q")
                time.sleep(0.5)
                dropped.append(int(m.group(1)))
    out["verdict"].append("could not free the active hand (dropped %s)" % dropped)
    return dropped


def unit_line(oid):
    """live search line for the unit (id, name, x, y, state)."""
    s = sk.search(query="morgue", in_view=True, page_size=250).text or ""
    for line in s.split("\n"):
        m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+).*?state=([\w-]+)', line.strip())
        if m and int(m.group(1)) == int(oid):
            return {"id": int(m.group(1)), "name": m.group(2),
                    "x": int(m.group(3)), "y": int(m.group(4)), "state": m.group(5)}
    return None


def tray_near(ux, uy):
    """a 'morgue tray' object adjacent to the unit (spawned north on open)."""
    s = sk.search(query="morgue tray", in_view=True, page_size=100).text or ""
    for line in s.split("\n"):
        m = re.match(r'- obj (\d+) "morgue tray" at (\d+),(\d+)', line.strip())
        if m and abs(int(m.group(2)) - ux) <= 1 and abs(int(m.group(3)) - uy) <= 1:
            return {"id": int(m.group(1)), "x": int(m.group(2)), "y": int(m.group(3))}
    return None


def beeper_state(oid):
    e = sk.examine(object_id=oid).text or ""
    m = re.search(r"The speaker is (enabled|disabled)", e)
    return m.group(1) if m else None


def bag_open(bid):
    """overlay bodybag_open on the bag's tile line."""
    s = sk.search(query="body bag", in_view=True, page_size=100).text or ""
    for line in s.split("\n"):
        m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+)', line.strip())
        if m and int(m.group(1)) == int(bid):
            t = sk.tile(int(m.group(3)), int(m.group(4)), all=True).text or ""
            for tl in t.split("\n"):
                if re.match(r'- obj %d ' % int(bid), tl.strip()):
                    return "bodybag_open" in tl
    return None


uid = opts.get("id") and int(opts["id"])
bag_id = opts.get("bag") and int(opts["bag"])
u = unit_line(uid) if uid else None
if uid and not u:
    # may have just changed state: one retry via known index
    s = sk.search(query=str(uid), page_size=30).text or ""
    m = re.search(r'- obj %d "([^"]*)" at (\d+),(\d+)' % uid, s)
    if m:
        u = {"id": uid, "name": m.group(1), "x": int(m.group(2)),
             "y": int(m.group(3)), "state": None}

if mode in ("open_bag", "close_bag", "bag_body"):
    if not bag_id:
        RESULT = {"ok": False, "note": "mode %s needs args.bag = <body bag obj id>" % mode}
    elif mode == "bag_body" and not (opts.get("body") and int(opts["body"])):
        RESULT = {"ok": False, "note": "mode bag_body also needs args.body = <mob id>"}
    else:
        body_id = opts.get("body") and int(opts["body"])
        s = sk.search(query="body bag", in_view=True, page_size=100).text or ""
        bxy = None
        for line in s.split("\n"):
            m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+)', line.strip())
            if m and int(m.group(1)) == int(bag_id):
                bxy = (int(m.group(3)), int(m.group(4)))
        if mode == "bag_body":
            # close the bag if it lies open (tile check - search lines do not
            # carry overlays): the close zips a body lying on it INSIDE
            opened = bag_open(bag_id)
            if opened and bxy:
                empty_active_hand()
                sk.click(object_id=bag_id)
                time.sleep(1.8)
            out["bag_open_before"] = opened
            out["bag_open_after"] = bag_open(bag_id)
            # verify on the TILE: a body zipped inside is not drawn there
            # (remembered 'last seen' lines excluded)
            fresh = None
            if bxy:
                t = sk.tile(bxy[0], bxy[1], all=True).text or ""
                for tl in t.split("\n"):
                    mm = re.match(r'- mob %d ' % body_id, tl.strip())
                    if mm and "last seen" not in tl and "not visible" not in tl:
                        fresh = True
            out["body_still_outside"] = bool(fresh)
            out["ok"] = opened is not None and not fresh
            if fresh:
                out["verdict"].append("body still on the bag tile after the close "
                                      "- retry or drag it onto the closed bag")
            if not opened:
                out["verdict"].append("bag not found in view - stand closer")
        else:
            empty_active_hand()
            sk.click(object_id=bag_id)
            time.sleep(1.6)
            opened = bag_open(bag_id)
            out["bag_open"] = opened
            out["ok"] = opened is (mode == "open_bag")
            if not out["ok"]:
                out["verdict"].append("bag state did not match the target (open=%s)" % opened)
elif uid is None:
    RESULT = {"ok": False, "note": "args.id = <morgue unit obj id> required "
                                   "(morgue_check.py lists them)"}
else:
    out["unit"] = u and dict(u, occupant=(re.search(r"\(([^()]+ - [^()]+)\)", u["name"])
                                          .group(1) if u and re.search(r"\(([^()]+ - [^()]+)\)", u["name"]) else None))
    if mode == "status":
        if u:
            out["beeper"] = beeper_state(uid)
            out["tray"] = tray_near(u["x"], u["y"])
            out["ok"] = True
        else:
            out["ok"] = False
            out["verdict"].append("unit %s not in view" % uid)
    elif mode in ("open", "close"):
        if not u:
            RESULT = {"ok": False, "note": "unit %s not in view" % uid}
        else:
            if mode == "open" and u["state"] == "morgue0":
                out["ok"] = True
                out["note"] = "already open (tray out)"
                out["tray"] = tray_near(u["x"], u["y"])
            elif mode == "close" and u["state"] != "morgue0":
                out["ok"] = True
                out["note"] = "already closed"
            else:
                empty_active_hand()
                g = bot.goto(x=u["x"], y=u["y"], max_steps=60)
                sk.click(object_id=uid)
                time.sleep(1.8)
                u2 = unit_line(uid)
                out["after_state"] = u2 and u2["state"]
                out["tray"] = u2 and tray_near(u2["x"], u2["y"])
                out["ok"] = (u2 and u2["state"] == "morgue0") if mode == "open" \
                    else (u2 and u2["state"] != "morgue0")
                if not out["ok"]:
                    out["verdict"].append("unit state now %s (wanted %s)"
                                          % (u2 and u2["state"],
                                             "morgue0" if mode == "open" else "not morgue0"))
    elif mode in ("beep", "beep_on", "beep_off"):
        before = beeper_state(uid)
        target = {"beep": None, "beep_on": "enabled", "beep_off": "disabled"}[mode]
        if before == target:
            out["ok"] = True
            out["beeper"] = {"before": before, "after": before}
            out["note"] = "already %s" % target
        else:
            if u:
                bot.goto(x=u["x"], y=u["y"], max_steps=60)
            try:
                sk.click(object_id=uid, alt=True)
            except Exception as ex:
                out["verdict"].append("alt-click unsupported: %s" % str(ex)[:60])
            time.sleep(1.2)
            after = beeper_state(uid)
            out["beeper"] = {"before": before, "after": after}
            out["ok"] = bool(before) and before != after if mode == "beep" else after == target
            if not out["ok"]:
                out["verdict"].append("beeper did not reach %r (now %r)" % (target, after))
    else:
        RESULT = {"ok": False, "note": "unknown mode %r" % mode}

if "RESULT" not in dir():
    RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
