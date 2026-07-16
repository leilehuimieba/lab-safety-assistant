from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_docker_runtime_declares_python_multipart() -> None:
    requirements = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    declared = {
        line.split("==", 1)[0].split(">=", 1)[0].strip().lower()
        for line in requirements.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "python-multipart" in declared, (
        "Docker installs the root requirements.txt, so FastAPI File/Form routes "
        "require python-multipart there"
    )
