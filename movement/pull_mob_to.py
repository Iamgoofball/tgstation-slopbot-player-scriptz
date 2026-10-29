"""Grab a mob (Ctrl+click = pull in this fork), haul it to a destination, and
optionally place it onto an object (operating table / stasis unit = buckle).

Run: run_script {script: ".../movement/pull_mob_to.py",
                 args: {"mob": 2892, "to_x": 79, "to_y": 105}}
   or args: {"mob": 2892, "onto_id": 15574, "onto_kind": "obj", "onto_name": "lifeform stasis unit"}
Destination search needs `onto_name` to find the object's tile. Verifies grab,
that the body followed, and (when placing) the final tile.
"""
import re
opts = args or {}
mob = opts.get("mob")
name = opts.get("mob_name", "")
onto_id, onto_kind = opts.get("onto_id"), opts.get("onto_kind")
to_x, to_y = opts.get("to_x"), opts.get("to_y")
if mob is None or (to_x is None and onto_id is None):
    raise ValueError("args: {'mob': id, 'to_x': x, 'to_y': y} or {'mob': id, 'onto_id': id, 'onto_kind': 'obj', 'onto_name': 'name'}")

def mob_line():
    s = sk.search(query=name, kind="mob", in_view=True).text or ""
    for l in s.split("\n"):
        if f"mob {mob} " in l:
            return l
    return None

out = {"mob": mob}
line = mob_line()
if not line:
    out["detail"] = "mob not in view - walk into range first, then rerun"
else:
    bot.goto(object_id=mob, expect_name=name or None, adjacent=True)
    c = sk.click(object_id=mob, expect_name=name or None, ctrl=True)
    out["grabbed"] = bool(re.search(r"grab \w+ passively|You grab", c.text or ""))
    if not out["grabbed"]:
        out["grabbed"] = "pull0" not in (sk.screen(page_size=40).text or "")
    if onto_id is not None:
        oname = opts.get("onto_name")
        if not oname:
            raise ValueError("give onto_name when using onto_id")
        m = re.search(rf"{onto_kind} {onto_id} \"[^\"]*\" at (\d+),(\d+)",
                      sk.search(query=oname, all_things=True).text or "")
        if not m:
            out["detail"] = "destination object not found by search"
        else:
            bot.goto(x=int(m.group(1)), y=int(m.group(2)))
            time.sleep(0.5)
            line2 = mob_line()
            out["followed"] = bool(line2)
            if line2:
                d = sk.drag(object_id=mob, onto_id=onto_id, onto_kind=onto_kind)
                out["placed_msg"] = "buckling" in (d.text or "")
                time.sleep(0.8)
                fin = mob_line() or ""
                fm = re.search(r"at (\d+),(\d+)", fin)
                out["placed"] = out["placed_msg"] or (fm and (int(fm.group(1)), int(fm.group(2))) == (int(m.group(1)), int(m.group(2))))
    else:
        bot.goto(x=to_x, y=to_y)
        time.sleep(0.5)
        out["followed"] = bool(mob_line())
    out["ok"] = bool(out.get("grabbed")) and (onto_id is None or bool(out.get("placed")))
out
