# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Pull (grab) a thing so it follows you: the shift+right-click context menu's
"Pull" verb. The SDK can't click Dream Seeker's popup menu, so the script
invokes the same verb: `Pull` on the command line, then answers the target
prompt with the thing's "name (obj id)" choice from oview(1) — you must stand
adjacent first. Walking then drags the pulled thing along (it trails on your
previous tile); bumping into it pushes it.

Run: run_script {script: ".../engineering/pull.py",
                 args: {"id": 38315}}                 # start pulling
                 args: {"id": 38315, "release": true} # stop pulling
Optional: {"walk": [x, y]} to walk there while pulled. Returns {pulled|released,
pos}. Note: ctrl+click does NOT pull here (this fork uses ctrl+click to toggle
machines); the HUD "stop pulling" button (state=pull) also releases.
"""
import re
opts = args or {}
oid = opts.get("id")
if not oid:
    raise ValueError("args: {'id': obj_id, 'release'?: bool, 'walk'?: [x, y]}")
out = {"id": oid}
if opts.get("release"):
    # click the HUD "stop pulling" button if present, else re-run Pull verb cancels by re-pull? Use HUD.
    cur = None
    btn = None
    for i in range(6):
        a = sk.screen(all=True, cursor=cur).text or ""
        m = re.search(r"next_cursor (\S+)", a)
        b = re.search(r'- obj (\d+) "stop pulling" at', a)
        if b:
            btn = int(b.group(1)); break
        cur = m.group(1) if m else None
        if not cur:
            break
    out["button"] = btn
    if btn:
        sk.click(object_id=btn, expect_name="stop pulling")
        time.sleep(0.4)
    out["released"] = True
else:
    ins = (sk.inspect(oid).text or "")
    mpos = re.search(r"at (\d+),(\d+),(\d+)", ins)
    if mpos:
        x, y = int(mpos.group(1)), int(mpos.group(2))
        # stand adjacent (prefer south of it)
        w = bot.goto(x=x, y=y - 1) if opts.get("from") in (None, "south") else None
        if w is None or "arrived" not in (w.text or ""):
            for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                if "arrived" in (bot.goto(x=x + dx, y=y + dy).text or ""):
                    break
        time.sleep(0.3)
    c = sk.command("Pull")
    time.sleep(0.6)
    t = c.text or ""
    m = re.search(r"prompt (\d+):", t)
    if not m:
        raise SystemExit("no Pull prompt: " + t[:150])
    choices = re.findall(r"- ([^\n(]+) \(obj %d\)" % oid, t)
    if not choices:
        raise SystemExit("obj %d not in oview(1) choices: stand adjacent" % oid)
    a = sk.answer_prompt(id=int(m.group(1)), value=choices[0])
    time.sleep(0.5)
    out["pulled"] = ("Pull obj %d" % oid) in (a.text or "")
    if "pulling" not in (a.text or "").lower():
        out["answer"] = (a.text or "")[:150]
if opts.get("walk"):
    w = bot.goto(x=opts["walk"][0], y=opts["walk"][1])
    time.sleep(0.5)
    out["walk"] = (w.text or "")[:80]
# SAFETY WATCHDOG (README section 1): check chat/status after moving things
DANGER = (r"delaminat|integrity|countdown|blast|explod|flood|fire|electroc|shock|causality|warning|emergency")
ch = re.sub(r"<[^>]+>", " ", sk.read_chat(wait_s=1).text or "")
hits = re.findall(r"[^\n]{0,60}(?:%s)[^\n]{0,60}" % DANGER, ch, re.I)
if hits:
    out["DANGER"] = hits[-2:]
# where is it now?
s = sk.search(query="", in_view=True).text or ""
for l in s.split("\n"):
    if re.match(r"- obj %d " % oid, l):
        out["pos"] = l[:130]
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
