"""ONE-CALL situational check: recent chat, your status, what's around you,
AND anything anyone SAID (radio or local) — parsed into `heard` entries so you
can respond and take the info in. Call between actions (one cheap envelope) —
after every script, before entering a room, when anything unexpected happens.
It is how you notice attacks, delams, floods, fires, people talking to you,
and instructions BEFORE they cost you.

Run: run_script {script: ".../common/check.py",
                 args: {"chat": 10, "around": 14}}
Returns {chat_tail, heard, needs_response, you, around, danger_words}.
- `heard`: [{who, verb, text, channel, mine}] — every line where someone
  said/asked/exclaimed/whispered/announced something, mine flagged.
- `needs_response`: lines where someone seems to address you (your name, your
  job, or a question) — ANSWER these on the radio before the next action.
Bigger `chat`/`around` when suspicious. Never act blind: if anything here
surprises you, stop and investigate before the next world-affecting script.
"""
import re
opts = args or {}
nchat = opts.get("chat") or 10
naround = opts.get("around") or 14
out = {}

# ---- chat tail (raw) ----
ch = (sk.read_chat(wait_s=1, limit=max(20, nchat * 3)).text or "")
out["chat_tail"] = [l[:150] for l in ch.split("\n") if l.strip()][-nchat:]

# ---- own name (never hard-code): from the status "you:" line ----
st = (sk.status().text or "")
m = re.search(r"you: mob \d+ \"([^\"]+)\"", st)
my_name = m.group(1) if m else None
out["you"] = m.group(0) if m else st[:200]

# ---- heard: everything anyone said, radio or local ----
# chat lines look like: "- [hh:mm:ss] [Common] Bob says, \"hello\" {radio} [by mob 12]"
# or "- [hh:mm:ss] [Engineering] Spodoptera Pastellina flutters, \"...\" {engradio}"
# Say verbs are species-specific (says/flutters/beeps/chirps/...) — so we match
# ANY "<who> <word>, \"<text>\"" shape and keep the verb as captured.
SAY_RE = re.compile(
    r"^\s*-\s*(?:\[\d+:\d+:\d+\]\s*)?(?:\[([^\]]+)\]\s*)?"     # channel tag
    r"(.{2,60}?)\s([\w']+),\s*"                                # who + verb (any word)
    r"\"(.*?)\"(?:\s*\{(\w+)\})?", re.S)
heard = []
for line in ch.split("\n"):
    line = line.strip()
    if not line or '"' not in line:
        continue
    m = SAY_RE.match(line)
    if not m:
        # fallback: just capture raw
        heard.append({"raw": line[:140], "mine": False})
        continue
    tag, who, verb, text, chan = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5) or ""
    who = who.strip()
    mine = bool(my_name and re.search(r"\b%s\b" % re.escape(my_name), who))
    heard.append({"who": who[:40], "verb": verb, "text": text[:140],
                  "channel": (tag or chan)[:16], "mine": mine})
out["heard"] = heard[-nchat:]

# ---- needs response: addressed at me, my job/role words, or a question ----
need = []
role_words = r"engineer|officer|doctor|assistant|captain|miner|scientist|crew|anyone"
my_first = my_name.split()[0].lower() if my_name else None
for h in out["heard"]:
    if h.get("mine"):
        continue
    blob = (h.get("who", "") + " " + h.get("text", "")).lower()
    name_hit = bool(my_first and re.search(r"\b%s\b" % re.escape(my_first), blob))
    if ("?" in blob
            or name_hit
            or re.search(role_words, blob)
            or re.search(r"\b(hey|you there|can you|could you|please|need help|"
                         r"stop|wait|get out|come here|help)\b", blob)):
        need.append(h)
out["needs_response"] = need[-5:]

# ---- status line (already read above) ----

# ---- surroundings ----
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
