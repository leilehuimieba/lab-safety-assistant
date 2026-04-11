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


def test_enforced_prod_policy_reads_latest_check_json(tmp_path: Path) -> None:
    module = load_module()

    repo = tmp_path / "repo"
    release_dir = repo / "release_exports" / "v8.1"
    docs_eval = repo / "docs" / "eval"
    docs_ops = repo / "docs" / "ops"
    oneclick_run = repo / "artifacts" / "eval_release_oneclick" / "run_20260411_000000"
    release_dir.mkdir(parents=True)
    docs_eval.mkdir(parents=True)
    docs_ops.mkdir(parents=True)
    oneclick_run.mkdir(parents=True)

    (release_dir / "knowledge_base_import_ready.csv").write_text("ok\n", encoding="utf-8")
    (release_dir / "README.md").write_text("# ok\n", encoding="utf-8")
    (release_dir / "web_seed_urls_v8_1_prefetch_status.csv").write_text("ok\n", encoding="utf-8")

    (oneclick_run / "eval_release_oneclick_report.json").write_text(
        '{"status":"success"}\n',
        encoding="utf-8",
    )
    (docs_eval / "release_policy_check.json").write_text(
        '{"status":"PASS","violations":[]}\n',
        encoding="utf-8",
    )
    (docs_eval / "release_policy_check_prod.json").write_text(
        '{"status":"BLOCK","violations":["legacy stale file"]}\n',
        encoding="utf-8",
    )
    (docs_eval / "release_risk_note_auto.json").write_text(
        '{"gate_decision":"PASS","latest_metrics":{"emergency_pass_rate":1.0}}\n',
        encoding="utf-8",
    )
    (docs_eval / "eval_dashboard_gate_override.json").write_text(
        '{"enabled":false}\n',
        encoding="utf-8",
    )

    payload = '{"status":"ok"}'.encode("utf-8")

    class DummyResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return payload

    old_argv = sys.argv[:]
    old_urlopen = module.urlopen
    try:
        module.urlopen = lambda *_args, **_kwargs: DummyResp()
        sys.argv = [
            "go_live_preflight.py",
            "--repo-root",
            str(repo),
            "--enforce-prod-policy",
            "--output-json",
            "docs/ops/go_live_readiness.json",
            "--output-md",
            "docs/ops/go_live_readiness.md",
        ]
        exit_code = module.main()
    finally:
        module.urlopen = old_urlopen
        sys.argv = old_argv

    assert exit_code == 0
