# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""READ-ONLY survey of every morgue unit in view (morgue.dm): open/closed
state, occupant auto-label, beeper. No clicks - safe to run anywhere.

Run: run_script {script: ".../job_scriptz/coroner/morgue_check.py",
                 args: {"ids"?: [unit obj ids], "trays"?: true, "bags"?: true}}
Auto-discovers units (icon_state morgue0-4; "secure morgue" units included).
args.ids: only report those units. args.trays: also list any "morgue tray"
open-tray objects; args.bags: also list body bags in view.

Fork truths (morgue.dm update_icon_state):
  morgue0 = tray out (OPEN) | morgue1 = closed EMPTY | morgue2 = closed
  occupied (dead) | morgue3 = occupied non-carbon | morgue4 = occupied
  REVIVABLE (a defib could work - do not autopsy these).
  The occupant is in the unit's NAME ("morgue - (Name - Species)"): the tray
  scan recurses into labeled body bags. Beeper: examine line
  "The speaker is enabled/disabled. Alt-click to toggle it." (click_alt).
"""
import re

opts = args or {}
out = {"morgues": [], "trays": [], "bags": [], "verdict": []}


def parse_search(text):
    """-> list of dicts {id, name, x, y, state} from '- obj ...' lines."""
    rows = []
    for line in (text or "").split("\n"):
        m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+).*?state=([\w-]+)', line.strip())
        if not m:
            m2 = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+)', line.strip())
            if not m2:
                continue
            rows.append({"id": int(m2.group(1)), "name": m2.group(2),
                         "x": int(m2.group(3)), "y": int(m2.group(4)), "state": None})
            continue
        rows.append({"id": int(m.group(1)), "name": m.group(2),
                     "x": int(m.group(3)), "y": int(m.group(4)), "state": m.group(5)})
    return rows


# ---- discover units in view
rows = parse_search(sk.search(query="morgue", in_view=True, page_size=250).text)
want_ids = set(int(i) for i in (opts.get("ids") or []))
STATE_RE = re.compile(r"^morgue[0-4]$")
for r in rows:
    if want_ids and r["id"] not in want_ids:
        continue
    is_unit = bool(STATE_RE.match(r["state"] or "")) or ("secure morgue" in r["name"].lower())
    if not is_unit:
        continue   # skips the Morgue airlock (state=closed), alarms, APCs, scrubbers
    u = {"id": r["id"], "name": r["name"], "x": r["x"], "y": r["y"], "state": r["state"]}
    # occupant from the auto-label: "morgue - (Judah Osterweis - Human)"
    m = re.search(r"\(([^()]+) - ([^()]+)\)\s*$", r["name"])
    u["occupant"] = ("%s (%s)" % (m.group(1), m.group(2))) if m else None
    # beeper from examine (read-only, free)
    try:
        e = sk.examine(object_id=r["id"]).text or ""
        bm = re.search(r"The speaker is (enabled|disabled)", e)
        u["beeper"] = bm.group(1) if bm else None
        if "adorning" in e:
            u["note"] = "has surgical prep (surgery_prepped) on it"
    except Exception as ex:
        u["beeper"] = "error: %s" % str(ex)[:60]
    MEANING = {"morgue0": "OPEN (tray out)", "morgue1": "closed EMPTY",
               "morgue2": "closed OCCUPIED (dead)", "morgue3": "occupied NON-CARBON",
               "morgue4": "occupied REVIVABLE - defib first, no autopsy"}
    u["meaning"] = MEANING.get(r["state"] or "", "secure morgue (beeper starts OFF)")
    out["morgues"].append(u)

if opts.get("trays"):
    for r in parse_search(sk.search(query="morgue tray", in_view=True, page_size=100).text):
        if r["state"] == "morguet":
            out["trays"].append({"id": r["id"], "x": r["x"], "y": r["y"]})
if opts.get("bags"):
    for r in parse_search(sk.search(query="body bag", in_view=True, page_size=100).text):
        if "body bag" in r["name"].lower():
            out["bags"].append({"id": r["id"], "name": r["name"],
                                "x": r["x"], "y": r["y"], "state": r["state"]})

out["count"] = len(out["morgues"])
if not out["morgues"]:
    out["verdict"].append("no morgue units in view - stand in/at the Morgue first "
                          "(walk_to(area='Morgue'))")
RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
