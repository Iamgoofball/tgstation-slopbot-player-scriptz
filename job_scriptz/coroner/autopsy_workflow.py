# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Full AUTOPSY chain on one corpse, in place (no towing): prep the chest ->
make skin incision -> retract skin -> autopsy -> read the report.

Run: run_script {script: ".../job_scriptz/coroner/autopsy_workflow.py",
                 args: {"patient": <mob id>,
                        "aid"?: id, "scalpel"?: id, "retractor"?: id,
                        "scanner"?: id, "expect_name"?: "Name"}}
Tool ids optional - auto-found from view (floor pile next to the corpse).
The patient must ALREADY be exposed: morgue occupant = morgue_tray_control
open the unit, then open_bag on its labeled body bag, then pass that mob id.

Fork truths (operations/*.dm + live-proven):
  aid (surgical drapes / bedsheet) applies the surgery_prepped status effect
  (TRAIT_READY_TO_OPERATE) per zone - the ITEM IS NOT CONSUMED; clicking the
  same zone again CLEARS it ("surgery cleared" -> click once more to re-prepare).
  chain (all chest, corpse must be dead + lying):
    1. drape: balloon "chest surgery prepared"
    2. scalpel: "make skin incision" 1.6s -> SURGERY_SKIN_CUT (auto-runs, no
       radial when it is the only op; re-click probe answers "nothing to do
       with scalpel!" when done)
    3. retractor: "retract skin" 2.4s -> SURGERY_SKIN_OPEN (the step people
       forget - without it the scanner healthscans instead of operating)
    4. scanner: "autopsy" 10s -> "You succeed." + "autopsy report of <name>
       - <time>" paper spawns IN YOUR HAND (TRAIT_DISSECTED set - one autopsy
       per corpse).
  The scanner's own cadaver healthscan preempts surgery when no op is
  available ("ANALYZING CADAVER") - that is the tell the chain is not ready.
  Q drops land at your feet (tools pile up next to the corpse - tidy after).
"""
import re

opts = args or {}
out = {"steps": [], "verdict": [], "tools": {}}
PATIENT = opts.get("patient") and int(opts["patient"])
if not PATIENT:
    RESULT = {"ok": False, "note": "args.patient = <mob id> required"}


class StepFail(Exception):
    pass


def active_obj():
    inv = sk.inventory().text or ""
    m = re.search(r'active_hand[^\n]*obj (\d+)', inv)
    return int(m.group(1)) if m else None


def in_hands(oid):
    return ("obj %d " % oid) in (sk.inventory().text or "")


def obj_line(oid, name_hint=None):
    """-> (x, y, line) from in-view search, else the known index (by name)."""
    for q in ("", name_hint or str(oid)):
        s = sk.search(query=q, in_view=(q == "" or name_hint is None),
                      page_size=120).text or ""
        for line in s.split("\n"):
            m = re.match(r'- obj (%d) "[^"]*" at (\d+),(\d+)' % oid, line.strip())
            if m:
                return int(m.group(2)), int(m.group(3)), line
    return None, None, None


def ensure_held(oid, label, name_hint=None):
    """Get obj oid into the ACTIVE hand. Returns how; records dropped ids."""
    if oid is None:
        raise StepFail("no %s id available" % label)
    if active_obj() == oid:
        out["tools"][label] = oid
        return "active"
    if in_hands(oid):
        sk.key(key="X")
        time.sleep(0.4)
        if active_obj() == oid:
            out["tools"][label] = oid
            return "swapped"
    dropped = active_obj()
    if dropped:
        sk.key(key="Q")
        time.sleep(0.5)
        out["verdict"].append("dropped obj %s from the active hand" % dropped)
    x, y, _ = obj_line(oid, name_hint)
    if x is None:
        raise StepFail("%s obj %s not locatable" % (label, oid))
    g = bot.goto(x=x, y=y, max_steps=60)
    sk.click(object_id=oid)
    time.sleep(0.8)
    if active_obj() != oid:
        raise StepFail("%s obj %s did not reach the active hand" % (label, oid))
    out["tools"][label] = oid
    return "picked"


def find_tool(name_re, exact=None):
    """floor item id by name in view, then known index."""
    for s in (sk.search(query=exact or name_re, in_view=True, page_size=150).text or "",
              sk.search(query=exact or name_re, page_size=150).text or ""):
        for line in s.split("\n"):
            m = re.match(r'- obj (\d+) "([^"]*)"', line.strip())
            if not m:
                continue
            nm = m.group(2).lower()
            if re.fullmatch(exact, nm) if exact else re.search(name_re, nm):
                if "carried by" not in line:
                    return int(m.group(1))
    return None


def try_step(label, tool_oid, wait_s, probe_words):
    """click patient with the tool, wait, verify via a re-click probe."""
    how = ensure_held(tool_oid, label, label.split()[0])
    c = sk.click(object_id=PATIENT)
    time.sleep(wait_s)
    ans = (c.text or "")
    ch = _pull_chat(2)
    if re.search(r"You succeed", ch):
        out["steps"].append({"step": label, "result": "done (chat success)", "how": how})
        return
    if re.search(r'nothing to do with %s' % re.escape(label.split()[0]), ans):
        out["steps"].append({"step": label, "result": "already done", "how": how})
        return
    if re.search(r'not lying down|obstructed|he is dead!', ans):
        raise StepFail("%s refused: %s" % (label,
                      (re.search(r'(not lying down|operation site is obstructed!|he is dead!)', ans) or ["?"])[0]))
    if "in_progress" not in ans:
        # maybe started without the tag: fall through to the probe
        pass
    time.sleep(wait_s)
    # probe: a second click must now answer "nothing to do"
    for attempt in range(2):
        c2 = sk.click(object_id=PATIENT)
        time.sleep(1.6)
        a2 = (c2.text or "")
        if re.search(probe_words, a2):
            out["steps"].append({"step": label, "result": "done", "how": how})
            return
        if "in_progress" in a2:
            time.sleep(wait_s)   # op restarted by the probe - wait it out
            continue
        out["steps"].append({"step": label, "result": "probe unclear", "tail": a2[-160:]})
        return
    raise StepFail("%s did not complete (probe: %s)" % (label, a2[-120:]))


if PATIENT:
    try:
        # ---- 0. locate + guard the patient
        s = sk.search(query="", kind="mob", in_view=True, page_size=120).text or ""
        pm = None
        for line in s.split("\n"):
            m = re.match(r'- mob (\d+) "([^"]*)" at (\d+),(\d+)', line.strip())
            if m and int(m.group(1)) == PATIENT:
                pm = m
        if not pm:
            raise StepFail("patient mob %s not in view (open its morgue tray + "
                           "body bag first)" % PATIENT)
        out["patient"] = {"id": PATIENT, "name": pm.group(2),
                          "tile": [int(pm.group(3)), int(pm.group(4))]}
        if opts.get("expect_name") and opts["expect_name"].lower() not in pm.group(2).lower():
            out["verdict"].append("name mismatch: %r vs %r" % (pm.group(2), opts["expect_name"]))
        e = sk.examine(object_id=PATIENT).text or ""
        if re.search(r"catatonic", e, re.I):
            raise StepFail("patient is ALIVE (catatonic) - autopsy is for the dead")
        g = bot.goto(object_id=PATIENT, max_steps=80)
        out["walk"] = (g.text or "")[:80]

        # ---- 1. prep the chest (skip if already prepped - clicking clears!)
        if re.search(r"adorning (his|her|their) chest", e):
            out["steps"].append({"step": "prep", "result": "already prepped"})
        else:
            aid = opts.get("aid") and int(opts["aid"]) or find_tool(r"surgical drapes")
            if aid is None:
                raise StepFail("no surgical drapes in view - pass args.aid "
                               "(any surgery aid: drapes, bedsheet)")
            how = ensure_held(aid, "aid", "surgical drapes")
            c = sk.click(object_id=PATIENT)
            time.sleep(1.6)
            a = (c.text or "")
            if "surgery cleared" in a:
                c2 = sk.click(object_id=PATIENT)   # was prepped - re-apply
                time.sleep(1.6)
                a = (c2.text or "") + " (re-clicked)"
            ok = "surgery prepared" in a
            out["steps"].append({"step": "prep", "result": "prepared" if ok else "unclear",
                                 "how": how, "tail": a[-120:]})
            if not ok:
                raise StepFail("prep did not register: %s" % a[-100:])

        # ---- 2. incise (scalpel)
        scalpel = opts.get("scalpel") and int(opts["scalpel"]) or find_tool(r"^scalpel$", exact=r"scalpel")
        try_step("scalpel incise", scalpel, 2.2, r"nothing to do with scalpel")

        # ---- 3. retract (retractor) -> skin OPEN
        retractor = opts.get("retractor") and int(opts["retractor"]) or find_tool(r"retractor")
        try_step("retractor retract", retractor, 3.2, r"nothing to do with retractor")

        # ---- 4. autopsy (scanner) -> report in hand
        scanner = opts.get("scanner") and int(opts["scanner"]) or find_tool(r"autopsy scanner")
        ensure_held(scanner, "scanner", "autopsy scanner")
        c = sk.click(object_id=PATIENT)
        a = (c.text or "")
        time.sleep(12.0)
        ch = _pull_chat(2)
        if "ANALYZING CADAVER" in ch or "ANALYZING CADAVER" in a:
            raise StepFail("scanner healthscan fired instead of the autopsy op "
                           "(skin not open / already dissected)")
        out["steps"].append({"step": "scanner autopsy",
                             "result": "started" if ("in_progress" in a or "You succeed" in ch) else a[-120:]})
        # ---- 5. the report
        time.sleep(2.0)
        rid, rname = None, None
        s = sk.search(query="autopsy report", page_size=40).text or ""
        m = re.search(r'- obj (\d+) "(autopsy report[^"]*)"', s)
        if m:
            rid, rname = int(m.group(1)), m.group(2)
        out["report"] = {"id": rid} if rid else None
        if not rid:
            raise StepFail("no autopsy report spawned (op may not have finished)")
        e2 = sk.examine(object_id=rid).text or ""
        w = sk.tgui_windows(all=True).text or ""
        wid = None
        for mm in re.finditer(r'(  (tgui-window-\d+):\n(?:(?:    [^\n]*)\n)+)', w):
            blk = mm.group(1)
            if "PaperSheet" in blk and "closed: true" not in blk:
                a2 = re.search(r"updated_s_ago: ([0-9.]+)", blk)
                if a2 and float(a2.group(1)) < 10:
                    wid = mm.group(2)
        if wid:
            d = sk.tgui_window(id=wid, max_chars=3000).text or ""
            mp = re.search(r"text_preview: (.*)", d)
            out["report"]["text"] = (mp.group(1)[:400] if mp else None)
            sk.tgui_send(id=wid, type="close")
        out["ok"] = True
        out["verdict"].append("autopsy complete: report %s %r" % (rid, (rname or "?")[:50]))
    except StepFail as ex:
        out["ok"] = False
        out["verdict"].append("STEP FAILED: %s" % ex)

if "RESULT" not in dir():
    RESULT = out
RESULT.setdefault("ok", False)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
