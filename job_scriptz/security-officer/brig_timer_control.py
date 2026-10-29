# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'),
          encoding='utf-8').read())
precheck()
"""Brig cell door timer (tgui "BrigTimer") driver: read the timer, set a
preset (short=2 / medium=3 / long=5 min), adjust the time (+-600 = 1 min,
+-100 = 10 s), start (closes the cell door + locks the cell locker),
stop (opens + unlocks, no radio message), flash (fires the cell flasher),
or run a full SAFE round-trip (mode "cycle") on an EMPTY cell.

Run: run_script {script: ".../job_scriptz/security-officer/brig_timer_control.py",
                 args: {"mode": "status"|"preset"|"time"|"start"|"stop"|
                              "flash"|"cycle",
                        "timer"?: <obj id>,      # else by name near args.x/y
                        "name"?: "Cell 2",       # the display's name
                        "preset"?: "short"|"medium"|"long",
                        "adjust"?: 600,          # +- seconds for "time"
                        "force"?: true}}         # start even if occupied
Cell timers (MetaStation, this round): "Cell 2" 22173 at (101,165), "Cell 3"
22651 at (103,165) - NOTE a cell DOOR also answers to "Cell 3" (22656 at
103,164): pass the id, or the script skips dense matches. Max sentence 15
minutes. Starting a timer with a prisoner inside is the JOB's tool - direct
modes trust the caller; only `cycle` runs the empty-cell guard.

Fork truths (live-verified on Cell 2, 22173):
  - The timer is a WALL DISPLAY named "Cell N" (icon [frame]); click it with
    an EMPTY active hand (held items attackby).
  - The tgui window dump carries NO state (only title/interface/object) -
    ALL verification comes from the ACT's data_changes:
      preset -> "minutes: 0 -> 2"; start -> "timing: 0 -> 1" (+ the cell
      door's leftsecureopen -> leftsecureclosing); stop -> "timing: 1 -> 0"
      (+ the door reopening); time -> "seconds/minutes: A -> B".
  - `cycle` refuses to start when ANY mob (even a hauberoach) is in the
    cell zone (3x6 south of the timer) unless force=true.
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


def find_timer():
    tid = opts.get("timer")
    if tid:
        s = sk.search(query="Cell", kind="obj", page_size=15).text or ""
        for l in s.split("\n"):
            m = re.match(r"- obj (\d+) \"(Cell \d)\" at (\d+),(\d+)",
                         l.strip())
            if m and int(m.group(1)) == tid:
                return tid, (int(m.group(3)), int(m.group(4))), m.group(2)
        return tid, None, None
    name = opts.get("name") or "Cell"
    s = sk.search(query=name, kind="obj", page_size=15).text or ""
    best = None
    for l in s.split("\n"):
        m = re.match(r'- obj (\d+) "(Cell \d)" at (\d+),(\d+)', l.strip())
        if m and re.match(r"Cell \d$", m.group(2)) and " dense " not in l:
            d = int(m.group(3)) + int(m.group(4))
            if best is None or d < best[0]:
                best = (d, int(m.group(1)), int(m.group(3)), int(m.group(4)),
                        m.group(2))
    return (best[1], (best[2], best[3]), best[4]) if best else (None, None,
                                                               None)


def act_changes(a):
    """Parse an act's data_changes into {key: (from, to)}."""
    t = a.text or ""
    if re.search(r"data_changes: none", t):
        return {}
    ch = {}
    seg = re.split(r"data_changes:", t)
    if len(seg) < 2:
        return None   # no data_changes section at all
    for line in seg[1].split("\n"):
        m = re.match(r"\s*- (\w+): (\S+) -> (\S+)", line)
        if m:
            ch[m.group(1)] = (m.group(2), m.group(3))
        elif line.strip() and not line.strip().startswith("-") and ch:
            break
    return ch


def win_block(wid):
    wins = sk.tgui_windows(all=True).text or ""
    for m in re.finditer(r"(  (tgui-window-%s):\n(?:(?:    [^\n]*)\n)+)"
                         % re.escape(wid), wins):
        return m.group(1)
    return ""


# ---- find + open
tid, txy, tname = find_timer()
if not tid:
    RESULT = {"ok": False, "note": "no cell door timer found by name"}
else:
    out["timer"] = {"id": tid, "pos": txy, "name": tname}
    empty_active_hand()
    if txy:
        g = bot.goto(x=txy[0], y=txy[1], max_steps=60)
        out["walk"] = "arrived" in (g.text or "")
    c = sk.click(object_id=tid)
    time.sleep(1.8)
    wins = sk.tgui_windows(all=True).text or ""
    wid = None
    for m in re.finditer(r"(  (tgui-window-\d+):\n(?:(?:    [^\n]*)\n)+)",
                         wins):
        if "BrigTimer" in m.group(1) and "closed: true" not in m.group(1):
            wid = m.group(2)
            out["window"] = [l.strip()[:110] for l in m.group(1).split("\n")][
                :6]
    if not wid:
        RESULT = {"ok": False, "note": "BrigTimer tgui did not open",
                  "click": (c.text or "")[:200]}
    else:
        out["wid"] = wid

        def cell_occupied():
            if not txy:
                return False
            my_name = _my_name()
            found = []
            for dx in (-1, 0, 1):
                for dy in (1, 2, 3):
                    t = sk.tile(txy[0] + dx, txy[1] - dy, all=True).text or ""
                    for l in t.split("\n"):
                        m = re.match(r"- mob (\d+) \"([^\"]*)\"", l.strip())
                        if m and m.group(2) != my_name:
                            found.append("%s (%d,%d)" % (m.group(2),
                                                         txy[0] + dx,
                                                         txy[1] - dy))
            return found

        def timing_of(ch):
            return ch and ch.get("timing") and ch["timing"]

        if mode == "status":
            e = sk.examine(object_id=tid).text or ""
            out["examine"] = e[:250]
            out["ok"] = bool(out.get("window"))
        elif mode == "preset":
            a = sk.tgui_act(id=wid, action="preset",
                            params={"preset": opts.get("preset") or "short"})
            time.sleep(1.5)
            ch = act_changes(a)
            out["changes"] = ch
            out["ok"] = bool(ch and "minutes" in ch)
            if not out["ok"]:
                out["verdict"].append("preset did not change the minutes - "
                                      "see the act text")
        elif mode == "time":
            a = sk.tgui_act(id=wid, action="time",
                            params={"adjust": opts.get("adjust") or 600})
            time.sleep(1.5)
            ch = act_changes(a)
            out["changes"] = ch
            out["ok"] = bool(ch and ("minutes" in ch or "seconds" in ch))
        elif mode == "start":
            occ = cell_occupied()
            out["cell_occupied"] = occ
            if occ and not opts.get("force"):
                out["verdict"].append("REFUSED: someone in the cell zone: "
                                      "%s - use force=true only when this "
                                      "is the prisoner you are jailing"
                                      % ", ".join(occ))
                out["ok"] = False
            else:
                a = sk.tgui_act(id=wid, action="start")
                time.sleep(1.6)
                ch = act_changes(a)
                out["changes"] = ch
                out["ok"] = bool(timing_of(ch) and ch["timing"][1] == "1")
        elif mode == "stop":
            a = sk.tgui_act(id=wid, action="stop")
            time.sleep(1.6)
            ch = act_changes(a)
            out["changes"] = ch
            out["ok"] = bool(timing_of(ch) and ch["timing"][1] == "0") or \
                bool(ch and "timing" not in ch)
            if not out["ok"]:
                out["verdict"].append("timer did not stop - see changes")
        elif mode == "flash":
            a = sk.tgui_act(id=wid, action="flash")
            time.sleep(1.2)
            out["act"] = (a.text or "")[:250]
            out["ok"] = True
        elif mode == "cycle":
            occ = cell_occupied()
            out["cell_occupied"] = occ
            if occ and not opts.get("force"):
                out["verdict"].append("REFUSED: someone in the cell zone: "
                                      "%s" % ", ".join(occ))
                out["ok"] = False
            else:
                a0 = sk.tgui_act(id=wid, action="stop")
                time.sleep(1.6)
                a1 = sk.tgui_act(id=wid, action="preset",
                                 params={"preset": opts.get("preset") or
                                         "short"})
                time.sleep(1.5)
                a2 = sk.tgui_act(id=wid, action="start")
                time.sleep(2.0)
                a3 = sk.tgui_act(id=wid, action="flash")
                time.sleep(1.4)
                a4 = sk.tgui_act(id=wid, action="stop")
                time.sleep(1.8)
                ch1, ch2, ch4 = act_changes(a1), act_changes(a2), \
                    act_changes(a4)
                out["preset_changes"] = ch1
                out["start_changes"] = ch2
                out["stop_changes"] = ch4
                started = bool(timing_of(ch2) and ch2["timing"][1] == "1")
                stopped = bool((timing_of(ch4) and ch4["timing"][1] == "0")
                               or (ch4 is not None and "timing" not in ch4
                                   and ch4))
                presetted = bool(ch1 and "minutes" in ch1)
                out["ok"] = started and stopped and presetted
                out["verdict"].append("round-trip: preset=%s start=%s "
                                      "flash=act-sent stop=%s"
                                      % (presetted, started, stopped))
                if not stopped:
                    out["verdict"].append("WARNING: timer still running - "
                                          "stop it by hand or mode=stop")
        else:
            out["verdict"].append("unknown mode %r" % mode)
            out["ok"] = False

RESULT = out
RESULT.setdefault("ok", True)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
