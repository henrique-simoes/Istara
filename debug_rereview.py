import json
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent
pi_replacement_root = repo_root.with_name(f"{repo_root.name}-pi-replacement")
sys.path.insert(0, str(Path.home() / "Documents/Skills/build-stream-conductor/scripts"))
import conductor  # noqa: E402

tasks_json = subprocess.check_output(
    ["compass-forge", "task", "list", "--target", str(pi_replacement_root)]
).decode()
data = json.loads(tasks_json)
tasks = data if isinstance(data, list) else data.get("tasks", [])

cast = {"pipeline_run": "pi-eval", "reviewers": ["pi-eval-code-reviewer"], "stages": [
    {"name": "plan", "role": "pi-eval-architect-c"},
    {"name": "implement", "role": "pi-eval-implementer"},
    {"name": "code-review", "role": "pi-eval-code-reviewer"},
    {"name": "fix", "role": "pi-eval-fixer"}
]}

print("rroles:", conductor.reviewer_roles(cast))
print("pipeline_run:", cast.get("pipeline_run"))
rroles = conductor.reviewer_roles(cast)
pipeline_run = str(cast.get("pipeline_run") or "")

pending_roles = {(t.get("owner_role") or "") for t in tasks
                     if (t.get("owner_role") or "") in rroles
                     and (not pipeline_run or str(conductor._task_payload(t).get("pipeline_run") or "") == pipeline_run)
                     and (t.get("status") or "") not in conductor.TERMINAL_TASK_STATUSES}
print("pending_roles:", pending_roles)

def is_remediation(t):
    if (t.get("status") or "") != "done":
        return False
    if (t.get("owner_role") or "") in rroles:
        return False
    payload = conductor._task_payload(t)
    source_ref = str(payload.get("source_task") or "")
    source = {str(tt.get("public_id")): tt for tt in tasks}.get(source_ref)
    if source_ref:
        return bool(source and (source.get("owner_role") or "") in rroles)
    return str(t.get("public_id") or "").startswith("FIX")

done_fixes = [t for t in tasks if is_remediation(t)]
print("done_fixes:", [t["public_id"] for t in done_fixes])
