# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Audit the BUILDABLE/PERSISTENT silicon things in view: cyborg
endoskeletons (part completeness), MMIs (brain alive?), finished cyborgs
(charge / module / laws), mechs (occupant, integrity, beacon/DNA lock).

Run: run_script {script: ".../job_scriptz/roboticist/shell_check.py",
                 args: {"ids"?: [obj ids], "kind"?: "endoskeleton"|"mmi"
                              |"cyborg"|"mech"|"cyborg reclassification board"}}
Read-only (examine only). Empty view is a VALID answer (a fresh lab has
none - print parts and build a shell; keep one finished shell on standby).

Fork truths:
  - A bare endoskeleton examine is SPARSE ("a cyborg endoskeleton" only);
    parts attached appear as overlays / extra examine lines - count them as
    completeness hints, verdict "unverifiable" when nothing is listed.
  - MMI: examine names the occupant's brainmob when one is inside; a
    braindead or absent brain must NOT go into a shell (job rule #1: check
    the MMI first - a live brain can speak).
  - Cyborgs are silicon MOBS (name usually "(Cyborg)" / "borg"); examine
    carries the cell/charge and module lines when present.
  - Mechs are dense vehicles; examine shows armor/integrity lines and -
    when fitted - tracking beacon / DNA lock entries (job checklist).
"""
import re

opts = args or {}
out = {"found": [], "verdict": []}
want_kinds = opts.get("kind") and [k.lower() for k in (opts["kind"] if
                       isinstance(opts["kind"], list) else [opts["kind"]])]
want_ids = set(int(i) for i in (opts.get("ids") or []))


def search_rows(q, limit=80):
    s = sk.search(query=q, in_view=True, page_size=limit).text or ""
    rows = []
    for line in s.split("\n"):
        m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+).*?state=([\w-]+)', line.strip())
        if m and "left the view" not in line and "last seen" not in line:
            rows.append({"id": int(m.group(1)), "name": m.group(2),
                         "x": int(m.group(3)), "y": int(m.group(4)),
                         "state": m.group(5)})
    return rows


seen = set()
JOBS = [
    ("endoskeleton", "endoskeleton", r"cyborg endoskeleton", None),
    ("mmi", "interface", r"MMI|Man-Machine Interface", None),
    ("mmi", "positron", r"positronic brain", None),
    ("cyborg reclassification board", "reclassification board",
     r"reclassification board", None),
    ("mech", "mech",
     r"(Ripley|Odysseus|Gygax|Durand|Phazon).*(?!board|module|console|control)",
     r"board|module|console|control"),
]
for kind, query, include, exclude in JOBS:
    if want_kinds and kind not in want_kinds:
        continue
    for r in search_rows(query):
        if r["id"] in seen or (want_ids and r["id"] not in want_ids):
            continue
        if not re.search(include, r["name"], re.I):
            continue
        if exclude and re.search(exclude, r["name"], re.I):
            continue
        seen.add(r["id"])
        e = sk.examine(object_id=r["id"]).text or ""
        row = {"kind": kind, "id": r["id"], "name": r["name"],
               "x": r["x"], "y": r["y"], "state": r["state"],
               "examine_lines": []}
        for line in e.split("\n"):
            t = line.strip().lstrip("- ").strip()
            if not t or t.startswith("That's") or t.startswith("rev "):
                continue
            if re.match(r"^(lines:|opened_windows:|  )", line.strip()):
                continue
            if len(row["examine_lines"]) < 8:
                row["examine_lines"].append(t[:130])
        if kind == "mmi":
            # organic.dm: icon_state mmi_off (empty) / mmi_alive / mmi_dead
            row["brain"] = {"mmi_alive": "present-alive",
                            "mmi_dead": "present-DEAD",
                            "mmi_off": "empty"}.get(r["state"], "unclear")
        if kind == "mech":
            row["beacon"] = "beacon" in e.lower()
            row["dna_lock"] = re.search(r"DNA lock|dna lock", e) is not None
        out["found"].append(row)

# cyborgs (silicon mobs)
s = sk.search(query="", kind="mob", in_view=True, page_size=80).text or ""
for line in s.split("\n"):
    t = line.strip()
    if not t.startswith("- mob"):
        continue
    if not re.search(r"cyborg|borg|silicon|android", t, re.I):
        continue
    m = re.match(r"- mob (\d+) \"([^\"]*)\"", t)
    if not m or (want_ids and int(m.group(1)) not in want_ids):
        continue
    e = sk.examine(object_id=int(m.group(1))).text or ""
    row = {"kind": "cyborg", "id": int(m.group(1)), "name": m.group(2),
           "examine_lines": [l.strip()[:130] for l in e.split("\n")
                             if l.strip().startswith("- ")][1:7]}
    cm = re.search(r"(\d+(?:\.\d+)?)\s*%", e)
    row["charge_pct"] = cm and float(cm.group(1))
    out["found"].append(row)

# verdicts
for row in out["found"]:
    if row["kind"] == "mmi" and row.get("brain") != "present-alive":
        out["verdict"].append("MMI %s: brain %s - only an ALIVE brain (mmi_alive)"
                              " may go into a shell; empty/braindead MMIs are "
                              "useless (check before shelling)"
                              % (row["id"], row.get("brain")))
    if row["kind"] == "mech" and not (row.get("beacon") or row.get("dna_lock")):
        out["verdict"].append("mech %s (%s): no beacon/DNA lock seen in the "
                              "examine - fit both (job checklist)" % (row["id"], row["name"]))
    if row["kind"] == "cyborg" and row.get("charge_pct") is not None \
            and row["charge_pct"] < 20:
        out["verdict"].append("cyborg %s: charge %s%% - send it to a recharging "
                              "station" % (row["id"], row["charge_pct"]))
if not out["found"]:
    out["verdict"].append("no shells/MMIs/cyborgs/mechs in view (valid for a "
                          "fresh lab - build a shell and keep it on standby)")
RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
