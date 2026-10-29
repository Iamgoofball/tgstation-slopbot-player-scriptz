# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Drive the emergency roller bed (folded item <-> deployed structure).

Run: run_script {script: ".../job_scriptz/paramedic/roller_bed_use.py",
                 args: {"mode": "status"|"deploy"|"buckle"|"unbuckle"|"pull"
                              |"unpull"|"fold"|"brakes",
                        "bed"?: id (item OR structure), "patient"?: mob id,
                        "x"?, "y"?}}
Default mode "status". bed id optional â€” finds the folded item (belt overlay
`state=emerg_folded` / active hand) or the deployed structure
("emergency medical bed") in view. x/y: walk there first (deploy happens at
YOUR feet â€” bed.dm: attack_self -> deploy_bed(user, user.loc)).

Interactions (all code-verified, bed.dm):
  deploy â€” click the folded item IN HAND (attack_self): structure
    "emergency medical bed" (icon emerg_down) appears on your tile; the item
    is consumed -> the structure has a NEW id (reported).
  buckle â€” drag the patient onto the deployed bed (mouse_drop; bed dense when
    occupied, icon emerg_up).
  unbuckle â€” EMPTY-HAND LMB on the bed (context: LMB "Unbuckle"; an item in
    hand would do something else) -> icon emerg_down.
  pull â€” ctrl+click the bed, verified via the "stop pulling" HUD icon.
  fold â€” RIGHT-click the bed (RMB "Fold up"; refused while a mob is buckled),
    gives a NEW "roller bed" item id on your tile.
  brakes â€” ALT-click toggles anchored ("brakes applied/released", verified
    via examine; a buckled patient can't alt-click themselves off).
  status â€” icon_state (emerg_down / emerg_up / emerg_folded) + brakes +
    buckled mob, read from the TILE (remembered contents, dark tiles too).
"""
import re

opts = args or {}
mode = (opts.get("mode") or "status").lower()
out = {"mode": mode, "verdict": []}


def close_all():
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        sk.tgui_send(id=m.group(1), type="close")
        time.sleep(0.12)


def empty_active_hand():
    for _ in range(2):
        inv = sk.inventory().text or ""
        act = [l for l in inv.split("\n") if "active_hand" in l]
        if act and ("empty" in act[0] or "obj" not in act[0]):
            return True
        sk.key(key="X")
        time.sleep(0.4)
    return False


def search_obj(name_query, oid=None):
    """-> (id, x, y) of the first in-view obj matching; oid filters exact id."""
    s = sk.search(query=name_query, in_view=True, page_size=30)
    for line in (s.text or "").split("\n"):
        m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+)', line)
        if not m:
            continue
        if oid is not None and int(m.group(1)) != int(oid):
            continue
        if name_query.lower() in line.lower():
            return int(m.group(1)), int(m.group(3)), int(m.group(4))
    return None, None, None


def tile_state(oid, x, y):
    """icon_state from the tile's remembered contents (live, dark tiles ok)."""
    if x is None:
        return None
    t = sk.tile(int(x), int(y), all=True)
    m = re.search(r'- obj %d "[^"]*" \[([\w-]+)\]' % int(oid), t.text or "")
    return m.group(1) if m else None


def pull_hud_active():
    sc = sk.screen(page_size=250).text or ""
    for line in sc.split("\n"):
        if "stop pulling" in line and "- obj" in line:
            m = re.search(r'state=(pull[\w-]*)', line)
            return bool(m and m.group(1) not in ("pull0",))
    return False


def you_xy():
    m = re.search(r'at (\d+),(\d+),(\d+)', sk.status().get("you", "") or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (None, None, None)


# ---- locate the bed (item or structure)
bed_id = opts.get("bed") and int(opts["bed"])
item_id = struct_id = None
if bed_id:
    # is it in view as structure, item on screen, or in hand?
    struct_id, sx, sy = search_obj("emergency medical bed", bed_id)
    if not struct_id:
        item_id = bed_id
else:
    struct_id, sx, sy = search_obj("emergency medical bed")
    if not struct_id:
        inv = sk.inventory().text or ""
        m = re.search(r'active_hand[^\n]*obj (\d+) "roller bed"', inv)
        if m:
            item_id = int(m.group(1))
        else:
            sc = sk.screen(page_size=250).text or ""
            m = re.search(r'- obj (\d+) "roller bed" .*state=emerg_folded', sc)
            if not m:
                mm = re.search(r'- obj (\d+) "belt" at CENTER', sc)
                if mm:
                    sk.click(object_id=int(mm.group(1)))  # open belt view
                    time.sleep(0.6)
                    sc = sk.screen(page_size=250).text or ""
            m = re.search(r'- obj (\d+) "roller bed" .*state=emerg_folded', sc)
            if m:
                item_id = int(m.group(1))
out["bed"] = {"item": item_id, "structure": struct_id}
if not item_id and not struct_id:
    RESULT = {"ok": False, "note": "no roller bed (belt? deployed nearby?)"}
else:
    if opts.get("x") and opts.get("y"):
        g = bot.goto(x=int(opts["x"]), y=int(opts["y"]), max_steps=250)
        if g.failed and "already there" not in (g.text or ""):
            out["verdict"].append("walk to %s,%s failed" % (opts["x"], opts["y"]))

    # ---- modes
    if mode == "status":
        if struct_id:
            out["structure_state"] = tile_state(struct_id, sx, sy)
            e = sk.examine(object_id=struct_id)
            ex = e.text or ""
            out["brakes"] = "brakes are applied" in ex
            out["foldable"] = "fold it up with a Right-click" in ex
            if item_id or True:
                pass
        if item_id:
            out["item_state"] = "emerg_folded"

    elif mode == "deploy":
        if struct_id:
            out["verdict"].append("a bed is already deployed nearby (%s at %s,%s)"
                                  % (struct_id, sx, sy))
            out["ok"] = True
        elif not item_id:
            RESULT = {"ok": False, "note": "no folded roller bed to deploy"}
        else:
            # ensure it is in the hand
            inv = sk.inventory().text or ""
            if not re.search(r'active_hand[^\n]*obj %d\b' % item_id, inv):
                sk.click(object_id=item_id)  # belt overlay click -> hand
                time.sleep(0.7)
                inv = sk.inventory().text or ""
                if not re.search(r'active_hand[^\n]*obj %d\b' % item_id, inv):
                    RESULT = {"ok": False, "note": "roller bed did not reach the active hand"}
                    RESULT.setdefault("mode", mode)
            if "RESULT" not in dir():
                mx, my, mz = you_xy()
                sk.click(object_id=item_id)  # in-hand = attack_self = deploy
                time.sleep(1.6)
                nid, nx, ny = search_obj("emergency medical bed")
                out["deployed"] = {"id": nid, "tile": [nx, ny]}
                if not nid:
                    out["ok"] = False
                    out["verdict"].append("no structure appeared at %s,%s" % (mx, my))
                else:
                    out["ok"] = True

    elif mode == "buckle":
        pid = opts.get("patient") and int(opts["patient"])
        if not pid:
            RESULT = {"ok": False, "note": "mode buckle needs args.patient = <mob id>"}
        elif not struct_id:
            RESULT = {"ok": False, "note": "no deployed bed â€” deploy first"}
        else:
            g = bot.goto(object_id=pid, max_steps=120)
            if g.failed and "already there" not in (g.text or ""):
                out["ok"] = False
                out["verdict"].append("cannot reach the patient to drag them")
            else:
                empty_active_hand()
                d = sk.drag(object_id=pid, onto_id=struct_id)
                out["drag"] = (d.text or "")[:160]
                time.sleep(1.6)
                sx, sy = (search_obj("emergency medical bed", struct_id))[1:]
                st = tile_state(struct_id, sx, sy)
                out["after"] = st
                out["ok"] = st == "emerg_up"
                if not out["ok"]:
                    out["verdict"].append("bed did not take the patient "
                                          "(same-tile drag may hug â€” step off and re-drag)")

    elif mode == "unbuckle":
        if not struct_id:
            RESULT = {"ok": False, "note": "no deployed bed in view"}
        else:
            empty_active_hand()  # LMB unbuckle needs an EMPTY hand
            g = bot.goto(object_id=struct_id, max_steps=60)
            sk.click(object_id=struct_id)
            time.sleep(1.5)
            st = tile_state(struct_id, sx, sy)
            out["after"] = st
            out["ok"] = st == "emerg_down"
            if not out["ok"]:
                out["verdict"].append("bed still occupied (icon %s)" % st)

    elif mode == "pull":
        if not struct_id:
            RESULT = {"ok": False, "note": "no deployed bed in view"}
        else:
            empty_active_hand()
            sk.click(object_id=struct_id, ctrl=True)
            time.sleep(1.2)
            out["pull_hud"] = pull_hud_active()
            out["ok"] = bool(out["pull_hud"])
            if not out["ok"]:
                out["verdict"].append("pull HUD not active â€” ctrl-click the bed again")

    elif mode == "unpull":
        hud = None
        sc = sk.screen(page_size=250).text or ""
        for line in sc.split("\n"):
            if "stop pulling" in line and "- obj" in line:
                m = re.search(r'- obj (\d+)', line)
                if m:
                    hud = int(m.group(1))
        if hud:
            sk.click(object_id=hud)
            time.sleep(0.8)
        out["pull_hud"] = pull_hud_active()
        out["ok"] = not out["pull_hud"]

    elif mode == "fold":
        if not struct_id:
            RESULT = {"ok": False, "note": "no deployed bed in view"}
        else:
            st = tile_state(struct_id, sx, sy)
            if st == "emerg_up":
                RESULT = {"ok": False, "note": "patient buckled â€” unbuckle before folding"}
            else:
                empty_active_hand()
                sk.click(object_id=struct_id, right=True)
                time.sleep(1.6)
                st2 = tile_state(struct_id, sx, sy)
                out["after"] = st2
                if st2 in (None, "emerg_folded"):
                    nid, nx, ny = search_obj("roller bed")
                    inv = sk.inventory().text or ""
                    hand = re.search(r'active_hand[^\n]*obj (\d+) "roller bed"', inv)
                    out["folded"] = {"id": (hand and int(hand.group(1))) or nid,
                                     "tile": [nx, ny] if nid else None}
                    out["ok"] = True
                else:
                    out["ok"] = False
                    out["verdict"].append("bed still deployed (%s) â€” RMB fold refused" % st2)

    elif mode == "brakes":
        if not struct_id:
            RESULT = {"ok": False, "note": "no deployed bed in view"}
        else:
            e = sk.examine(object_id=struct_id)
            before = "brakes are applied" in (e.text or "")
            g = bot.goto(object_id=struct_id, max_steps=60)
            try:
                sk.click(object_id=struct_id, alt=True)
                applied = None
            except Exception as ex:
                out["verdict"].append("alt-click unsupported: %s" % ex)
                applied = "error"
            time.sleep(1.2)
            e2 = sk.examine(object_id=struct_id)
            after = "brakes are applied" in (e2.text or "")
            out["brakes"] = {"before": before, "after": after}
            out["ok"] = applied != "error" and before != after
            if not out["ok"] and applied != "error":
                out["verdict"].append("brake state did not change (buckled mobs block it?)")
    else:
        RESULT = {"ok": False,
                  "note": "unknown mode %r (status/deploy/buckle/unbuckle/pull/unpull/fold/brakes)" % mode}

if "RESULT" not in dir():
    RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
