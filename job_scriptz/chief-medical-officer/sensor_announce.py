# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===
import os as _os
_d = _os.path.dirname(_os.path.abspath(__file__))
exec(open(_os.path.join(_d, '..', '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())
precheck()
"""The CMO shift-start announcement: remind the crew to turn their suit
sensors ON (binary + vitals + tracking), on the Common radio. This is the
CMO's documented bare-minimum task #1 (skill guide section 3).

Run: run_script {script: ".../job_scriptz/chief-medical-officer/sensor_announce.py",
                 args: {"channel"?: "common"|"medical"|"command", "extra"?: text}}
Default channel: common. Say-only script; appends your own line if "extra".
"""
opts = args or {}
channel = (opts.get("channel") or "common").lower()
extra = opts.get("extra")

base = ("Attention crew: please enable your suit sensors — binary, vitals "
        "and tracking. Medical dispatch relies on them to find you when "
        "you are hurt. Thank you, CMO.")
text = base + (" " + extra if extra else "")

r = sk.say(text, channel="radio", radio=channel)
RESULT = {"said": text[:80] + "...", "channel": channel,
          "answer": (r.text or "")[:200]}

# === END CHECK (scriptz: full sit-rep after every script) ===
END_CHECK = postcheck()
{"result": RESULT, "end_check": END_CHECK}
