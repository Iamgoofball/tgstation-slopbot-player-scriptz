# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Survey machines around one or more spots: walks to each (x, y), pages
through the in-view search, and returns the filtered machinery list (id, name,
tile, area, state). The agent reads this once per room instead of eyeballing.

Run: run_script {script: ".../engineering/survey_machines.py",
                 args: {"spots": [[166,149],[169,151]]}}
Optional: {"hide": "pipe|cable|grille|window|floor|light|sign|camera|pool",
           "only": "canister|filter|pump|vent|scrubber" (regex filter), "max": 60}.
Returns {machines: [...], n}. Coordinates are map tiles; walk fails on doors
your ID can't open (see the answer's access_note).
"""
import re
opts = args or {}
spots = opts.get("spots") or []
hide = opts.get("hide") or r"pipe|cable|grille|window|floor|light fixture|sign|camera|pool of"
only = opts.get("only")
if not spots:
    raise ValueError("args: {'spots': [[x, y], ...], 'only'?/'hide'?: regex}")
out = {"machines": []}
seen = {}
# SAFETY WATCHDOG (README section 1): abort the survey on danger.
DANGER = (r"delaminat|integrity|countdown|blast|explod|flood|fire|electroc|"
          r"shock|attack|husk|bomb|causality|warning|emergency|toxin")
def watch(tag=""):
    ch = re.sub(r"<[^>]+>", " ", sk.read_chat(wait_s=1).text or "")
    hits = re.findall(r"[^\n]{0,60}(?:%s)[^\n]{0,60}" % DANGER, ch, re.I)
    if hits:
        raise SystemExit("ABORT danger %s: %s" % (tag, hits[-2:]))
for x, y in [(int(s[0]), int(s[1])) for s in spots]:
    w = bot.goto(x=x, y=y)
    time.sleep(0.3)
    cur = None
    for page in range(8):                # search is paginated (~30/page)
        a = sk.search(query="", in_view=True, cursor=cur).text or ""
        for l in a.split("\n"):
            m = re.match(r"- obj (\d+) \"([^\"]+)\" at (\d+,\d+,\d+) in (.+?) state=(\S+)", l)
            if not m:
                continue
            oid, name, tile, area, state = int(m.group(1)), m.group(2), m.group(3), m.group(4), m.group(5)
            if re.search(hide, name, re.I):
                continue
            if only and not re.search(only, name, re.I):
                continue
            seen[oid] = (name, tile, area.strip()[:34], state[:34])
        m2 = re.search(r"next_cursor (\S+)", a)
        cur = m2.group(1) if m2 else None
        if not cur:
            break
    watch("%d,%d" % (x, y))   # between spots
out["machines"] = ["obj %d %s @ %s [%s] %s" % (k, v[0], v[1], v[2], v[3])
                   for k, v in sorted(seen.items())][: opts.get("max", 60)]
out["n"] = len(seen)
out["you"] = (sk.status().get("you") or "")[:90]
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
