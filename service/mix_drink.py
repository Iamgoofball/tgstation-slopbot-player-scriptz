# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Mix a drink: hold the container, click each source bottle to pour.

Pouring in tgstation: with the CONTAINER in the active hand, click a reagent
bottle - it pours a fixed dose per click (default 10u). So a recipe is just a
list of {item, clicks}. Sources are found by exact name anywhere (in view or
remembered tiles); bottles stocked inside the drink showcase are NOT visible
to the client - vend them out first (showcase_stock.py) or keep them on the
bar. Contents verified by examining the container afterwards.

Run: run_script {script: ".../service/mix_drink.py",
                 args: {"container": "shaker",
                        "sources": [{"item": "Tunguska triple distilled",
                                     "clicks": 3},
                                    {"item": "orange juice", "clicks": 3}]}}
Optional: {"serve_table": true} sets the container on a table afterwards.
Returns {ok, contents, steps, now, rev}.
"""
import re, time
opts = args or {}
container = opts.get("container") or "shaker"
sources = opts.get("sources") or []
if not sources:
    raise ValueError("args: {'container': 'shaker', 'sources': "
                     "[{'item': 'Griffeater gin', 'clicks': 2}, ...]}")
out = {"ok": True, "steps": []}


def _hand_item():
    inv = (sk.inventory().text or "")
    act = [l for l in inv.split("\n") if "active_hand" in l]
    if act and "empty" in act[0]:
        return None
    m = re.search(r'obj (\d+) "([^"]+)"', act[0]) if act else None
    return m.group(2) if m else "unknown"


def _find_exact(name, in_view=True):
    s = (sk.search(query=name, in_view=in_view).text or "")
    for m in re.finditer(r'- obj (\d+) "([^"]*)"', s):
        if m.group(2) != name:
            continue
        p = re.search(r'at (\d+),(\d+)', s[m.start():])
        return (int(m.group(1)), m.group(2),
                (int(p.group(1)), int(p.group(2))) if p else None)
    return None, None, None


def _held_somewhere(name):
    inv = (sk.inventory().text or "")
    return bool(re.search(r'- obj \d+ "' + re.escape(name) + r'"', inv))


# ---- container in the ACTIVE hand (vend/pickup may have left it in either) ----
if not _held_somewhere(container):
    cid, cname, cpos = _find_exact(container, True)
    if not cid:
        cid, cname, cpos = _find_exact(container, False)
    if not cid:
        raise RuntimeError("container not found: " + container)
    if cpos:
        bot.goto(x=cpos[0], y=cpos[1]); time.sleep(0.4)
    if _hand_item() is not None:
        sk.key(key="X"); time.sleep(0.6)
        if _hand_item() is not None:
            raise RuntimeError("both hands full, cannot pick up " + container)
    cid2, _, _ = _find_exact(container, True) or (cid, cname, cpos)
    sk.click(object_id=(cid2 or cid), expect_name=(cname or container)[:40]); time.sleep(0.8)
if _hand_item() is None or container[:5] not in (_hand_item() or "").lower():
    sk.key(key="X"); time.sleep(0.6)     # bring it to the active hand
if _hand_item() is None or container[:5] not in (_hand_item() or "").lower():
    raise RuntimeError("container not in active hand: holding " + str(_hand_item()))
out["container"] = _hand_item()

# ---- pour each source ----
for src in sources:
    name = (src.get("item") or "").strip()
    clicks = int(src.get("clicks") or 1)
    sid, sname, spos = _find_exact(name, True)
    if not sid:
        sid, sname, spos = _find_exact(name, False)
    if not sid:
        out["steps"].append({"item": name, "ok": False, "why": "bottle not found"})
        out["ok"] = False
        continue
    if spos:
        bot.goto(x=spos[0], y=spos[1]); time.sleep(0.4)   # in view != in reach
        sid, sname, spos = _find_exact(name, True) or (sid, sname, spos)
    if _hand_item() is None or container[:5] not in (_hand_item() or "").lower():
        sk.key(key="X"); time.sleep(0.5)
    if _hand_item() is None or container[:5] not in (_hand_item() or "").lower():
        out["steps"].append({"item": name, "ok": False, "why": "container left active hand"})
        out["ok"] = False
        continue
    done = 0
    for i in range(clicks):
        sid3, _, _ = _find_exact(name, True) or (sid, sname, spos)
        if not sid3:
            break
        sk.click(object_id=sid3, expect_name=None); time.sleep(0.9)
        done += 1
        watch("mix_drink")
    out["steps"].append({"item": name, "ok": done >= clicks,
                         "clicks": done, "wanted": clicks})

# ---- verify by examining the container ----
e = (sk.examine_held().text if hasattr(sk, "examine_held") else None)
if not e:   # examine what the active hand holds: click it? use examine on held id
    inv = (sk.inventory().text or "")
    m = re.search(r'obj (\d+) "' + re.escape(out.get("container", "?")) + '"', inv)
    e = (sk.examine(object_id=int(m.group(1))).text if m else "")
out["contents"] = [l.strip()[:140] for l in (e or "").split("\n")
                   if re.search(r"\d+ units? of|It contains|reagents", l, re.I)][:8]

# ---- optional: set the container on a table ----
if opts.get("serve_table"):
    t = _find_exact(opts.get("table_name") or "table", True)
    if t[0]:
        bot.goto(x=t[2][0], y=t[2][1]); time.sleep(0.4)
        t2 = _find_exact(opts.get("table_name") or "table", True) or t
        sk.click(object_id=t2[0], expect_name=None); time.sleep(0.8)
        out["served"] = _hand_item() is None

now = sk.status()
RESULT = dict(out, now=(now.get("you") or "")[:80], rev=now.rev)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
