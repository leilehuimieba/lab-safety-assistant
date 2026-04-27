from __future__ import annotations

import sys
from pathlib import Path

# web_demo 已通过 pytest.ini pythonpath 以标准包方式导入，
# scripts 仍需要 sys.path 兼容以便测试直接 import 根层脚本。
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
