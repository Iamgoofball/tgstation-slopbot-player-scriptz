# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""The paramedic's kit check, ONE envelope: what you actually carry.

Run: run_script {script: ".../job_scriptz/paramedic/paramedic_kit_check.py",
                 args: {}}
Read-only. Sources (all verified live on the spawn kit):
  Belt + backpack contents render as `on "storage"` screen icons when their
  view is open (belt: handheld crew monitor state=crew_monitor, roller bed
  state=emerg_folded, syringe, survival box). The HUD click TOGGLES the view,
  so the script reads storage lines before AND after each HUD click and
  unions them â€” state-independent, no toggling assumption.
  Worn slots -> inventory(all=True): `in slot "..."` lines, plus
    `not shown on screen` for ears/gloves (excludes human bodypart lines).
Verdicts: no crew monitor (can't triage), no roller bed (can't move
bleeders â€” never drag them), no PDA (Lifeline tracker), no gloves
(fingerprints), no ID (doors won't open). Restock from the EMT locker
(Paramedic Dispatch) or NanoMed.
"""
import re

out = {"carried": [], "worn": {}, "verdict": []}


def storage_lines():
    sc = sk.screen(page_size=250).text or ""
    return [l for l in sc.split("\n") if 'on "storage"' in l and "- obj" in l]


def hud_id(name):
    m = re.search(r'- obj (\d+) "%s" at CENTER' % name, sk.screen(page_size=250).text or "")
    return int(m.group(1)) if m else None


# ---- union belt+backpack items across HUD toggles (see docstring)
seen = {}
for _ in range(2):  # pass 1: belt HUD, pass 2: back HUD
    for line in storage_lines():
        m = re.match(r'- obj (\d+) "([^"]+)" .*state=([\w-]+)', line)
        if m:
            seen[int(m.group(1))] = {"name": m.group(2), "state": m.group(3)}
    hid = hud_id("belt" if _ == 0 else "back")
    if hid:
        sk.click(object_id=hid)
        time.sleep(0.6)
for line in storage_lines():
    m = re.match(r'- obj (\d+) "([^"]+)" .*state=([\w-]+)', line)
    if m:
        seen[int(m.group(1))] = {"name": m.group(2), "state": m.group(3)}
out["carried"] = sorted(seen.values(), key=lambda e: e["name"])


def carried(sub):
    return any(sub in e["name"].lower() or sub in e["state"] for e in out["carried"])

# ---- worn slots
inv = sk.inventory(all=True).text or ""
for key, pat in (("pda", r"\bpda\b|\bPDA\b"), ("bandages", r"bandage"),
                 ("gloves", r"nitrile|gloves"), ("headset", r"headset"),
                 ("penlight", r"penlight"), ("backpack", r"backpack")):
    for l in inv.split("\n"):
        if "- obj " in l and re.search(pat, l, re.I) and "human " not in l:
            out["worn"][key] = True
out["worn"]["id_card"] = "ID Card" in inv

# ---- verdicts
if not carried("crew monitor") and not carried("crew_monitor"):
    out["verdict"].append("NO handheld crew monitor â€” triage loop broken "
                          "(NanoMed / Paramedic Dispatch)")
if not carried("emerg_folded") and not carried("roller"):
    out["verdict"].append("NO roller bed â€” bleeding patients must not be dragged; "
                          "get a bed (EMT locker)")
if not out["worn"].get("pda"):
    out["verdict"].append("no PDA â€” Lifeline tracker unavailable")
if not out["worn"].get("gloves"):
    out["verdict"].append("no nitrile gloves â€” you leave fingerprints and inject slower")
if not out["worn"]["id_card"]:
    out["verdict"].append("no ID worn â€” doors won't open (medbay/morgue/maintenance)")
out["ok"] = True
RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
