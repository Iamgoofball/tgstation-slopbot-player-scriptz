# Shared SAFETY PRELUDE — loaded at the top of every scriptz script.
# precheck()   = START-of-script FULL check: parses chat (heard/needs_response)
#                and status into the global _START_SITREP, ABORTS on danger.
# postcheck()  = END-of-script FULL check: ABORTS on danger, returns
#                {"chat_tail", "heard", "needs_response", "danger_words",
#                 "start_heard", "start_needs"} — start_heard is what was heard
#                when the script began (consumed from the buffer by precheck,
#                so the agent never loses speech that arrived mid-envelopes).
# watch(tag)   = mid-script danger check (cheap).
# NOTE: sk.read_chat is INCREMENTAL — every read consumes lines. Both checks
# therefore always parse and RETURN what they read; nothing is silently
# dropped. Read `heard`/`start_heard` in every digest and answer needs_response
# on the radio before the next action.
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
    """Full parse of the chat buffer (whatever is still unread) + status.
    Returns {chat_tail, heard, needs_response, danger_words}."""
    ch = sk.read_chat(wait_s=1, limit=60).text or ""
    st = sk.status().text or ""
    m = re.search(r"you: mob \d+ \"([^\"]+)\"", st)
    my_name = m.group(1) if m else None
    my_first = my_name.split()[0].lower() if my_name else None
    # Say verbs are species-specific (says/flutters/beeps/...): match any
    # "<channel?> <who> <word>, \"<text>\" {tag?}" chat line.
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
            # keep unparsed speech visible so it can NEVER vanish silently
            heard.append({"raw": line[:160], "mine": False, "unparsed": True})
            continue
        who = m.group(2).strip()
        mine = bool(my_name and re.search(r"\b%s\b" % re.escape(my_name), who))
        heard.append({"who": who[:40], "verb": m.group(3), "text": m.group(4)[:160],
                      "channel": (m.group(1) or m.group(5) or "")[:16], "mine": mine})
    need = []
    role_words = r"engineer|officer|doctor|assistant|captain|miner|scientist|crew|anyone"
    for h in heard:
        if h.get("mine"):
            continue
        blob = (str(h.get("who", "")) + " " + str(h.get("text", "")) + " " + str(h.get("raw", ""))).lower()
        name_hit = bool(my_first and re.search(r"\b%s\b" % re.escape(my_first), blob))
        if ("?" in blob or name_hit or re.search(role_words, blob)
                or re.search(r"\b(hey|you there|can you|could you|please|need help|"
                             r"stop|wait|get out|come here|help)\b", blob)):
            need.append(h)
    return {"chat_tail": [l[:130] for l in ch.split("\n") if l.strip()][-6:],
            "heard": heard[-10:], "needs_response": need[-6:],
            "danger_words": sorted(set(re.findall(
                r"delaminat\w*|integrity|countdown|blast|explod\w*|fire|flood|"
                r"electrocut\w*|attack\w*|husk|bomb|causality|warning|emergency|"
                r"toxin|dead|crit", ch, re.I)))[:8]}

_START_SITREP = {"heard": [], "needs_response": []}

def precheck(tag="start"):
    global _START_SITREP
    # parse FIRST (consumes the buffer), then judge danger on the same text
    sr = _sitrep()
    _START_SITREP = sr
    hits = []
    for d in sr["danger_words"]:
        hits.append(d)
    raw = " ".join(str(h.get("text") or h.get("raw") or "") for h in sr["heard"])
    bad = re.findall(r"[^\n]{0,70}(?:%s)[^\n]{0,70}" % DANGER, raw, re.I)
    if bad or _status_bad():
        raise SystemExit("PRECHECK ABORT %s: %s | status: %s"
                         % (tag, bad[-2:], (sk.status().text or "")[:100]))
    return sr

def postcheck(tag="end"):
    """END check: abort on danger, else return end sit-rep + what the start
    check heard (start_heard/start_needs)."""
    sr = _sitrep()
    raw = " ".join(str(h.get("text") or h.get("raw") or "") for h in sr["heard"])
    bad = re.findall(r"[^\n]{0,70}(?:%s)[^\n]{0,70}" % DANGER, raw, re.I)
    if bad or _status_bad():
        raise SystemExit("ENDCHECK ABORT %s: %s | status: %s"
                         % (tag, bad[-2:], (sk.status().text or "")[:100]))
    sr["checked"] = "end"
    sr["start_heard"] = _START_SITREP.get("heard", [])
    sr["start_needs"] = _START_SITREP.get("needs_response", [])
    return sr

def watch(tag=""):
    hits = _danger_hits()
    if hits or _status_bad():
        raise SystemExit("ABORT danger %s: %s | status: %s"
                         % (tag, hits[-2:], (sk.status().text or "")[:100]))
