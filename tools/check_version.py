from __future__ import annotations

import importlib.metadata
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    import tianze

    installed = importlib.metadata.version("tianze-bazi")
    if installed != tianze.__version__:
        print(f"Version mismatch: installed={installed}, source={tianze.__version__}")
        return 1
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        tag = os.environ.get("GITHUB_REF_NAME", "")
        if tag != f"v{tianze.__version__}":
            print(f"Release tag mismatch: {tag} != v{tianze.__version__}")
            return 1
    print(f"Version consistent: {tianze.__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
