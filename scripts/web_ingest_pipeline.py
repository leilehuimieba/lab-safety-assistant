from __future__ import annotations

import importlib.util
import runpy
import sys
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "pipeline/web_ingest_pipeline.py"


def _load_impl():
    spec = importlib.util.spec_from_file_location(f"{__name__}__impl", _TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load target script: {_TARGET}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


_impl = _load_impl()
for _name in dir(_impl):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_impl, _name)


if __name__ == "__main__":
    runpy.run_path(str(_TARGET), run_name="__main__")
