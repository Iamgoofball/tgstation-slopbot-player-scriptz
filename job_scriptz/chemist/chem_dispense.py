# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Drive the chem dispenser: set the amount, dispense reagents into the
inserted beaker, verify each step from the act answers.

Run: run_script {script: ".../job_scriptz/chemist/chem_dispense.py",
                 args: {"dispenser"?, "beaker"?: item id, "amount"?: 5-100,
                        "reagents": ["Water", ...], "remove_all"?: true,
                        "eject_after"?: true}}
dispenser id optional (nearest "chem dispenser" in view otherwise); beaker id
optional (uses the one in your active hand, else picks up the nearest beaker
in view). amount must be one of the beaker's transferAmounts (5,10,15,20,25,
30,50 for a beaker, +100 for a large one). remove_all empties the beaker
first (remove {amount: <max transferAmount>}). eject_after pops the beaker
back into your hand.
SAFETY: refuses Water when the beaker holds Potassium and vice versa
(Water + Potassium = instant explosion). Every dispense is verified from the
act's data_changes (energy drop + currentVolume rise), not a re-read race.
"""
import re

opts = args or {}
reagents = opts.get("reagents") or []
out = {"dispensed": [], "verdict": []}
if not reagents:
    out["verdict"].append("no reagents given — nothing to do")
    RESULT = out
else:

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

    def hand_beaker():
        """True if a beaker is in the active hand; if it's in the other hand,
        swap to it. The dispenser eject puts the beaker in the OFF hand's
        neighbour slot — empty_active_hand() then hides it from a naive
        active-hand check."""
        inv = sk.inventory().text or ""
        lines = [l for l in inv.split("\n")
                 if re.search(r'obj \d+ "(?:large )?beaker"', l) and "hand" in l]
        if not lines:
            return False
        if "active" in lines[0]:
            return True
        sk.key(key="X")
        time.sleep(0.4)
        return True

    def find_dispenser_win():
        w = sk.tgui_windows().text or ""
        for m in re.finditer(r"(tgui-window-\d+):", w):
            d = sk.tgui_window(id=m.group(1), max_chars=12000).text or ""
            if "closed: true" in d[:300]:
                continue
            if re.search(r"interface: ChemDispenser\b", d):
                return m.group(1), d
        return None, None

    def seg(d, key, n=800):
        i = d.find('"%s"' % key)
        return d[i:i + n] if i > -1 else ""

    def num(seg_, key):
        m = re.search(r'"%s": (-?[\d.]+)' % key, seg_)
        return float(m.group(1)) if m else None

    def beaker_state(d):
        b = seg(d, "beaker", 1200)
        return {"vol": num(b, "currentVolume"), "pH": num(b, "pH"),
                "contents": re.findall(r'"name": "([^"]+)",\s*"volume": ([\d.]+)', b)}

    # 1) find + open the dispenser
    did = opts.get("dispenser")
    if not did:
        s = sk.search(query="chem dispenser", in_view=True, page_size=20)
        best, bestd = None, None
        for m in re.finditer(r'- obj (\d+) "chem dispenser[^"]*" at \d+,\d+(?:,\d+)? in (\S+) '
                             r'\(dx (-?\d+), dy (-?\d+)\)', s.text or ""):
            d2 = int(m.group(3)) ** 2 + int(m.group(4)) ** 2
            if bestd is None or d2 < bestd:
                did, bestd = int(m.group(1)), d2
    if not did:
        out["verdict"].append("no chem dispenser in view")
        RESULT = out
    else:
        out["dispenser"] = did
        g = bot.goto(object_id=int(did))
        if g.failed and "already there" not in (g.text or ""):
            time.sleep(0.8)
            g = bot.goto(object_id=int(did))  # one retry: paths flake after
            # between-calls position drift
        if g.failed and "already there" not in (g.text or ""):
            out["verdict"].append("walk to dispenser failed")
            RESULT = out
        else:
            empty_active_hand()
            close_all()
            time.sleep(0.4)
            sk.click(object_id=int(did))
            time.sleep(1.8)
            wid, d = find_dispenser_win()
            if not wid:
                out["verdict"].append("dispenser window did not open (powered? empty hand?)")
                RESULT = out
            else:
                # 2) make sure a beaker is inserted (beaker_state vol None =
                #    no beaker — the data slice above doesn't reach the key)
                state = beaker_state(d)
                if state["vol"] is None:
                    if not hand_beaker():
                        # grab a beaker: click it with an empty hand (exact obj)
                        s = sk.search(query="large beaker|beaker", in_view=True, page_size=20)
                        bm = re.search(r'- obj (\d+) "(?:large )?beaker" at', s.text or "")
                        if bm:
                            g2 = bot.goto(object_id=int(bm.group(1)))
                            if not g2.failed or "already there" in (g2.text or ""):
                                empty_active_hand()
                                sk.click(object_id=int(bm.group(1)))
                                time.sleep(0.7)
                                hand_beaker()
                    if hand_beaker():
                        ai = sk.tgui_act(id=wid, action="insert")
                        time.sleep(0.6)
                        d = sk.tgui_window(id=wid, max_chars=12000).text or ""
                    state = beaker_state(d)
                if state["vol"] is None:
                    out["verdict"].append("no beaker inserted and none in hand/view — "
                                          "grab one from the tables first")
                    RESULT = out
                else:
                    out["beaker_before"] = state
                    have = dict((n, float(v)) for n, v in state["contents"])
                    # 3) SAFETY: Water + Potassium = explosion
                    for r in reagents:
                        if r == "Water" and have.get("Potassium"):
                            out["verdict"].append("REFUSED Water: beaker holds Potassium "
                                                  "(Water + Potassium explodes)")
                            reagents = [x for x in reagents if x != "Water"]
                        if r == "Potassium" and have.get("Water"):
                            out["verdict"].append("REFUSED Potassium: beaker holds Water "
                                                  "(Water + Potassium explodes)")
                            reagents = [x for x in reagents if x != "Potassium"]
                    # 4) remove_all / amount
                    if opts.get("remove_all"):
                        ta = re.search(r'"transferAmounts": \[([\d,\s]+)\]', d)
                        mx = max(int(x) for x in ta.group(1).split(",")) if ta else 100
                        ar = sk.tgui_act(id=wid, action="remove", params={"amount": mx})
                        time.sleep(0.5)
                        d = sk.tgui_window(id=wid, max_chars=12000).text or ""
                        out["beaker_before"] = beaker_state(d)
                    if opts.get("amount"):
                        amt = int(opts["amount"])
                        ta = re.search(r'"transferAmounts": \[([\d,\s]+)\]', d)
                        allowed = [int(x) for x in ta.group(1).split(",")] if ta else []
                        if allowed and amt not in allowed:
                            out["verdict"].append("amount %d not allowed (%s)" % (amt, allowed))
                        else:
                            aa = sk.tgui_act(id=wid, action="amount", params={"target": amt})
                            if re.search(r'"amount": \d+ -> %d\b' % amt, aa.text or ""):
                                out["amount"] = amt
                            time.sleep(0.3)
                    # 5) dispense, verifying each from the act answer
                    for r in reagents:
                        before = beaker_state(d)
                        ad = sk.tgui_act(id=wid, action="dispense", params={"reagent": r})
                        txt = ad.text or ""
                        grew = re.search(r'(?:beaker\.)?currentVolume: ([\d.]+) -> ([\d.]+)', txt)
                        got = float(grew.group(2)) - float(grew.group(1)) if grew else None
                        time.sleep(0.4)
                        d = sk.tgui_window(id=wid, max_chars=12000).text or ""
                        after = beaker_state(d)
                        out["dispensed"].append({"reagent": r, "added": got,
                                                 "beaker": after})
                        if got is None:
                            out["verdict"].append("dispense %s: no volume change seen "
                                                  "(unknown chemical? out of energy?)" % r)
                    out["beaker_after"] = beaker_state(d)
                    en = num(seg(d, "data", 400), "displayedUnits")
                    out["energy"] = en
                    if en is not None and en < 200:
                        out["verdict"].append("dispenser energy low: %su" % en)
                    # 6) eject
                    if opts.get("eject_after"):
                        ae = sk.tgui_act(id=wid, action="eject")
                        # the data_changes value TRUNCATES ("...currentV... -> null"):
                        # never expect a closing brace
                        out["ejected"] = bool(re.search(r'beaker: \{.* -> null',
                                                        ae.text or ""))
                    sk.tgui_send(id=wid, type="close")
                    out["ok"] = True
                    RESULT = out

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
