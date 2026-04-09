from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "release" / "go_live_preflight.py"


def load_module():
    spec = importlib.util.spec_from_file_location("go_live_preflight", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_expected_prefetch_status_name_tracks_release_dir() -> None:
    module = load_module()

    assert (
        module.expected_prefetch_status_name(Path("release_exports/v8.2"))
        == "web_seed_urls_v8_2_prefetch_status.csv"
    )
    assert (
        module.expected_prefetch_status_name(Path("release_exports/v8.1"))
        == "web_seed_urls_v8_1_prefetch_status.csv"
    )


def test_check_release_package_uses_release_specific_prefetch_name(tmp_path: Path) -> None:
    module = load_module()

    release_dir = tmp_path / "v8.2"
    release_dir.mkdir()
    (release_dir / "knowledge_base_import_ready.csv").write_text("ok\n", encoding="utf-8")
    (release_dir / "README.md").write_text("# ok\n", encoding="utf-8")
    (release_dir / "web_seed_urls_v8_2_prefetch_status.csv").write_text("ok\n", encoding="utf-8")

    results = module.check_release_package(release_dir)

    assert all(item.ok for item in results)
    assert [item.key for item in results] == [
        "release_package::knowledge_base_import_ready.csv",
        "release_package::README.md",
        "release_package::web_seed_urls_v8_2_prefetch_status.csv",
    ]
