# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Clean spills (dirt, vomit, flour...) in view with a rag/mop (Janitor lite).

Picks up the named tool from the floor, holds it in the ACTIVE hand, walks to
each spill tile and clicks the TURF (x, y, turf=True) - spilling objects like
dirt pass clicks through, and the clean itself is SILENT (no chat echo), so
success is verified by the spill object vanishing from view. Tool found BY
NAME - never hard-code ids. Re-run after new messes.

Run: run_script {script: ".../service/clean_bar.py",
                 args: {"tool": "rag", "radius": 6, "max_tiles": 10}}
Returns {ok, cleaned, misses, tool, now, rev}.
"""
import re, time
opts = args or {}
tool_name = opts.get("tool") or "rag"
radius = int(opts.get("radius") or 6)
max_tiles = int(opts.get("max_tiles") or 10)
SPILL = r"\b(dirt|vomit|flour|blood|space lube|toilet water)\b"
out = {"ok": True, "cleaned": [], "misses": []}


def _hand_item():
    inv = (sk.inventory().text or "")
    act = [l for l in inv.split("\n") if "active_hand" in l]
    if act and "empty" in act[0]:
        return None
    m = re.search(r'obj (\d+) "([^"]+)"', act[0]) if act else None
    return m.group(2) if m else "unknown"


# ---- pick up the tool (by name; already in hand > in view > fetch) ----
s = sk.search(query=tool_name, in_view=True).text or ""
m = re.search(r'- obj (\d+) "([^"]*' + re.escape(tool_name) + r'[^"]*)"', s)
held = _hand_item()
if held and re.search(re.escape(tool_name[:4]), held, re.I):
    pass                                  # already holding it
else:
    if not m:                       # not in view: is it known out of view?
        s = sk.search(query=tool_name).text or ""
        m = re.search(r'- obj (\d+) "([^"]*' + re.escape(tool_name) + r'[^"]*)"', s)
        if m:
            p = re.search(r'at (\d+),(\d+)', s)
            if p:
                bot.goto(x=int(p.group(1)) - 1, y=int(p.group(2))); time.sleep(0.4)
            s = sk.search(query=tool_name, in_view=True).text or ""
            m = re.search(r'- obj (\d+) "([^"]*' + re.escape(tool_name) + r'[^"]*)"', s)
    if not m:
        raise RuntimeError("tool not found (in view or known): " + tool_name)
    tid, tname = int(m.group(1)), m.group(2)
    if _hand_item() is not None:
        sk.key(key="X"); time.sleep(0.6)     # free the active hand
    sk.click(object_id=tid, expect_name=tname[:40]); time.sleep(0.8)
    if tool_name[:3] not in (_hand_item() or "").lower():
        raise RuntimeError("tool pickup failed: holding " + str(_hand_item()))
out["tool"] = (held or (tname if m else "?"))[:40]

done = set()
for _ in range(max_tiles):
    s = sk.look(radius=radius, max_things=40).text or ""
    spills = []
    for l in s.split("\n"):
        if "- obj" not in l or not re.search(SPILL, l, re.I):
            continue
        mi, mp = re.search(r'- obj (\d+)', l), re.search(r'at (\d+),(\d+)', l)
        if mi and mp:
            spills.append((int(mp.group(1)), int(mp.group(2)), int(mi.group(1))))
    spills = [(x, y, o) for (x, y, o) in spills if (x, y) not in done]
    if not spills:
        break
    x, y, oid = spills[0]
    w = bot.goto(x=x, y=y)
    if w.failed:
        done.add((x, y))
        out["misses"].append({"tile": [x, y], "why": "unreachable"})
        continue
    time.sleep(0.4)
    sk.click(x=x, y=y, turf=True); time.sleep(1.0)
    # silent clean: success = the spill object no longer in view
    gone = not re.search(r'- obj %d\b' % oid, (sk.search(query="dirt vomit flour blood", in_view=True).text or "") or "")
    if not gone:
        s2 = sk.search(query="vomit", in_view=True).text or ""
        gone = not re.search(r'- obj %d\b' % oid, s2)
    (out["cleaned"] if gone else out["misses"]).append(
        {"tile": [x, y]} if gone else {"tile": [x, y], "why": "spill still there"})
    done.add((x, y))
    if _hand_item() is None:            # tool got dropped/used up - re-grab
        m2 = re.search(r'- obj (\d+) "([^"]*' + re.escape(tool_name) + r'[^"]*)"', (sk.search(query=tool_name, in_view=True).text or ""))
        if m2:
            sk.click(object_id=int(m2.group(1)), expect_name=m2.group(2)[:40]); time.sleep(0.7)
    watch("clean_bar")

now = sk.status()
RESULT = dict(out, now=(now.get("you") or "")[:80], rev=now.rev)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
