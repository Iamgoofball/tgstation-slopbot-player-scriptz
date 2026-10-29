# Shared SAFETY PRELUDE — loaded at the top of every scriptz script.
# EVERY chat line this script run consumes is accumulated in _RAW_LOG via
# _pull_chat(); postcheck() parses and returns ALL of it, so speech that
# arrives mid-script (e.g. between machine clicks in ui_batch) is never lost.
# precheck()   = START check: pulls + parses chat, ABORTS on danger.
# postcheck()  = END check: ABORTS on danger, returns
#                {chat_tail, heard, needs_response, danger_words, view: {...},
#                 start_heard, start_needs}.
# watch(tag)   = mid-script danger check (also accumulates chat).
# View checks (the "view census"): chat alone misses NEXT-TILE dangers that
# never reach the log — fires, hostile mobs, hull breaches, gas. Both checks
# scan the ASCII view (areas + mobs + threat objects) and abort/report.
VIEW_THREAT = (r"\bfire\b(?!\s*(?:lock|alarm|axe|extinguisher|sensor|locker))|"
               r"burning plasma|plasma fire|plasma leak|"
               r"fireball|singularity|singulo|\bblob\b|blobbernaut|"
               r"xenomorph|alien (?:hunter|sentinel|drone|queen|praetorian)|"
               r"slime(?! ?extract)|screech|carp(?! ?bag)|"
               r"hole|breach|tesla(?! ?coil)|revanant|revenant")
# mobs that threaten: named mobs nearby (crowd/antagonist awareness)
VIEW_AREA_SKIP = ()   # no area name is itself a threat

def _view_census():
    """ASCII view census via sk.look() (the MCP's text map): areas present,
    other mobs nearby, threat objects, and the 'covered' line (hurt/damage
    overlays, blindfolds — things Dream Seeker draws OVER the map). Falls
    back to search(query="", in_view=True) if look fails. Used by
    precheck/postcheck so a hazard that never reaches chat is still seen.
    Returns {areas, mobs, threats, overlay}."""
    try:
        s = (sk.look(radius=7, max_things=40).text or "")
    except Exception:
        try:
            s = (sk.search(query="", in_view=True).text or "")
        except Exception as ex:
            return {"error": str(ex)[:60]}
    lines = [l for l in s.split("\n") if "- obj" in l or "- mob" in l]
    areas = sorted(set(re.search(r"area \"([^\"]+)\"", l).group(1).strip()
                       for l in lines if " in area " in l))
    if not areas:
        m = re.search(r"areas: (.+)", s)
        if m:  # look's "areas:" summary line (nearest first)
            areas = [a.strip().split(" (")[0]
                     for a in m.group(1).split(";") if a.strip()]
    mobs = [m.groups() for l in lines for m in
            [re.search(r"- mob (\d+) \"([^\"]+)\" at (\d+,\d+)", l)] if m]
    threats = [l[:110] for l in lines if re.search(VIEW_THREAT, l, re.I)][:6]
    st = (sk.status().text or "")
    me = re.search(r"you: mob (\d+)", st)
    me_id = me.group(1) if me else None
    cov = re.search(r"covered: (.+)", s)
    out = {"areas": areas[:10],
           "mobs": [{"id": m[0], "name": m[1][:40], "pos": m[2]}
                    for m in mobs if m[0] != me_id][:8],
           "threats": threats}
    if cov:
        out["overlay"] = cov.group(1)[:140]   # e.g. hurt red overlay, blindfold
    return out

DANGER = (r"delaminat|integrity|countdown|causality|blast|explod|detonat|"
          r"flood|fire alarm|electroc|shock|husk|bomb|toxin|attack|hurt|"
          r"wound|emergency|venerror|crit")

_RAW_LOG = []   # every chat line consumed by THIS script run (deduped)

def _pull_chat(wait_s=1):
    """THE only way scripts read chat: consume + ACCUMULATE so nothing is lost.
    Legacy direct sk.read_chat calls silently ate speech mid-script — that is
    how radio messages vanished. postcheck() parses _RAW_LOG and surfaces all
    of it."""
    ch = sk.read_chat(wait_s=wait_s, limit=60).text or ""
    for l in ch.split("\n"):
        l = l.strip()
        if l and l not in _RAW_LOG:
            _RAW_LOG.append(l)
    return ch

def _status_bad():
    st = sk.status().text or ""
    head = st[:200]
    return ("[ghost]" in head) or bool(re.search(r"\b(dead|crit|unconscious|husk)\b", head, re.I))

def _danger_hits():
    ch = re.sub(r"<[^>]+>", " ", _pull_chat())
    return re.findall(r"[^\n]{0,70}(?:%s)[^\n]{0,70}" % DANGER, ch, re.I)

def _parse_heard(text, my_name, my_first):
    # Say verbs are species-specific (says/flutters/beeps/...): match any
    # "<channel?> <who> <word>, \"<text>\" {tag?}" chat line.
    SAY_RE = re.compile(
        r"^\s*-\s*(?:\[\d+:\d+:\d+\]\s*)?(?:\[([^\]]+)\]\s*)?"
        r"(.{2,60}?)\s([\w']+),\s*"
        r"\"(.*?)\"(?:\s*\{(\w+)\})?", re.S)
    heard = []
    for line in text.split("\n"):
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
    return heard

def _my_name():
    st = sk.status().text or ""
    m = re.search(r"you: mob \d+ \"([^\"]+)\"", st)
    name = m.group(1) if m else None
    first = name.split()[0].lower() if name else None
    return name, first

def _needs(heard, my_first):
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
    return need

def _sitrep():
    """Full parse of EVERYTHING consumed this run + fresh buffer + view."""
    _pull_chat()
    name, first = _my_name()
    ch = "\n".join(_RAW_LOG)
    heard = _parse_heard(ch, name, first)
    # dedupe heard (watch() may re-parse the same lines)
    seen, uniq = set(), []
    for h in heard:
        k = (h.get("who"), h.get("text") or h.get("raw"))
        if k not in seen:
            seen.add(k)
            uniq.append(h)
    sr = {"chat_tail": [l[:130] for l in ch.split("\n") if l.strip()][-6:],
          "heard": uniq[-10:], "needs_response": _needs(uniq, first)[-6:],
          # "emergency" alone is noise ("Emergency Shuttle ..." names/announcements);
          # real emergencies carry a stronger word (delam/countdown/fire/...)
          "danger_words": sorted(set(w for w in re.findall(
              r"delaminat\w*|integrity|countdown|blast|explod\w*|fire|flood|"
              r"electrocut\w*|attack\w*|husk|bomb|causality|warning|emergency|"
              r"toxin|dead|crit", ch, re.I) if w.lower() != "emergency"),
              key=str)[:8],
          "view": _view_census()}
    return sr


def _view_bad(v):
    """Threat objects in the ASCII view (fire/plasma/singulo/...). Normal
    equipment with fire/lock words is excluded by VIEW_THREAT."""
    return v.get("threats") or []

_START_SITREP = {"heard": [], "needs_response": []}

def precheck(tag="start"):
    global _START_SITREP
    sr = _sitrep()
    _START_SITREP = sr
    raw = " ".join(str(h.get("text") or h.get("raw") or "") for h in sr["heard"])
    bad = re.findall(r"[^\n]{0,70}(?:%s)[^\n]{0,70}" % DANGER, raw, re.I)
    vbad = _view_bad(sr.get("view", {}))
    if bad or vbad or _status_bad():
        raise SystemExit("PRECHECK ABORT %s: %s | view: %s | status: %s"
                         % (tag, bad[-2:] or vbad[:2],
                            sr["view"].get("areas", [])[:4],
                            (sk.status().text or "")[:100]))
    return sr

def postcheck(tag="end"):
    """END check: abort on danger, else return end sit-rep + what was heard
    during the whole script (start_heard/start_needs from precheck)."""
    sr = _sitrep()
    raw = " ".join(str(h.get("text") or h.get("raw") or "") for h in sr["heard"])
    bad = re.findall(r"[^\n]{0,70}(?:%s)[^\n]{0,70}" % DANGER, raw, re.I)
    vbad = _view_bad(sr.get("view", {}))
    if bad or vbad or _status_bad():
        raise SystemExit("ENDCHECK ABORT %s: %s | view: %s | status: %s"
                         % (tag, bad[-2:] or vbad[:2],
                            sr["view"].get("areas", [])[:4],
                            (sk.status().text or "")[:100]))
    sr["checked"] = "end"
    sr["start_heard"] = _START_SITREP.get("heard", [])
    sr["start_needs"] = _START_SITREP.get("needs_response", [])
    return sr

def watch(tag=""):
    hits = _danger_hits()
    vb = _view_bad(_view_census())
    if hits or vb or _status_bad():
        raise SystemExit("ABORT danger %s: %s | view: %s | status: %s"
                         % (tag, hits[-2:] or vb[:2], vb[:2],
                            (sk.status().text or "")[:100]))
