"""ONE-CALL situational check: recent chat, your status, and what's around you.
Call this between actions (it costs one cheap envelope) — vitally: after every
script, before entering a room, when anything unexpected happens. It is how you
notice attacks, delams, floods, fires, people shouting at you, and opportunities
BEFORE they cost you.

Run: run_script {script: ".../common/check.py",
                 args: {"chat": 8, "around": 14}}
Returns {chat_tail, you, around} — compact; call with bigger `chat`/`around`
when suspicious. Never act blind: if anything here surprises you, stop and
investigate before the next world-affecting script.
"""
import re
opts = args or {}
nchat = opts.get("chat") or 8
naround = opts.get("around") or 14
out = {}
ch = (sk.read_chat(wait_s=1, limit=nchat * 3).text or "")
out["chat_tail"] = [l[:150] for l in ch.split("\n") if l.strip()][-nchat:]
st = (sk.status().text or "")
m = re.search(r"you: .*", st)
out["you"] = (m.group(0) if m else st[:200])
s = sk.search(query="", in_view=True).text or ""
items = []
for l in s.split("\n"):
    mm = re.match(r"- (?:obj|mob) \d+ \"[^\"]+\" at (\d+,\d+,\d+) in ([^(]+)", l)
    if mm:
        items.append(l[:130])
out["around"] = items[-naround:]
out["danger_words"] = sorted(set(re.findall(
    r"delaminat\w*|integrity|countdown|blast|explod\w*|fire|flood|electrocut\w*|"
    r"attack\w*|husk|bomb|causality|warning|emergency|toxin|dead|crit",
    ch, re.I)))[:8]
out
