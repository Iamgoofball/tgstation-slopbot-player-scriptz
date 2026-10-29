# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Read several machines' tgui state in one envelope (walks to each, opens,
parses the JSON data). With `actions` (per id) it also APPLIES tgui actions and
re-reads the state after.

Run: run_script {script: ".../engineering/ui_batch.py", args: {"ids": [37890],
  "actions": {"37890": [{"action": "power"}, {"action": "pressure", "params": {"pressure": 4500}}]}}
Optional: {"set_states": {id: {"field": "on", "goal": true,
  "act_on": {"action": "power"}, "act_off": {"action": "power"}}}} —
  STATE-CHECKED apply: read field first, act ONLY if it differs from goal
  (toggles are not idempotent — blind acts caused both emitter mistakes),
  then re-read to verify. Entries may instead be {"field","goal","action"}
  for symmetric toggles with params.
Returns {results: {id: {win, data|raw, set_states?, actions?, after?}}, ok}.
Empty active hand!
"""
import json
import re
opts = args or {}
ids = opts.get("ids") or []
actions = opts.get("actions") or {}
if not ids and not actions:
    raise ValueError("args: {'ids': [...], 'actions'?: {id: [{action, params}]}}")

# SAFETY WATCHDOG (see README section 1): abort on danger between machines.
DANGER = (r"delaminat|integrity|countdown|blast|explod|detonat|flood|fire|"
          r"electroc|shock|attack|husk|bomb|causality|warning|emergency|toxin")
def watch(tag=""):
    ch = re.sub(r"<[^>]+>", " ", _pull_chat())
    hits = re.findall(r"[^\n]{0,60}(?:%s)[^\n]{0,60}" % DANGER, ch, re.I)
    if hits:
        raise SystemExit("ABORT danger %s: %s" % (tag, hits[-2:]))

watch("start")
ids = list(dict.fromkeys(list(ids) + [int(k) for k in actions]))
out = {"results": {}}
for oid in ids:
    try:
        bot.goto(object_id=oid, adjacent=True)
        time.sleep(0.3)
        # close stale windows of the same interface first: clicks REUSE an
        # already-open window, so a leftover one would be read instead
        w = [k.strip().rstrip(":") for k in (sk.tgui_windows().text or "").split("\n") if "tgui-window" in k]
        for cand in w:
            try:
                d = sk.tgui_window(id=cand).text or ""
                m0 = re.search(r"interface: (\S+)", d)
                if m0 and (not opts.get("iface") or m0.group(1) == opts["iface"]):
                    sk.tgui_send(id=cand, type="close")
                    time.sleep(0.2)
            except Exception:
                pass
        sk.click(object_id=oid, expect_name=None)
        time.sleep(1.2)
        w = [k.strip().rstrip(":") for k in (sk.tgui_windows().text or "").split("\n") if "tgui-window" in k]
        # after the close-out, the only matching window is this machine's
        win = None
        for cand in w:
            d = sk.tgui_window(id=cand).text or ""
            m0 = re.search(r"interface: (\S+)", d)
            if m0 and (not opts.get("iface") or m0.group(1) == opts["iface"]):
                win = cand
                break
        if not win:
            out["results"][oid] = {"win": None}
            continue
        def read():
            d = sk.tgui_window(id=win).text or ""
            m = re.search(r"state: \|\n(.*?)\nmessages_by_type", d, re.S) or re.search(r"state: \|\n(.*)", d, re.S)
            if not m:
                return {"raw": d[:opts.get("slice", 300)]}
            try:
                j = json.loads(m.group(1))
                data = j.get("data", j)
                if isinstance(data, dict) and "filter_types" in data:   # compress gas tables
                    data = dict(data, filter_types={f["gas_id"]: f["enabled"] for f in data["filter_types"] if f.get("enabled")})
                return {"data": data if isinstance(data, dict) else str(data)[:opts.get("slice", 300)]}
            except Exception as ex:
                return {"parse": str(ex)[:60], "raw": m.group(1)[:opts.get("slice", 300)]}
        rec = {"win": win}
        rec.update(read())
        am = re.search(r"actions: (.*?)action_params_in_data", (sk.tgui_window(id=win).text or ""), re.S)
        rec["actions"] = (am.group(1).strip()[:160] if am else "")
        ss = (opts.get("set_states") or {}).get(str(oid))
        if ss:
            def fget():
                d2 = sk.tgui_window(id=win).text or ""
                m2 = re.search(r'"' + ss["field"] + r'":\s*(1|0|true|false)', d2)
                return (m2.group(1) in ("1", "true")) if m2 else None
            cur = fget()
            goal = bool(ss.get("goal", True))
            rec["set_states"] = {"field": ss["field"], "before": cur,
                                 "acted": (cur is None or cur != goal)}
            if cur is None or cur != goal:
                spec = ss.get("act_on") if goal else ss.get("act_off")
                if spec is None and ss.get("action"):
                    spec = {"action": ss["action"], "params": ss.get("params")}
                if spec:
                    sk.tgui_act(id=win, action=spec["action"], params=spec.get("params") or {})
                    time.sleep(0.8)
            rec["set_states"]["after"] = fget()
            rec["set_states"]["ok"] = (rec["set_states"]["after"] == goal)
        for act in actions.get(str(oid)) or []:
            a = sk.tgui_act(id=win, action=act["action"], params=act.get("params") or {})
            time.sleep(0.6)
        if actions.get(str(oid)):
            rec["after"] = read()
        out["results"][oid] = rec
        watch("after %s" % oid)   # abort remaining machines on danger
    except Exception as ex:
        out["results"][oid] = {"error": str(ex)[:100]}
    finally:
        if 'win' in dir() and win:
            try:
                sk.tgui_send(id=win, type="close")
                time.sleep(0.3)
            except Exception:
                pass
out["ok"] = all(v.get("win") or v.get("error") for v in out["results"].values())
RESULT = (out)

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
