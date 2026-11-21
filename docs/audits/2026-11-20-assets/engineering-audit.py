import contextlib
import importlib.metadata
import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

root = Path.cwd()
sys.path.insert(0, str(root))
from apps.api.main import app
from tools import release_check
import tianze

saved = json.loads((root / "apps/web/src/api/generated/openapi.json").read_text(encoding="utf-8"))
current = app.openapi()
ci = subprocess.run([sys.executable, "-c", "import tianze; assert tianze.__version__ == '0.3.0'"], capture_output=True, encoding="utf-8")

class StopBeforeBuild(Exception):
    pass

capture = io.StringIO()
real_load = release_check._load

def audit_load(relative, default):
    if relative == "release/quality-summary.json":
        return {"allPass": False, "failed": ["AUDIT_INJECTED_FAILURE"]}
    return real_load(relative, default)

with patch.object(release_check, "_load", side_effect=audit_load), patch.object(release_check.subprocess, "run", side_effect=StopBeforeBuild), contextlib.redirect_stdout(capture):
    try:
        release_check.main()
    except StopBeforeBuild:
        pass

result = {
    "python": sys.version,
    "versions": {name: importlib.metadata.version(name) for name in ["fastapi", "pydantic", "pytest", "uvicorn", "lunar-python"]},
    "packageVersion": tianze.__version__,
    "contract": {
        "savedPaths": len(saved["paths"]), "currentPaths": len(current["paths"]),
        "missingPaths": sorted(set(current["paths"]) - set(saved["paths"])),
        "savedSchemas": list(saved.get("components", {}).get("schemas", {})),
        "currentSchemas": list(current.get("components", {}).get("schemas", {})),
    },
    "ciVersionCheck": {"returncode": ci.returncode, "stderr": ci.stderr},
    "qualityGateFailureProbe": {"injectedQualityAllPass": False, "observedOutput": capture.getvalue(), "stoppedBeforeBuildAndWrites": True},
}
destination = root.parent / "engineering-audit.json"
destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=True, indent=2))
