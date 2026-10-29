# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Read the nearest APC's tgui and report its power state (generic power check).

Run: run_script {script: ".../generic_scriptz/apc_read.py"}
Searches machinery in view for an APC (wall terminal), walks adjacent, opens
its tgui, parses the JSON state: cell %, external power, charging, load.
Verdict: fine (external on) / low (cell<40) / dying (no external power).
No APC in view -> ok:false (walk into any powered room first).
Gotchas: bot.goto/bot.open_machine need object_id as an INT; tgui ids are
strings. Parse the embedded JSON ("powerCellStatus": 100), never the rendered
text — rendered text reorders and paraphrases.
"""
import re

def active_hand_line():
    """The inventory line carrying the handactive marker (or None)."""
    for l in (sk.inventory().text or "").split("\n"):
        if "handactive" in l:
            return l
    return None

def empty_active_hand():
    """Free the active hand for world clicks: swap to the other hand if it is
    empty, else drop (key Q). Follows the bar of vendor_list.py."""
    inv = (sk.inventory().text or "")
    hands = [l for l in inv.split("\n") if re.search(r"\bhand\b", l) and "slot" in l]
    if active_hand_line() is None:
        return  # already empty
    # count held items in the two hand lines
    held = [l for l in hands if re.search(r"obj \d+", l)]
    if len(held) >= 2:
        sk.key(key="Q"); time.sleep(0.4)      # drop active
    else:
        sk.key(key="X"); time.sleep(0.4)      # swap to the empty hand
    if active_hand_line() is not None:
        sk.key(key="Q"); time.sleep(0.4)      # belt-and-braces

def run():
    s = sk.search(query="APC", in_view=True)
    t = (s.text or "")
    ids = re.findall(r"- (?:obj|mob) (\d+) \"([^\"]*APC[^\"]*)\"", t)
    out = {"apcs_in_view": [[i[0], i[1]] for i in ids[:6]]}
    if not ids:
        return dict(out, ok=False, note="no APC in view — walk into any powered room first")
    aid = int(ids[0][0])
    empty_active_hand()
    a = bot.goto(object_id=aid, expect_name=ids[0][1])
    if a.failed:
        return dict(out, ok=False, note="walk to APC failed: " + (a.text or "")[-120:])
    m = bot.open_machine(aid, expect_name=ids[0][1])
    wid = getattr(m, "window_id", None)
    if not wid:
        return dict(out, ok=False, note="APC tgui did not open: " + (m.text or "")[-120:])
    time.sleep(0.3)
    w = sk.tgui_window(id=wid, max_chars=8000)
    dat = (w.text or "")
    # parse the tgui JSON state block, not the rendered text (rendered text
    # reorders and paraphrases; the JSON keys are stable)
    def jnum(key):
        m = re.search(r'"%s":\s*(-?[\d.]+)' % key, dat)
        return float(m.group(1)) if m else None
    cell = jnum("powerCellStatus")
    ext = jnum("externalPower")
    load = re.search(r'"totalLoad":\s*"([^"]+)"', dat)
    chg = jnum("chargingStatus")
    sk.tgui_send(id=wid, type="close")
    out.update({"cell_pct": None if cell is None else int(cell),
                "external_power": ext, "charging": chg,
                "total_load": load.group(1) if load else None,
                "raw_head": dat[:160]})
    c = out["cell_pct"]
    ext_ok = ext is not None and ext >= 2
    out["ok"] = True
    out["verdict"] = ("fine" if (ext_ok and (c is None or c >= 40)) else
                      "low" if (ext_ok and c is not None and c < 40) else
                      "dying")
    return out

RESULT = run()

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
