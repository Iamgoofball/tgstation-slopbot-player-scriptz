# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'),
          encoding='utf-8').read())
precheck()
"""One-envelope Brig Control survey (the Warden's desk): the four consoles
(prisoner management - opened + logged + data dumped, security records,
camera console - interface probe, crew monitoring), the lockdown button grid
(Brig Lockdown Control, Prison Wing Lockdown, Cell Window Control), the
Warden Desk Shutters state, the warden's locker, and mobs in the wing.

Run: run_script {script: ".../job_scriptz/warden/brig_control_check.py",
                 args: {"no_walk"?: true,   # skip walking to the desk
                        "x"?/y?: tile,      # walk fallback if name-search fails
                        "say"?: true}}      # :s check-in at the end
MetaStation Brig Control (verified this round, same round as the secoff
notes): prisoner management console 23959 (108,165), security records
console 23971 (108,163), security camera console 23973 (108,162), crew
monitoring console 23361 (106,162), warden's locker 23163 (105,165,
dense - stand ADJACENT, clicks beyond 1 tile are ignored), lockdown buttons
Brig Lockdown Control 23169 / Prison Wing Lockdown 23170 / Cell Window
Control 23168 at (105,164)ish, Warden Desk Shutters 23717 (107,161).

Fork truths (live-verified):
  - PrisonerManagement tgui: actions eject_id, handle_implant
    {implant_action, implant_ref}, insert_id, login, logout, reset_id,
    set_id_goal; data = {authorized, inserted_id, implants}. Login verified
    (authorized: 0 -> 1). set_id_goal = the labor-camp point goal.
  - Consoles are DENSE: walk to the tile in front, then click.
  - Crew monitor casualties: reuse chief-medical-officer/crew_monitor.py
    (args console=23361 x=106 y=162) - same console type, same parse.
"""
import re

opts = args or {}
out = {"consoles": {}, "verdict": []}


def read_status():
    time.sleep(0.8)
    return (sk.status().text or "")


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
    time.sleep(0.5)
    if active_obj() is not None:
        sk.key(key="Q")
        time.sleep(0.6)


def find_named(q, pat, page_size=8):
    s = sk.search(query=q, kind="obj", page_size=page_size).text or ""
    for l in s.split("\n"):
        m = re.match(r"- obj (\d+) \"([^\"]*)\" at (\d+),(\d+)", l.strip())
        if m and re.search(pat, m.group(2), re.I) and \
                "left the view" not in l:
            return {"id": int(m.group(1)), "name": m.group(2),
                    "x": int(m.group(3)), "y": int(m.group(4)),
                    "line": l.strip()[:150]}
    return None


def open_console_tgui(cid, cx, cy, iface_pat):
    """Walk adjacent, empty-hand click, return the new tgui window id."""
    empty_active_hand()
    g = bot.goto(x=cx, y=cy, max_steps=40)
    walk_ok = "arrived" in (g.text or "")
    c = sk.click(object_id=cid)
    time.sleep(1.8)
    wins = (sk.tgui_windows(all=True).text or "")
    for m in re.finditer(r"  (tgui-window-\d+):\n((?:    [^\n]*\n)+)", wins):
        blk = m.group(2)
        if re.search(iface_pat, blk) and "closed: true" not in blk:
            return m.group(1), blk, walk_ok
    return None, "", walk_ok


# ---- walk to the desk (anchor derived from a console found by NAME -
# ids re-roll every round; args x/y as an explicit fallback)
if not opts.get("no_walk"):
    desk = (find_named("prisoner management console",
                       r"prisoner management")
            or find_named("security records console", r"security records")
            or find_named("warden's locker", r"warden's locker"))
    if desk and desk.get("x"):
        g = bot.goto(x=desk["x"] - 1, y=desk["y"], max_steps=80)
        out["walk"] = "arrived" in (g.text or "")
    elif opts.get("x") and opts.get("y"):
        g = sk.walk_to(x=opts["x"], y=opts["y"], max_steps=80)
        out["walk"] = "arrived" in (g.text or "")
    else:
        out["verdict"].append("no desk anchor found by name - pass args "
                              "x/y or use no_walk")
        out["walk"] = False

# ---- 1) prisoner management console (the warden's own)
pm = find_named("prisoner management console", r"prisoner management")
if pm:
    out["consoles"]["prisoner_management"] = pm
    wid, blk, walk = open_console_tgui(pm["id"], pm["x"] - 1, pm["y"],
                                       r"PrisonerManagement")
    if wid:
        a = sk.tgui_act(id=wid, action="login")
        time.sleep(1.2)
        authed = re.search(r"authorized: (\S+) -> (\S+)", a.text or "")
        w = (sk.tgui_window(id=wid, max_chars=1400).text or "")
        mdata = re.search(r'"data": \{(.*?)\n   \}', w, re.S)
        out["prisoner_console"] = {
            "wid": wid,
            "login_change": authed.groups() if authed else
            ("already", "1"),
            "data": mdata.group(1).replace("\n", " ")[:300] if mdata
            else w[:300],
        }
        out["consoles"]["prisoner_management"]["tgui"] = "open+logged"
    else:
        out["verdict"].append("PrisonerManagement tgui did not open (stand "
                              "adjacent - the console is dense)")
else:
    out["verdict"].append("no prisoner management console found")

# ---- 2) records + camera + crew monitor (locate + state only)
for key, q, pat in (("security_records", "security records console",
                     r"security records"),
                    ("camera", "security camera console",
                     r"camera console"),
                    ("crew_monitor", "crew monitoring console",
                     r"crew monitoring")):
    f = find_named(q, pat)
    if f:
        out["consoles"][key] = f
    else:
        out["verdict"].append("no %s console found" % key)

# camera console: probe its interface name only (the data dump is huge)
cam = out["consoles"].get("camera")
if cam:
    empty_active_hand()
    g = bot.goto(x=cam["x"] - 1, y=cam["y"], max_steps=40)
    c = sk.click(object_id=cam["id"])
    time.sleep(2.2)
    wins = (sk.tgui_windows(all=True).text or "")
    cam_hit = None
    for wblk in re.finditer(r"  (tgui-window-\d+):\n((?:    [^\n]*\n)+)",
                            wins):
        if "closed: true" in wblk.group(2):
            continue
        iface = re.search(r"    interface: ([^\n]*)", wblk.group(2))
        title = re.search(r"    title: ([^\n]*)", wblk.group(2))
        if iface and "camera" in iface.group(1).lower():
            cam_hit = {"wid": wblk.group(1),
                       "title": title.group(1) if title else None,
                       "interface": iface.group(1)}
    if cam_hit:
        out["camera_console"] = cam_hit
    else:
        out["verdict"].append("no camera console tgui opened on this click "
                              "(be adjacent + powered; match the window by "
                              "its interface, not its position in the list)")

# ---- 3) lockdown buttons (found by NAME - ids re-roll every round)
# + shutters + locker
out["lockdown_buttons"] = []
btn_ids, seen = [], set()
for q in ("Lockdown", "Cell Window Control"):
    s = (sk.search(query=q, kind="obj", page_size=10).text or "")
    for l in s.split("\n"):
        m = re.match(r"- obj (\d+) \"([^\"]*)\"", l.strip())
        if m and int(m.group(1)) not in seen and \
                re.search(r"lockdown|cell window control", m.group(2),
                          re.I) and "left the view" not in l:
            seen.add(int(m.group(1)))
            btn_ids.append((int(m.group(1)), m.group(2)))
for bid, bname in btn_ids:
    try:
        e = (sk.examine(object_id=bid).text or "")
    except Exception:
        e = ""
    out["lockdown_buttons"].append({"id": bid, "name": bname,
                                    "examine": e.split("\n")[1][:120]
                                    if len(e.split("\n")) > 1 else e[:120]})
sh = find_named("Warden Desk Shutters", r"Warden Desk Shutters")
if sh:
    out["desk_shutters"] = {"id": sh["id"],
                            "state": sh["line"].split("state=")[-1][:20]}
wl = find_named("warden's locker", r"warden's locker")
if wl:
    t = (sk.tile(wl["x"], wl["y"], all=True).text or "")
    line = next((l for l in t.split("\n") if ("obj %d " % wl["id"]) in l),
                "")
    out["wardens_locker"] = {"id": wl["id"],
                             "locked": "[locked]" in line,
                             "open": "menu obj" in line or
                             "[warden_open]" in line}

# ---- 4) mobs in the wing
st = read_status()
my_id = re.search(r"you: mob (\d+)", st)
my_id = my_id.group(1) if my_id else None
my_name = _my_name()
VERMIN = re.compile(r"hauberoach|roach|mouse|rat|carp|spider", re.I)
mobs = []
s = (sk.search(query="", kind="mob", page_size=25).text or "")
for l in s.split("\n"):
    m = re.match(r"- mob (\d+) \"([^\"]*)\"", l.strip())
    if m and m.group(1) != my_id and m.group(2) != my_name:
        area = re.search(r"in (?:area )?\"?([A-Za-z][A-Za-z' &-]*)", l)
        mobs.append({"id": int(m.group(1)), "name": m.group(2),
                     "area": area.group(1).strip() if area else None})
out["mobs_near"] = mobs
out["vermin_near"] = [m["name"] for m in mobs if VERMIN.search(m["name"])]
prisoners = [m for m in mobs if not VERMIN.search(m["name"]) and
             m["name"] != "McGriff" and
             (m["area"] or "").startswith(("Brig", "Holding", "Prison"))]
out["prisoners_in_wing"] = prisoners
if prisoners:
    out["verdict"].append("PRISONERS in the wing: %s"
                          % ", ".join(m["name"] for m in prisoners))
else:
    out["verdict"].append("no prisoners in the wing - cells are empty")

# ---- radio check-in
if opts.get("say", True):
    try:
        sk.say(text="Brig check: consoles %s, cells empty, lockdown %s."
               % ("OK" if out["consoles"].get("prisoner_management")
                  else "CHECK", "ready"), radio="security")
        time.sleep(0.6)
        out["said"] = True
    except Exception as exc:
        out["verdict"].append("radio say failed: %s" % exc)

RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
