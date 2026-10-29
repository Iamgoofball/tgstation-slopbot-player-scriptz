# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'),
          encoding='utf-8').read())
precheck()
"""Security records console (tgui "SecurityRecords") driver: login, list the
crew records (name/rank/wanted_status/crew_ref), add a crime or citation,
set the wanted status, invalidate a crime, edit a field, logout.

Run: run_script {script: ".../job_scriptz/security-officer/sec_records_control.py",
                 args: {"mode": "status"|"list"|"login"|"logout"|"set_wanted"|
                              "add_crime"|"invalidate_crime"|"edit_field",
                        "console"?: <obj id>,     # else nearest by name
                        "crew"?: <name regex>,    # whose record (list finds it)
                        "crew_ref"?: "[0x...]",   # exact ref (skips the lookup)
                        "status"?: "None"|"Suspected"|"Arrest"|"Incarcerated"|
                                   "Parole"|"Discharged",
                        "crime"?: "Theft", "details"?, "fine"?: 0,
                        "crime_ref"?: "[0x...]", "field"?, "value"?}}
Console locations (MetaStation, this round): Security Office 27423 at
(121,169), Brig Control 23971 at (108,163), Detective's Office 28268,
HoS office 28457, Security Post - Cargo Bay 16734, Security Post - Medbay
19876, Security Post - Science 29234, Customs 10952.

Verified live (own record): login, list (13 records), set_wanted
(None -> Suspected -> None), add_crime (fine 100 = CITATION, no status
change), invalidate_crime (voided it), logout.
NEVER tested / dangerous: add_crime with fine 0 (a CRIME - sets Arrest and
Beepsky arrests on sight), delete_record, purge_records (destroys records).

Fork truths (this round):
  - Opening the console needs an EMPTY ACTIVE hand (a held item attackbys).
  - The window's data comes from sk.tgui_window(id, path="data.records",
    fields="name,rank,wanted_status,crew_ref") - tgui_windows does NOT dump
    it; statuses live in data.available_statuses.
  - Valid actions (server introspection): add_crime, delete_record,
    edit_crime, edit_field, invalidate_crime, login, logout, print_record,
    purge_records, set_wanted, view_record. There is NO set_note on this
    fork - notes go through edit_field.
  - Arrest requires at least one crime on the record; a fine > 0 makes a
    citation instead (no status change). Only the crime's author or someone
    with armory access can edit/invalidate it.
"""
import re

opts = args or {}
mode = opts.get("mode") or "status"
out = {"mode": mode, "verdict": []}


def active_obj():
    for l in (sk.inventory().text or "").split("\n"):
        if "lhandactive" in l:
            m = re.match(r"- obj (\d+)", l.strip())
            if m:
                return int(m.group(1))
    return None


def empty_active_hand():
    if active_obj() is None:
        return
    sk.key(key="X")
    time.sleep(0.4)
    if active_obj() is not None:
        sk.key(key="Q")
        time.sleep(0.5)


def act_changes(a):
    t = a.text or ""
    if re.search(r"data_changes: none", t):
        return {}
    seg = re.split(r"data_changes:", t)
    if len(seg) < 2:
        return None
    ch = {}
    for line in seg[1].split("\n"):
        # keys are dotted paths, often with an annotation in parens:
        # - records.12.wanted_status (Lennox Fields): "None" -> "Suspected"
        m = re.match(r'\s*- ([\w.]+(?: \([^)]*\))?): "?([^" ]*)"? -> '
                     r'"?([^" ]*)"?', line)
        if m:
            ch[m.group(1)] = (m.group(2), m.group(3))
        elif line.strip() and not line.strip().startswith("-") and ch:
            break
    return ch


def find_console():
    cid = opts.get("console")
    if cid:
        return cid, None
    s = sk.search(query="security records console", page_size=10).text or ""
    best = None
    for l in s.split("\n"):
        m = re.match(r'- obj (\d+) "security records console" at (\d+),(\d+)',
                     l.strip())
        if m and "left the view" not in l:
            d = int(m.group(2)) + int(m.group(3))
            if best is None or d < best[0]:
                best = (d, int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (best[1], (best[2], best[3])) if best else (None, None)


def open_window(cid):
    empty_active_hand()
    if cid[1]:
        g = bot.goto(x=cid[1][0], y=cid[1][1], max_steps=80)
        if "arrived" not in (g.text or ""):
            out["verdict"].append("walk to the console: %s"
                                  % (g.text or "")[:80])
    c = sk.click(object_id=cid[0])
    time.sleep(2.0)
    wins = sk.tgui_windows(all=True).text or ""
    for m in re.finditer(r"(  (tgui-window-\d+):\n(?:(?:    [^\n]*)\n)+)",
                         wins):
        if "SecurityRecords" in m.group(1) and "closed: true" not in \
                m.group(1):
            return m.group(2)
    return None


def is_authed(wid):
    try:
        w = sk.tgui_window(id=wid, path="data.authenticated", max_chars=80)
        m = re.search(r"value: (\S+)", w.text or "")
        return bool(m and m.group(1) in ("1", "true"))
    except Exception:
        return False


def ensure_login(wid):
    if is_authed(wid):
        out["logged_in"] = True
        return True
    a = sk.tgui_act(id=wid, action="login")
    time.sleep(1.4)
    ch = act_changes(a)
    out["login_changes"] = ch
    ok = bool(ch and ch.get("authenticated", ("", ""))[1] in ("1", "true"))
    if not ok:
        # already-authenticated consoles no-op the login act: prove it with
        # a data read
        try:
            w = sk.tgui_window(id=wid, path="data.records", max_chars=200)
            if "items:" in (w.text or ""):
                ok = True
                out["verdict"].append("already authenticated (the login act "
                                      "was a no-op, data reads fine)")
        except Exception:
            pass
    out["logged_in"] = ok
    if not ok:
        out["verdict"].append("login failed - security access needed")
    return ok


def records(wid):
    w = sk.tgui_window(id=wid, path="data.records",
                       fields="name,rank,wanted_status,crew_ref",
                       max_chars=8000)
    rows = []
    for l in (w.text or "").split("\n"):
        m = re.match(r'- \{"name":"([^"]*)","rank":"([^"]*)",'
                     r'"wanted_status":"([^"]*)",'
                     r'"crew_ref":"(\[0x[0-9a-f]+\])"', l.strip())
        if m:
            rows.append({"name": m.group(1), "rank": m.group(2),
                         "wanted_status": m.group(3),
                         "crew_ref": m.group(4)})
    return (w.text or ""), rows


def resolve_crew(wid):
    ref = opts.get("crew_ref")
    if ref:
        return ref, None
    crew = opts.get("crew")
    if not crew:
        return None, None
    _, rows = records(wid)
    hits = [r for r in rows if re.search(crew, r["name"], re.I)]
    if opts.get("rank"):
        hits = [r for r in hits if re.search(opts["rank"], r["rank"], re.I)]
    if not hits:
        out["verdict"].append("no record matches crew=%r (rank=%r)"
                              % (crew, opts.get("rank")))
        return None, None
    if len(hits) > 1:
        out["verdict"].append("%d records match - picked the first: %s / %s; "
                              "pass rank= to disambiguate"
                              % (len(hits), hits[0]["name"], hits[0]["rank"]))
    return hits[0]["crew_ref"], hits[0]["name"]


# ---- open + login
cid = find_console()
if not cid[0]:
    RESULT = {"ok": False, "note": "no security records console found"}
else:
    out["console"] = cid
    wid = open_window(cid)
    if not wid:
        RESULT = {"ok": False, "note": "SecurityRecords tgui did not open"}
    else:
        out["wid"] = wid
        if mode in ("status", "list") or mode not in ("logout",):
            ensure_login(wid)
        # ---- modes
        if mode in ("status",):
            try:
                w = sk.tgui_window(id=wid, path="data", outline=True,
                                   max_chars=1500)
                out["data_outline"] = (w.text or "")[:900]
            except Exception as exc:
                out["verdict"].append("tgui_window data: %s" % exc)
            out["ok"] = out.get("logged_in", False)
        elif mode in ("list",):
            txt, rows = records(wid)
            out["records"] = rows
            out["records_raw_head"] = txt[:1200]
            try:
                w = sk.tgui_window(id=wid, path="data.available_statuses",
                                   max_chars=300)
                out["statuses"] = (w.text or "")[:200]
            except Exception as exc:
                out["verdict"].append("statuses: %s" % exc)
            out["ok"] = bool(rows) or bool(txt)
        elif mode in ("set_wanted", "add_crime", "invalidate_crime",
                      "edit_field"):
            ensure_login(wid)
            cref, cname = resolve_crew(wid)
            if mode != "invalidate_crime" and not cref:
                out["verdict"].append("no crew_ref (give crew_ref or crew)")
                out["ok"] = False
            elif mode == "set_wanted":
                a = sk.tgui_act(id=wid, action="set_wanted",
                                params={"crew_ref": cref,
                                        "status": opts.get("status")
                                        or "Suspected"})
                time.sleep(1.4)
                ch = act_changes(a)
                out["changes"] = ch
                want = opts.get("status") or "Suspected"
                moved = ch and any("wanted_status" in k and v[1] == want
                                   for k, v in ch.items())
                out["ok"] = bool(moved)
                if not out["ok"] and ch is not None:
                    out["verdict"].append("wanted_status did not move to %r "
                                          "(Arrest needs a crime on the "
                                          "record first?) - see changes"
                                          % want)
                err = re.search(r"(Error|failed|denied)[^\n]*", a.text or "")
                if err:
                    out["verdict"].append(err.group(0))
                    out["ok"] = False
            elif mode == "add_crime":
                a = sk.tgui_act(id=wid, action="add_crime",
                                params={"crew_ref": cref,
                                        "name": opts.get("crime")
                                        or "Test citation",
                                        "details": opts.get("details") or "",
                                        "fine": opts.get("fine", 0)})
                time.sleep(1.4)
                ch = act_changes(a)
                out["changes"] = ch
                err = re.search(r"(Error|failed|denied)[^\n]*", a.text or "")
                if err:
                    out["verdict"].append(err.group(0))
                fine = opts.get("fine", 0)
                if out.get("ok") is not False:
                    out["ok"] = not err
                if fine and fine > 0:
                    out["verdict"].append("citation added (fine %s) - void "
                                          "it with invalidate_crime" % fine)
                else:
                    out["verdict"].append("CRIME added - this SETS ARREST; "
                                          "check the wanted status")
                # fetch the new crime_ref
                try:
                    w = sk.tgui_window(id=wid, path="data.records",
                                       fields="name,citations", max_chars=4000)
                    out["citations_raw"] = (w.text or "")[:800]
                except Exception:
                    pass
            elif mode == "invalidate_crime":
                cr = opts.get("crime_ref")
                if not cr:
                    txt, _ = records(wid)
                    m = re.search(r'"crime_ref":"(\[0x[0-9a-f]+\])"', txt)
                    cr = m and m.group(1)
                if not cr:
                    out["verdict"].append("no crime_ref found to invalidate")
                    out["ok"] = False
                else:
                    a = sk.tgui_act(id=wid, action="invalidate_crime",
                                    params={"crew_ref": cref,
                                            "crime_ref": cr})
                    time.sleep(1.4)
                    ch = act_changes(a)
                    out["changes"] = ch
                    out["crime_ref"] = cr
                    out["ok"] = bool(ch) and ch is not None
            elif mode == "edit_field":
                a = sk.tgui_act(id=wid, action="edit_field",
                                params={"crew_ref": cref,
                                        "field": opts.get("field"),
                                        "value": opts.get("value", "")})
                time.sleep(1.4)
                ch = act_changes(a)
                out["changes"] = ch
                out["ok"] = bool(ch) and ch is not None
                err = re.search(r"(Error|failed|denied)[^\n]*", a.text or "")
                if err:
                    out["verdict"].append(err.group(0))
        elif mode == "logout":
            a = sk.tgui_act(id=wid, action="logout")
            time.sleep(1.4)
            ch = act_changes(a)
            out["changes"] = ch
            out["ok"] = bool(ch and ch.get("authenticated",
                                           ("1", "0"))[1] in ("0", "false"))
        else:
            out["verdict"].append("unknown mode %r" % mode)
            out["ok"] = False

RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
