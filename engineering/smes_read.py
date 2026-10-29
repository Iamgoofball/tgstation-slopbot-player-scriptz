# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Read a SMES ("power storage unit") tgui: charge %, input/output state,
available/used. Read-ONLY (writing lives in smes_set.py). Walks to the unit
first — readers must move, callers don't have to be adjacent.

Run: run_script {script: ".../engineering/smes_read.py", args: {"id": <obj id>}}
Empty active hand required to open. Returns {charge, inputting, outputting,
input_available, output_used, ok}. bot.goto flags "already there" as failed —
treated as success.
"""
import re

opts = args or {}
oid = opts.get("id")
if not oid:
    raise ValueError("args: {'id': obj_id}")
out = {"id": oid}

g = bot.goto(object_id=int(oid))
if g.failed and "already there" not in (g.text or ""):
    out["ok"] = False
    out["note"] = "walk to SMES failed: " + (g.text or "")[-100:]
    RESULT = out
else:
    # close stale windows (the stale-APC-as-SMES trap)
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        try:
            b = sk.tgui_window(id=m.group(1)).text or ""
            i = re.search(r"interface: (\S+)", b)
            if i and i.group(1) != "Smes":
                sk.tgui_send(id=m.group(1), type="close")
                time.sleep(0.2)
        except Exception:
            pass
    sk.click(object_id=int(oid))
    time.sleep(1.2)
    wins = sk.tgui_windows().text or ""
    mm = None
    for m in re.finditer(r"(tgui-window-\d+):", wins):
        b = sk.tgui_window(id=m.group(1)).text or ""
        i = re.search(r"interface: (\S+)", b)
        if i and i.group(1) == "Smes":
            mm = m.group(1)
            break
    out["win"] = mm
    if mm:
        d = sk.tgui_window(id=mm, max_chars=6000).text or ""

        def num(p):
            x = re.search(p, d)
            try:
                return float(x.group(1)) if x else None
            except ValueError:
                return None

        out["charge"] = num(r'"charge":\s*([0-9.]+)')
        cap = num(r'"capacity":\s*([0-9.eE+]+)')  # only static_data has it
        if cap and out["charge"] is not None:
            out["charge_pct"] = round(100.0 * out["charge"] / cap, 1)
        out["inputting"] = bool(re.search(r'"inputAttempt":\s*1', d))
        out["outputting"] = bool(re.search(r'"outputAttempt":\s*1', d))
        out["input_available"] = num(r'"inputAvailable":\s*([0-9.eE+]+)')
        out["output_used"] = num(r'"outputUsed":\s*([0-9.eE+]+)')
        sk.tgui_send(id=mm, type="close")
        out["ok"] = out["charge"] is not None
    else:
        out["ok"] = False
        out["note"] = "no Smes window opened (empty hand needed; right machine?)"
    RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
