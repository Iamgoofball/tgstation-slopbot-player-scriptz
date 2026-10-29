# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""The CMO's cryo check (bare-minimum task #2): every cryo cell in view —
power, temperature, occupant, beaker — plus verdicts; `start: true` switches
the cells ON.

Run: run_script {script: ".../job_scriptz/chief-medical-officer/cryo_check.py",
                 args: {"cells"?: [ids], "start"?: true, "x"?, "y"?}}
Without ids it surveys "cryo cell" in view (Medbay's Cryogenics room: 2 cells
at 82,111 / 80,111 this round). Empty ACTIVE hand needed (a hand item click
"uses" the item on the pod — the CMO spawns with a surgical medkit; swap X).
Cryo window (interface Cryo): data {isOperating, isOpen, autoEject, occupant,
cellTemperature, beaker}, actions power/door/eject/insert/autoeject. The
power button is DISABLED while the pod door is open — send `door` first
(verified: door 1->0, then power 0->1 via data_changes). Acts are parsed from
their ANSWERS and go to the window id whose title/interface was verified —
NOT hard-coded tgui-window-1 (a zombie window can hold that id with
identical-looking values and silently rejects acts). An UNPOWERED room opens
no window — that is itself the verdict (check the room's APC:
engineering/apc_channel.py). AAS "Insufficient cryogenic" = connector gas
empty (temp near 2.7 K): cryo runs but heals nothing until gas + beaker.
"""
import re

opts = args or {}
start = bool(opts.get("start"))
out = {"cells": [], "verdict": []}

def close_all():
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        sk.tgui_send(id=m.group(1), type="close")
        time.sleep(0.12)

def empty_active_hand():
    for _ in range(2):
        inv = sk.inventory().text or ""
        act = [l for l in inv.split("\n") if "active_hand" in l]
        if act and ("empty" in act[0] or "obj" not in act[0]):
            return
        sk.key(key="X")
        time.sleep(0.4)

def find_cryo_win():
    w = sk.tgui_windows().text or ""
    for m in re.finditer(r"(tgui-window-\d+):", w):
        try:
            d = sk.tgui_window(id=m.group(1), max_chars=800).text or ""
        except Exception:
            continue
        if "closed: true" in d:
            continue
        i = re.search(r"interface: (\S+)", d)
        if i and i.group(1) == "Cryo":
            return m.group(1)
    return None

# 1) find cells
ids = [int(i) for i in (opts.get("cells") or [])]
if not ids:
    s = sk.search(query="cryo cell", in_view=True, page_size=20)
    ids = [int(m.group(1)) for m in
           re.finditer(r'- obj (\d+) "cryo cell"', s.text or "")]
if not ids:
    out["verdict"].append("no cryo cell in view — stand in Cryogenics")
    out["ok"] = False
    RESULT = out
else:
    empty_active_hand()
    for oid in ids:
        g = bot.goto(object_id=oid)
        if g.failed and "already there" not in (g.text or ""):
            out["cells"].append({"id": oid, "ok": False, "note": "unreachable"})
            continue
        close_all()
        time.sleep(0.4)
        sk.click(object_id=oid)
        time.sleep(1.8)
        wid = find_cryo_win()
        if not wid:
            out["cells"].append({"id": oid, "ok": False,
                                 "note": "no window (unpowered? empty hand?)"})
            continue
        d = sk.tgui_window(id=wid, max_chars=3000).text or ""
        row = {"id": oid}
        op = re.search(r'"isOperating": (\d)', d)
        opn = re.search(r'"isOpen": (\d)', d)
        tmp = re.search(r'"cellTemperature": ([\d.]+)', d)
        occ = re.search(r'"occupant": (null|\{)', d)
        bkr = re.search(r'"beaker": (null|\{)', d)
        row["on"] = int(op.group(1)) if op else None
        row["open"] = int(opn.group(1)) if opn else None
        row["temp_k"] = float(tmp.group(1)) if tmp else None
        row["has_occupant"] = bool(occ and occ.group(1) == "{")
        row["has_beaker"] = bool(bkr and bkr.group(1) == "{")
        if start and row["on"] == 0:
            # the power button is DISABLED while the pod door is open —
            # close it first (door), then power; parse the ACT ANSWERS
            # (data_changes), the immediate re-read races the server
            if row.get("open") == 1:
                ad = sk.tgui_act(id=wid, action="door")
                if re.search(r'"isOpen": 1 -> 0', ad.text or ""):
                    row["open"] = 0
                time.sleep(0.5)
            ap = sk.tgui_act(id=wid, action="power")
            row["power_act"] = (ap.text or "")[:200]
            # the answer truncates mid-word ("Insufficient cryogeni...")
            insufficient = "Insufficient cryogeni" in (ap.text or "")
            if re.search(r'"isOperating": 0 -> 1', ap.text or ""):
                row["on"] = 1
                out["verdict"].append("cryo %d switched ON" % oid)
            time.sleep(0.8)
            d2 = sk.tgui_window(id=wid, max_chars=1200).text or ""
            op2 = re.search(r'"isOperating": (\d)', d2)
            if op2:
                row["on"] = int(op2.group(1))
                msg = "cryo %d switched ON" % oid
                if row["on"] == 1 and msg not in out["verdict"]:
                    out["verdict"].append(msg)
            if row["on"] == 0 and insufficient:
                out["verdict"].append(
                    "cryo %d refuses to run: connector has no cryogenic gas "
                    "(machine self-shuts; fill it from the atmos loop first)"
                    % oid)
        sk.tgui_send(id=wid, type="close")
        out["cells"].append(row)

    # 2) verdicts
    for row in out["cells"]:
        if not row.get("ok", True) and "note" in row:
            out["verdict"].append("cryo %s: %s" % (row["id"], row["note"]))
            continue
        if row.get("on") == 0:
            out["verdict"].append("cryo %s OFF" % row["id"])
        if not row.get("has_beaker"):
            out["verdict"].append("cryo %s has no beaker — load cryoxadone "
                                  "from chemistry" % row["id"])
        t = row.get("temp_k")
        if t is not None and t > 150:
            out["verdict"].append("cryo %s WARM (%s K) — pipe gas gone"
                                  % (row["id"], t))
        if row.get("has_occupant"):
            out["verdict"].append("cryo %s OCCUPIED" % row["id"])
    n_on = sum(1 for r in out["cells"] if r.get("on") == 1)
    out["verdict"].append("%d/%d cryo cells on" % (n_on, len(out["cells"])))
    out["ok"] = any(r.get("ok", True) for r in out["cells"])
    RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
