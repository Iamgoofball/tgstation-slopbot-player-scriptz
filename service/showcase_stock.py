# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Stock the drink showcase from a vending machine (Bartender routine).

Vends bottles from a vendor, carries each to the showcase and racks it.
All refs are looked up AT RUNTIME from the open Vending window's product
list - never hard-code ids or refs (they change every round).

Run: run_script {script: ".../service/showcase_stock.py",
                 args: {"vendor": "Booze-O-Mat", "showcase": "drink showcase",
                        "count": 6}}
Optional args: {"items": ["Griffeater gin", ...]} to stock named products
(falls back to the first `count` products). One script run, one compact
dict back: {ok, stocked, skipped, now, rev}.
"""
import re, time
opts = args or {}
vendor_name = opts.get("vendor") or "Booze-O-Mat"
showcase_name = opts.get("showcase") or "drink showcase"
count = int(opts.get("count") or 6)
items = opts.get("items") or []
out = {"ok": True, "stocked": [], "skipped": []}


def _find(name, query=None):
    """First '- obj N "name..."' match in view (search fallback)."""
    s = sk.search(query=query or name, in_view=True).text or ""
    m = re.search(r'- obj (\d+) "([^"]*' + re.escape(name) + r'[^"]*)"', s)
    return (int(m.group(1)), m.group(2)) if m else (None, None)


def _hand_item():
    """Name of the item in the ACTIVE hand, or None if empty."""
    inv = (sk.inventory().text or "")
    act = [l for l in inv.split("\n") if "active_hand" in l]
    if act and "empty" in act[0]:
        return None
    m = re.search(r'obj (\d+) "([^"]+)"', act[0]) if act else None
    return m.group(2) if m else "unknown"


def _swap_to_empty():
    """Swap hands (X) if the active hand is occupied; True if empty after."""
    if _hand_item() is not None:
        sk.key(key="X"); time.sleep(0.6)
    return _hand_item() is None


# ---- open the vendor (walk adjacent first: interaction range ~1 tile) ----
vid, vname = _find(vendor_name)
if not vid:
    raise RuntimeError("vendor not found in view: " + vendor_name)
vp = re.search(r'at (\d+),(\d+)', (sk.search(query=vendor_name, in_view=True).text or ""))
if vp:
    bot.goto(x=int(vp.group(1)) + 1, y=int(vp.group(2)))
    time.sleep(0.5)
c = sk.click(object_id=vid, expect_name=vendor_name)
time.sleep(2.0)

# ---- find the vendor's Vending window and its product refs ----
wid = None
wins = (sk.tgui_windows().text or "")
for m in re.finditer(r"(tgui-window-\d+):", wins):
    wtxt = (sk.tgui_window(id=m.group(1)).text or "")
    if "interface: Vending" in wtxt and vendor_name in wtxt:
        wid = m.group(1); wtxt_all = wtxt; break
if not wid:
    raise RuntimeError("no Vending window opened for " + vendor_name)
products = re.findall(
    r'- ([^:\n]+): \d+ cr.*?-> vend \{"ref": "(\[0x[0-9a-f]+\])"', wtxt_all)
if items:
    chosen = [(n, r) for (n, r) in products if any(i.lower() in n.lower() for i in items)]
else:
    chosen = products[:count]
out["products_seen"] = len(products)
out["chosen"] = [n.strip() for n, _ in chosen][:count]

# ---- showcase id (walk to it each trip) ----
sid, sname = _find(showcase_name)
if not sid:
    raise RuntimeError("showcase not found in view: " + showcase_name)
sp = re.search(r'at (\d+),(\d+)', (sk.search(query=showcase_name, in_view=True).text or ""))

for name, ref in chosen:
    name = name.strip()
    if not _swap_to_empty():
        out["skipped"].append({"item": name, "why": "both hands full"})
        continue
    a = sk.tgui_act(id=wid, action="vend", params={"premium": False, "ref": ref})
    time.sleep(1.2)
    # vend drops the bottle into an EMPTY active hand; only pick it off the
    # floor if it somehow landed there instead (occupied-hand fallback)
    if _hand_item() is None:
        bid, bname = _find(name)
        if not bid:
            out["skipped"].append({"item": name, "why": (a.text or "")[:80]})
            continue
        sk.click(object_id=bid, expect_name=bname[:40]); time.sleep(0.8)
    if sp:
        bot.goto(x=int(sp.group(1)), y=int(sp.group(2))); time.sleep(0.4)
    sid2, _ = _find(showcase_name)   # re-find: ids can shift after walks
    sk.click(object_id=sid2 or sid, expect_name=showcase_name); time.sleep(0.8)
    if _hand_item() is None:
        out["stocked"].append(name)
    else:
        out["skipped"].append({"item": name, "why": "still in hand"})
    bot.goto(x=int(vp.group(1)) + 1, y=int(vp.group(2))); time.sleep(0.3)
    watch("showcase_stock")

try:
    sk.tgui_send(id=wid, type="close")
except Exception:
    pass

now = sk.status()
RESULT = dict(out, now=(now.get("you") or "")[:80], rev=now.rev)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
