"""One-off: apply BOTH patches to every scriptz script (idempotent):
1. SAFETY PRECHECK header (loads common/watch_prelude.py, calls precheck()).
2. END CHECK: wrap the final top-level Expr as RESULT = (...) and append the
   end block so every script returns {result, end_check} and runs postcheck().
Run from repo root: python _apply_checks.py
"""
import ast, os

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP = {"check.py", "watch_prelude.py", "_apply_checks.py"}
HEADER = (
    "# === SAFETY PRECHECK (scriptz README section 1): abort on danger before anything ===\n"
    "import os as _os\n"
    "_d = _os.path.dirname(_os.path.abspath(__file__))\n"
    "exec(open(_os.path.join(_d, '..', 'common', 'watch_prelude.py'), encoding='utf-8').read())\n"
    "precheck()\n")
END_BLOCK = (
    "\n# === END CHECK (scriptz: full sit-rep after every script) ===\n"
    "END_CHECK = postcheck()\n"
    '{"result": RESULT, "end_check": END_CHECK}\n')

def wrap_final_expr(text):
    tree = ast.parse(text)
    last = tree.body[-1]
    if not isinstance(last, ast.Expr):
        return text  # ends with assignment/statement: keep as-is
    lines = text.split("\n")
    start, end = last.lineno - 1, last.end_lineno
    block = lines[start:end]
    block[0] = "RESULT = (" + block[0]
    block[-1] = block[-1] + ")"
    return "\n".join(lines[:start] + block + lines[end:]).rstrip("\n") + "\n"

changed = []
for dirpath, _, files in os.walk(ROOT):
    if "__pycache__" in dirpath:
        continue
    for fn in sorted(files):
        if not fn.endswith(".py") or fn in SKIP:
            continue
        p = os.path.join(dirpath, fn)
        with open(p, encoding="utf-8") as f:
            text = f.read()
        has_header = "SAFETY PRECHECK" in text
        has_end = "END CHECK" in text
        if has_header and has_end:
            continue
        body = text
        if not has_header:
            body = HEADER + body
        if not has_end:
            body = wrap_final_expr(body)
            # does the final statement return a value? if it ended in an
            # assignment the runner returns None anyway; keep END block uniform
            body += END_BLOCK
        ast.parse(body)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        changed.append((os.path.relpath(p, ROOT), "hdr" if not has_header else "",
                        "end" if not has_end else ""))
for c in changed:
    print(*c)
print("total: %d" % len(changed))
