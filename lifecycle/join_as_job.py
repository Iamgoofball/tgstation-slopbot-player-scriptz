"""Join the round as a job (lobby join -> job menu -> select_job).

Run: run_script {script: ".../lifecycle/join_as_job.py", args: {"job": "Medical Doctor"}}
Verify with the returned line: late-joiners spawn buckled into an Arrival Shuttle seat."""
import re
job = (args or {}).get("job") or ValueError("args: {'job': 'Medical Doctor'}")
j = sk.lobby(action="join")
m = re.search(r"tgui-window-\d+", j.text or "")
out = {"menu": bool(m), "job": job}
if m:
    a = sk.tgui_act(id=m.group(0), action="select_job", params={"job": job})
    t = (a.text or "")
    out["spawned"] = "mob_changed" in t
    out["buckled"] = "buckled" in t.lower()
time.sleep(1.0)
out["you"] = (sk.status().get("you") or "")[:90]
out["ok"] = out.get("spawned", False)
out
