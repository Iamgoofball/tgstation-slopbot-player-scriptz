# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Print a DNA injector (mutator or activator) from the DNA console.

Run: run_script {script: ".../job_scriptz/geneticist/dna_injector_print.py",
                 args: {"mutref"? | "alias"?, "source"?="occupant",
                        "is_activator"?: 0|1, "discover_all"?: true,
                        "pickup"?: true, "console"?, "x"?, "y"?}}
- mutref: the mutation's ByondRef, e.g. "[0x2100d660]" (read from
  genetics_lab_check / the console UI). OR pass alias/name substring, e.g.
  alias "Monkified" — resolved against storage.occupant/console/disk.
- discover_all: run the console's all_check_discovery first (reveals every
  occupant mutation: name + description; verified live: 7 unknown -> Monkified
  discovered). Without it, only already-discovered mutations can be matched.
- is_activator 0 (default) = MUTATOR injector (applies the mutation when
  injected); 1 = ACTIVATOR ("research") injector (activates dormant copies,
  used for chromosome recycling). Activator cooldown scales with instability.
- pickup: click the fresh injector into your active hand.

Verified live round-trip: print_injector {source: "occupant",
mutref: "[0x2100d660]", is_activator: 0} -> obj "Monkified mutator"
appeared at the console tile, isInjectorReady 1 -> 0.
Guards (console code): injector cooldown (silent), anomalous mutations
(SCANNER_MUTATION_CLASS_OTHER) refuse with a console radio ERROR line.
"""
import re

opts = args or {}
out = {"verdict": []}


def close_all():
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        sk.tgui_send(id=m.group(1), type="close")
        time.sleep(0.12)


def empty_active_hand():
    for _ in range(2):
        inv = sk.inventory().text or ""
        act = [l for l in inv.split("\n") if "active_hand" in l]
        if act and ("empty" in act[0] or "obj" not in act[0]):
            return
        sk.key(key="X")
        time.sleep(0.4)


def nearest(name):
    s = sk.search(query=name, in_view=True, page_size=30)
    best, bestd = None, None
    for m in re.finditer(
            r'- obj (\d+) "%s[^"]*" at \d+,\d+(?:,\d+)? in .+? '
            r'\(dx (-?\d+), dy (-?\d+)\)' % name, s.text or ""):
        d2 = int(m.group(2)) ** 2 + int(m.group(3)) ** 2
        if bestd is None or d2 < bestd:
            best, bestd = int(m.group(1)), d2
    return best


def open_console(console_id):
    g = bot.goto(object_id=console_id)
    if g.failed and "already there" not in (g.text or ""):
        return None, None
    close_all()
    empty_active_hand()
    time.sleep(0.3)
    sk.click(object_id=console_id)
    time.sleep(1.8)
    for m in re.finditer(r"(tgui-window-\d+):", sk.tgui_windows().text or ""):
        d = sk.tgui_window(id=m.group(1), max_chars=14000).text or ""
        if "closed: true" in d[:300]:
            continue
        if re.search(r"interface: DnaConsole\b", d):
            return m.group(1), d
    return None, None


def parse_occupant(d):
    """-> list of mutation entries {alias,name?,ref?,discovered,active}."""
    dd = d[d.find('"data"'):d.find('"data"') + 9000]
    occ = dd[dd.find('"occupant"'):dd.find('"disk"') if dd.find('"disk"') > -1 else len(dd)]
    entries = []
    for chunk in re.split(r'\{\s*"Alias"', occ)[1:]:
        e = {"alias": (re.search(r'"([^"]+)"', chunk) or [None, "?"]).group(1),
             "discovered": re.search(r'"Discovered": 1', chunk) is not None,
             "active": re.search(r'"Active": 1', chunk) is not None}
        nm = re.search(r'"Name": "([^"]+)"', chunk)
        ref = re.search(r'"ByondRef": "([^"]+)"', chunk)
        if nm:
            e["name"] = nm.group(1)
        if ref:
            e["ref"] = ref.group(1)
        entries.append(e)
    return entries


console_id = opts.get("console") and int(opts["console"]) or nearest("DNA Console")
source = opts.get("source") or "occupant"
is_activator = 1 if opts.get("is_activator") in (1, "1", True) else 0
alias = opts.get("alias")
mutref = opts.get("mutref")
out["args"] = {"source": source, "is_activator": is_activator,
               "alias": alias, "mutref": mutref}

if not console_id:
    RESULT = {"ok": False, "note": "no DNA Console in view (walk to Genetics Lab)"}
else:
    wid, data = open_console(console_id)
    if not wid:
        RESULT = {"ok": False, "note": "console window did not open (powered? occupied hand?)"}
    else:
        entries = parse_occupant(data)
        out["occupant_mutations"] = entries

        # ---- optional: discover everything first
        if opts.get("discover_all"):
            und = [e["alias"] for e in entries if not e["discovered"]]
            if und:
                sk.tgui_act(id=wid, action="all_check_discovery")
                time.sleep(2.0)
                d2 = sk.tgui_window(id=wid, max_chars=14000).text or ""
                entries = parse_occupant(d2)
                out["occupant_mutations"] = entries
                out["discovered_now"] = [e["name"] for e in entries
                                         if e["discovered"] and e["alias"] in und]

        # ---- resolve the mutation
        mrow = None
        if mutref:
            mrow = next((e for e in entries if e.get("ref") == mutref), None)
            if not mrow:
                out["verdict"].append("mutref %s not in storage.occupant — re-read the console"
                                      % mutref)
        elif alias:
            hits = [e for e in entries
                    if alias.lower() in (e.get("name") or e.get("alias") or "").lower()]
            if not hits:
                out["verdict"].append("no occupant mutation matches alias %r — try discover_all" % alias)
            elif len(hits) > 1:
                out["verdict"].append("alias %r is ambiguous: %s" % (alias, [e.get("name") for e in hits]))
            else:
                mrow = hits[0]
        else:
            out["verdict"].append("pass mutref or alias (see genetics_lab_check for refs)")

        if not mrow:
            sk.tgui_send(id=wid, type="close")
            RESULT = out
            out["ok"] = False
        elif not mrow.get("ref"):
            sk.tgui_send(id=wid, type="close")
            out["ok"] = False
            out["verdict"].append("matched %s but it has no ByondRef (not discovered?)" % mrow["alias"])
        else:
            # ---- print it
            a = sk.tgui_act(id=wid, action="print_injector",
                            params={"source": source, "mutref": mrow["ref"],
                                    "is_activator": str(is_activator)})
            out["act"] = (a.text or "")[:200]
            time.sleep(2.2)
            d3 = sk.tgui_window(id=wid, max_chars=9000).text or ""
            ready = re.search(r'"isInjectorReady": ([0-9])', d3)
            out["injector_ready_after"] = ready and ready.group(1)
            printed = out["injector_ready_after"] == "0" or "isInjectorReady: 1 -> 0" in (a.text or "")
            if not printed:
                out["verdict"].append("print REFUSED (isInjectorReady stayed 1): cooldown or "
                                      "anomalous mutation — wait and re-run")
            sk.tgui_send(id=wid, type="close")

            # ---- find the fresh injector on the floor near the console
            # search matches on name OR icon_state ("Monkified mutator" carries
            # a 'matched on its icon_state "dnainjector"' note); newest id wins.
            best = None
            if printed:
                time.sleep(0.6)
                s = sk.search(query="injector", in_view=True, page_size=10)
                for line in (s.text or "").split("\n"):
                    if "injector" not in line.lower():
                        continue
                    m = re.search(r'- obj (\d+) "([^"]*)" at (\d+),(\d+)', line)
                    if not m:
                        continue
                    oid = int(m.group(1))
                    if best is None or oid > best["id"]:
                        best = {"id": oid, "name": m.group(2),
                                "tile": "%s,%s" % (m.group(3), m.group(4))}
            out["injector"] = best
            out["ok"] = bool(best)
            if not best:
                out["verdict"].append("no fresh injector seen near the console")
            elif opts.get("pickup"):
                sk.click(object_id=best["id"])
                time.sleep(0.9)
                inv = sk.inventory().text or ""
                got = [l.strip() for l in inv.split("\n") if "active_hand" in l and "obj" in l]
                out["picked_up"] = bool(got)
                if got:
                    out["picked_what"] = got[0][:80]

if "RESULT" not in dir():
    RESULT = out  # normal path: report the accumulated out dict
RESULT.setdefault("ok", True)
# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
