from __future__ import annotations

import os
import sys
from pathlib import Path

# 测试环境默认关闭语义检索，避免 sentence-transformers 自动下载模型导致超时
os.environ.setdefault("ENABLE_EMBEDDING", "0")

# web_demo 已通过 pytest.ini pythonpath 以标准包方式导入，
# scripts 仍需要 sys.path 兼容以便测试直接 import 根层脚本。
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
