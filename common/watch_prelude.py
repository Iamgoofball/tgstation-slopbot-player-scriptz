# Shared SAFETY PRELUDE — loaded at the top of every scriptz script.
# precheck()   = START-of-script FULL check: chat (parsed) + status, ABORT on danger.
# postcheck()  = END-of-script FULL check: same parse; ABORT on danger; returns
#                {chat_tail, heard, needs_response, danger_words} so the agent
#                sees what anyone said while the script ran.
# watch(tag)   = mid-script check (danger/status only, cheap).
# See scriptz README section 1. Repeated benign danger lines (e.g. the Poly
# parrot quoting old alarms) still abort — abort is cheap, dying is not.
DANGER = (r"delaminat|integrity|countdown|causality|blast|explod|detonat|"
          r"flood|fire alarm|electroc|shock|husk|bomb|toxin|attack|hurt|"
          r"wound|emergency|venerror|crit")

def _status_bad():
    st = sk.status().text or ""
    head = st[:200]
    return ("[ghost]" in head) or bool(re.search(r"\b(dead|crit|unconscious|husk)\b", head, re.I))

def _danger_hits():
    ch = re.sub(r"<[^>]+>", " ", sk.read_chat(wait_s=1).text or "")
    return re.findall(r"[^\n]{0,70}(?:%s)[^\n]{0,70}" % DANGER, ch, re.I)

def _sitrep():
    """The check.py parse: chat tail, heard (anyone said anything, radio or
    local), needs_response (addressed at me / my role / a question)."""
    ch = sk.read_chat(wait_s=1, limit=30).text or ""
    st = sk.status().text or ""
    m = re.search(r"you: mob \d+ \"([^\"]+)\"", st)
    my_name = m.group(1) if m else None
    my_first = my_name.split()[0].lower() if my_name else None
    SAY_RE = re.compile(
        r"^\s*-\s*(?:\[\d+:\d+:\d+\]\s*)?(?:\[([^\]]+)\]\s*)?"
        r"(.{2,60}?)\s([\w']+),\s*"
        r"\"(.*?)\"(?:\s*\{(\w+)\})?", re.S)
    heard = []
    for line in ch.split("\n"):
        line = line.strip()
        if not line or '"' not in line or "," not in line:
            continue
        m = SAY_RE.match(line)
        if not m:
            continue
        who = m.group(2).strip()
        mine = bool(my_name and re.search(r"\b%s\b" % re.escape(my_name), who))
        heard.append({"who": who[:40], "verb": m.group(3), "text": m.group(4)[:140],
                      "channel": (m.group(1) or m.group(5) or "")[:16], "mine": mine})
    need = []
    role_words = r"engineer|officer|doctor|assistant|captain|miner|scientist|crew|anyone"
    for h in heard:
        if h.get("mine"):
            continue
        blob = (h.get("who", "") + " " + h.get("text", "")).lower()
        name_hit = bool(my_first and re.search(r"\b%s\b" % re.escape(my_first), blob))
        if ("?" in blob or name_hit or re.search(role_words, blob)
                or re.search(r"\b(hey|you there|can you|could you|please|need help|"
                             r"stop|wait|get out|come here|help)\b", blob)):
            need.append(h)
    return {"chat_tail": [l[:130] for l in ch.split("\n") if l.strip()][-5:],
            "heard": heard[-6:], "needs_response": need[-4:],
            "danger_words": sorted(set(re.findall(
                r"delaminat\w*|integrity|countdown|blast|explod\w*|fire|flood|"
                r"electrocut\w*|attack\w*|husk|bomb|causality|warning|emergency|"
                r"toxin|dead|crit", ch, re.I)))[:8]}

def precheck(tag="start"):
    hits = _danger_hits()
    if hits or _status_bad():
        raise SystemExit("PRECHECK ABORT %s: %s | status: %s"
                         % (tag, hits[-2:], (sk.status().text or "")[:100]))

def postcheck(tag="end"):
    """END check: same rule as the start — abort on danger, else return the
    sit-rep. Scripts wrap their result with this: {result, end_check}."""
    hits = _danger_hits()
    if hits or _status_bad():
        raise SystemExit("ENDCHECK ABORT %s: %s | status: %s"
                         % (tag, hits[-2:], (sk.status().text or "")[:100]))
    sr = _sitrep()
    sr["checked"] = "end"
    return sr

def watch(tag=""):
    hits = _danger_hits()
    if hits or _status_bad():
        raise SystemExit("ABORT danger %s: %s | status: %s"
                         % (tag, hits[-2:], (sk.status().text or "")[:100]))
