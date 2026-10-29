"""(Re)load the station map so paths over unseen tiles can be planned.

Run: run_script {script: ".../setup/load_map.py",
                 args: {"map_path": "F:/-tg-station/_maps/map_files/MetaStation/MetaStation.dmm"}}
Needed after every MCP reboot (the client forgets the map)."""
opts = args or {}
p = opts.get("map_path") or "F:/-tg-station/_maps/map_files/MetaStation/MetaStation.dmm"
lm = sk.load_map(p)
t = (lm.text or "")
st = sk.status()
{"ok": "loaded" in t.lower(), "you": (st.get("you") or "")[:80], "rev": st.rev}
