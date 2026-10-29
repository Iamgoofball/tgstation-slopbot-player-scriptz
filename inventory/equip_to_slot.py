"""Equip a held item to a HUD slot (click the slot button with it in the active
hand) — or remove a worn item by dragging it onto a turf (careful: bags DUMP
their contents instead of coming off; true removal needs a StripMenu via
drag-mob-onto-adjacent-mob).

Run: run_script {script: ".../inventory/equip_to_slot.py",
                 args: {"mode": "equip", "item_id": 17763, "hud_slot_id": 193368}}
   or args: {"mode": "remove_to_turf", "item_id": 186031, "to_x": 84, "to_y": 94}
"""
import re
opts = args or {}
mode = opts.get("mode", "equip")
iid = opts.get("item_id")
if iid is None:
    raise ValueError("args: {'mode': 'equip'|'remove_to_turf', 'item_id': id, ...}")
if mode == "equip":
    slot = opts.get("hud_slot_id")
    if slot is None:
        raise ValueError("equip needs hud_slot_id (the HUD button obj id)")
    c = sk.click(object_id=slot, expect_name=None)
    t = (c.text or "")
    ok = "too big" not in t and "cannot" not in t.lower()
    inv = (sk.inventory().text or "")
    worn = [l.strip()[:90] for l in inv.split("\n") if str(iid) in l]
    {"ok": ok and any("slot" in l for l in worn), "note": t[-120:], "worn": worn[:1]}
else:
    x, y = opts.get("to_x"), opts.get("to_y")
    if x is None:
        raise ValueError("remove_to_turf needs to_x/to_y")
    d = sk.drag(object_id=iid, onto_x=x, onto_y=y)
    {"ok": True, "answer": (d.text or "")[:160],
     "warn": "bags dump contents to the turf instead of coming off"}
