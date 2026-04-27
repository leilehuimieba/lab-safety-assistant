from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "release" / "recover_dify_provider_and_smoke.py"


def load_module():
    spec = importlib.util.spec_from_file_location("recover_dify_provider_and_smoke", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_patch_workflow_model_calls_patch_script(monkeypatch, tmp_path: Path) -> None:
    module = load_module()
    captured: dict[str, object] = {}

    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def _fake_run(cmd: list[str], input_text: str | None = None):
        captured["cmd"] = cmd
        captured["input_text"] = input_text
        return _Proc()

    monkeypatch.setattr(module, "_run", _fake_run)

    module.patch_workflow_model(str(tmp_path), "wf-123", "gpt-5.2", 0.2)

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert str(Path(tmp_path) / "scripts" / "patch_workflow_model.py") in cmd
    assert "--workflow-id" in cmd and "wf-123" in cmd
    assert "--model-name" in cmd and "gpt-5.2" in cmd
    assert "--temperature" in cmd and "0.2" in cmd

