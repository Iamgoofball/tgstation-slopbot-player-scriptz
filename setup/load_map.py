# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""(Re)load the station map so paths over unseen tiles can be planned.

Run: run_script {script: ".../setup/load_map.py",
                 args: {"map_path": "F:/-tg-station/_maps/map_files/MetaStation/MetaStation.dmm"}}
Needed after every MCP reboot (the client forgets the map)."""
opts = args or {}
p = opts.get("map_path") or "F:/-tg-station/_maps/map_files/MetaStation/MetaStation.dmm"
lm = sk.load_map(p)
t = (lm.text or "")
st = sk.status()
RESULT = ({"ok": "loaded" in t.lower(), "you": (st.get("you") or "")[:80], "rev": st.rev})

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
