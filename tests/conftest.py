from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
WEB_DEMO = ROOT / "web_demo"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

if str(WEB_DEMO) not in sys.path:
    sys.path.insert(0, str(WEB_DEMO))
