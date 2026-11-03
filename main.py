from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.chdir(root)
    from wfeditor.main import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
