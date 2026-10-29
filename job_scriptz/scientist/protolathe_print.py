# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""Protolathe front-end: delegates to the generic Fabricator driver
(machines/fabricator_control.py) with the Science department protolathe as
the default machine. The circuit imprinter and every department techfab use
the SAME driver - pass args.machine = "circuit imprinter" / "techfab".

Run: run_script {script: ".../job_scriptz/scientist/protolathe_print.py",
                 args: {"mode": "status"|"list"|"build"|"insert"|"eject",
                        "design"?: "screwdriver", "amount"?: 1, "wait"?: true,
                        "sheet"?: <id> or "sheet_name"?: "glass",
                        "machine"?: "department protolathe",   # default
                        "pattern"?: "capacitor"}}
Defaults: mode "build" needs args.design; design resolves by name/path
substring against the protolathe's 66 designs (e.g. "screwdriver",
"experi_scanner", "basic_capacitor"). See machines/fabricator_control.py
for the full arg set and the live-verified facts (ore silo, empty active
hand, prints ejecting onto the machine tile or a neighbor).
"""
opts = dict(args or {})
opts.setdefault("machine", "department protolathe")
if opts.get("mode") is None and opts.get("design"):
    opts["mode"] = "build"
args = opts
exec(open(_os.path.join(_d, "..", "..", "machines",
                        "fabricator_control.py"), encoding="utf-8").read())
{"result": RESULT, "end_check": END_CHECK}
