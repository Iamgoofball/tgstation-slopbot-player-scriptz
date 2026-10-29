# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Work the MEDICAL RECORDS terminal (MedicalRecords tgui): read the crew
records or edit one - notes, cause of death, physical/mental status, blood
type. The coroner's morgue laptop is the usual terminal (MetaStation: obj at
the morgue desk, (100,83)).

Run: run_script {script: ".../job_scriptz/coroner/medical_records.py",
                 args: {"action": "read"|"add_note"|"cause"|"physical"
                                      |"mental"|"blood",
                        "laptop"?: <obj id>,   # else finds "medical laptop" in view
                        "name": "Weinstein",   # substring of the record's crew name
                        "value": "..."}}       # note text / cause / status / blood
Default action "read". Any MedicalRecords terminal works - the Detective's
Office WALL CONSOLE verified identically (pass its id as laptop).

Fork truths (computer/records/medical.dm ui_act - ALL params go with
crew_ref located in GLOB.manifest.general):
  add_note   {crew_ref, content} - content passes reject_bad_name (strict:
             letters/numbers/spaces; >2 notes on a record: oldest are cut).
  delete_note{crew_ref, note_ref}
  set_physical_status {crew_ref, physical_status} - must be a listed status
             (the window data lists them; e.g. Deceased). Setting anything
             but Deceased CLEARS cause_of_death.
  set_mental_status   {crew_ref, mental_status}
  set_cause_of_death  {crew_ref, cause}
  set_blood_type      {crew_ref, blood_type} - roundstart blood type NAME ("A+").
Click the laptop with an EMPTY active hand (item-in-hand = attackby). The
window is the tgui whose interface is MedicalRecords; records carry a
crew_ref the UI actions need - action "read" dumps the name->ref map.
data.records reads via path as a pretty-printed JSON array (retry until
the header's items: N); same-name records = one per body (actions target
the first ref per name).
"""
import json
import re

opts = args or {}
action = (opts.get("action") or "read").lower()
out = {"action": action, "verdict": []}


def empty_active_hand():
    """Free the active hand: X-swap first, then Q-drop if both hands are full.
    Returns the list of dropped obj ids (recorded for tidy-up)."""
    dropped = []
    for attempt in range(3):
        inv = sk.inventory().text or ""
        act = [l for l in inv.split("\n") if "active_hand" in l]
        if act and ("empty" in act[0] or "obj" not in act[0]):
            if dropped:
                out["verdict"].append("dropped to free the active hand: %s" % dropped)
            return dropped
        if attempt == 0:
            sk.key(key="X")
            time.sleep(0.4)
        else:
            m = re.search(r'active_hand[^\n]*obj (\d+)', inv)
            if m:
                sk.key(key="Q")
                time.sleep(0.5)
                dropped.append(int(m.group(1)))
    out["verdict"].append("could not free the active hand (dropped %s)" % dropped)
    return dropped


def find_laptop():
    lid = opts.get("laptop") and int(opts["laptop"])
    # search matches NAMES, not ids - scan the full in-view list for the id,
    # then fall back to a name query (in view, then the known index)
    for q, iv in (("", True), ("medical laptop", True), ("medical laptop", False)):
        s = sk.search(query=q, in_view=iv, page_size=200).text or ""
        for line in s.split("\n"):
            m = re.match(r'- obj (\d+) "([^"]*)" at (\d+),(\d+)', line.strip())
            if m and (lid and int(m.group(1)) == lid or "laptop" in m.group(2).lower()):
                return {"id": int(m.group(1)), "name": m.group(2),
                        "x": int(m.group(3)), "y": int(m.group(4))}
    return None


def records_window():
    w = sk.tgui_windows(all=True).text or ""
    for mm in re.finditer(r'(  (tgui-window-\d+):\n(?:(?:    [^\n]*)\n)+)', w):
        blk = mm.group(1)
        if "MedicalRecords" in blk and "closed: true" not in blk:
            a = re.search(r"updated_s_ago: ([0-9.]+)", blk)
            if a and float(a.group(1)) < 15:
                return mm.group(2)
    return None


def parse_records(dat):
    """(name -> crew_ref) pairs + the entry count from the records list.
    data.records read via path comes back as `items: N` + a pretty-printed
    JSON array (value: | block) - slice first '[' .. last ']' and loads it
    whole; the overview-dump regexes stay as a fallback for small lists.
    Returns (pairs, total): pairs maps each UNIQUE name to its FIRST ref
    (same-name records = one per body; actions target the first)."""
    pairs = {}
    total = 0
    i, j = dat.find("["), dat.rfind("]")
    if 0 <= i < j:
        try:
            arr = json.loads(dat[i:j + 1])
            for e in arr:
                if isinstance(e, dict) and e.get("name") and \
                        e.get("crew_ref"):
                    total += 1
                    pairs.setdefault(e["name"], e["crew_ref"])
            if total:
                return pairs, total
        except Exception:
            pass
    hits = re.findall(r'"name": "([^"]{3,60})"[^{}]*?"crew_ref": "([^"]+)"', dat)
    if not hits:   # ref first, name after
        hits = [(n, r) for r, n in re.findall(
            r'"crew_ref": "([^"]+)"[^{}]*?"name": "([^"]{3,60})"', dat)]
    for n, r in hits:
        total += 1
        pairs.setdefault(n, r)
    return pairs, total


lap = find_laptop()
if not lap:
    RESULT = {"ok": False, "note": "no medical laptop in view - stand at the "
                                   "morgue desk or pass args.laptop = <id>"}
else:
    out["laptop"] = lap
    empty_active_hand()
    g = bot.goto(x=lap["x"], y=lap["y"], max_steps=60)
    c = sk.click(object_id=lap["id"])
    time.sleep(1.6)
    wid = records_window()
    if not wid:
        RESULT = {"ok": False, "note": "MedicalRecords window did not open "
                                       "(click answer: %s)" % (c.text or "")[-120:]}
    else:
        # data.records populates ASYNC after the click - read with retry
        # until the entry count reaches the header's `items: N`
        recs, total = {}, 0
        for attempt in range(3):
            dat = (sk.tgui_window(id=wid, path="data.records",
                                  max_chars=20000).text or "")
            dat = dat.replace("\\n", "\n")
            recs, total = parse_records(dat)
            m_items = re.search(r"items: (\d+)", dat)
            want = int(m_items.group(1)) if m_items else total
            if total >= want:
                break
            time.sleep(1.5)
        out["records"] = [{"name": k, "crew_ref": v} for k, v in recs.items()][:30]
        out["records_total"] = total
        if total < want:
            out["verdict"].append("records list incomplete: %d of %s entries"
                                  % (total, want))
        elif total > len(recs):
            out["verdict"].append("%d records, %d unique names (same-name "
                                  "records = one per body; actions target "
                                  "the first ref per name)"
                                  % (total, len(recs)))
        if action == "read":
            out["ok"] = True
        else:
            name_q = opts.get("name") or ""
            target = [(n, r) for n, r in recs.items()
                      if name_q.lower() in n.lower()] if name_q else \
                     ([(n, r) for n, r in recs.items()] if len(recs) == 1 else [])
            if len(target) != 1:
                out["ok"] = False
                out["verdict"].append("args.name %r matched %d records - be more "
                                      "specific" % (name_q, len(target)))
            else:
                crew_ref = target[0][1]
                PARAMS = {
                    "add_note": ("add_note", {"crew_ref": crew_ref,
                                              "content": opts.get("value") or ""}),
                    "cause": ("set_cause_of_death", {"crew_ref": crew_ref,
                                                     "cause": opts.get("value") or ""}),
                    "physical": ("set_physical_status", {"crew_ref": crew_ref,
                                                         "physical_status": opts.get("value") or ""}),
                    "mental": ("set_mental_status", {"crew_ref": crew_ref,
                                                     "mental_status": opts.get("value") or ""}),
                    "blood": ("set_blood_type", {"crew_ref": crew_ref,
                                                 "blood_type": opts.get("value") or ""}),
                }
                act, params = PARAMS[action]
                if not opts.get("value"):
                    out["ok"] = False
                    out["verdict"].append("action %s needs args.value (statuses/notes/"
                                          "blood are validated server-side: use a value the "
                                          "window data lists)" % action)
                else:
                    a = sk.tgui_act(id=wid, action=act, params=params)
                    time.sleep(1.4)
                    dat2 = sk.tgui_window(id=wid, max_chars=9000).text or ""
                    changed = dat2 != dat
                    out["crew_ref"] = crew_ref
                    out["ui_act"] = (a.text or "")[:160]
                    out["data_changed"] = changed
                    if action == "add_note" and opts["value"][:24] in dat2:
                        out["ok"] = True
                        out["verdict"].append("note visible in the record data")
                    elif action in ("physical", "mental", "blood", "cause") and \
                            opts["value"][:24] in dat2:
                        out["ok"] = True
                        out["verdict"].append("value visible in the record data")
                    else:
                        out["ok"] = changed
                        if not changed:
                            out["verdict"].append("window data unchanged - the action "
                                                  "may have been rejected (check the value)")
        try:
            sk.tgui_send(id=wid, type="close")
        except Exception:
            pass

if "RESULT" not in dir():
    RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
