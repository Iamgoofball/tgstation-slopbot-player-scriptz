"""Take one item out of an OPEN container UI into a hand, verify, report slot.

Run: run_script {script: ".../inventory/take_from_container.py",
                 args: {"item_id": 186015, "expect_name": "suture", "auto_drop": true}}
Rule of thumb from live runs: the taker needs an EMPTY hand available; the item
lands there and that hand becomes active. If both hands are full and
`auto_drop` is set, the ACTIVE hand's item is dropped first (Q).
"""
opts = args or {}
iid = opts.get("item_id"); iname = opts.get("expect_name")
if iid is None:
    raise ValueError("args: {'item_id': id, 'expect_name': 'name'}")

def hand_items():
    t = (sk.inventory().text or "")
    act, other = [], []
    for l in t.split("\n"):
        if "in slot \"" in l and "hand" in l:
            (act if "handactive" in l else other).append(l.strip()[:90])
    return act, other

act, other = hand_items()
if act and opts.get("auto_drop"):
    sk.key(key="Q")
    time.sleep(0.4)
    act, other = hand_items()
if act:
    raise ValueError(f"active hand not empty ({act[0]}); drop or pass auto_drop=true")

sk.click(object_id=iid, expect_name=iname)
time.sleep(0.5)
act, other = hand_items()
got = [l for l in act + other if str(iid) in l]
{"ok": bool(got), "slot": (got[0] if got else None), "other": other[:1]}
