from __future__ import annotations

import importlib.util


FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


if FASTAPI_AVAILABLE:
    from fastapi.testclient import TestClient
    from web_demo import app as web_app
    from web_demo.routers import training_routes as _tr

    def test_training_roster_status_uses_roster_and_attempts(monkeypatch, tmp_path) -> None:
        roster = tmp_path / "training_roster.csv"
        attempts = tmp_path / "training_attempts.csv"
        roster.write_text(
            "student_id,name,class_name,lab_group,required_training\n"
            "2026001,学生A,化学工程1班,A组,true\n"
            "2026002,学生B,化学工程1班,A组,true\n"
            "2026003,学生C,化学工程1班,B组,true\n",
            encoding="utf-8-sig",
        )
        attempts.write_text(
            "attempt_id,submitted_at,participant,session_id,score,total_questions,pass_threshold,passed,weak_categories\n"
            "A1,2026-04-27T09:00:00,学生A,s1,90,5,80,true,\n"
            "B1,2026-04-27T09:10:00,学生B,s1,60,5,80,false,Chemical\n",
            encoding="utf-8-sig",
        )
        monkeypatch.setattr(_tr, "TRAINING_ROSTER_FILE", roster)
        monkeypatch.setattr(_tr, "TRAINING_ROSTER_TEMPLATE_FILE", roster)
        monkeypatch.setattr(_tr, "TRAINING_ATTEMPTS_FILE", attempts)

        client = TestClient(web_app.app)
        resp = client.get("/api/training/roster_status")

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["total_required"] == 3
        assert payload["completed_count"] == 2
        assert payload["passed_count"] == 1
        assert payload["incomplete_count"] == 2
        assert {item["name"] for item in payload["incomplete_students"]} == {"学生B", "学生C"}


    def test_training_roster_upload_saves_csv(monkeypatch, tmp_path) -> None:
        roster = tmp_path / "training_roster.csv"
        attempts = tmp_path / "training_attempts.csv"
        template = tmp_path / "training_roster_template.csv"
        attempts.write_text(
            "attempt_id,submitted_at,participant,session_id,score,total_questions,pass_threshold,passed,weak_categories\n",
            encoding="utf-8-sig",
        )
        template.write_text("student_id,name,class_name,lab_group,required_training\n", encoding="utf-8-sig")
        monkeypatch.setattr(_tr, "TRAINING_ROSTER_FILE", roster)
        monkeypatch.setattr(_tr, "TRAINING_ROSTER_TEMPLATE_FILE", template)
        monkeypatch.setattr(_tr, "TRAINING_ATTEMPTS_FILE", attempts)

        client = TestClient(web_app.app)
        resp = client.post(
            "/api/training/roster_upload",
            json={
                "csv_text": "student_id,name,class_name,lab_group,required_training\n2026008,学生H,化学工程2班,A组,true\n"
            },
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["saved_count"] == 1
        assert payload["status"]["total_required"] == 1
        assert roster.exists()
        assert "学生H" in roster.read_text(encoding="utf-8-sig")


    def test_training_roster_template_download(monkeypatch, tmp_path) -> None:
        template = tmp_path / "training_roster_template.csv"
        template.write_text(
            "student_id,name,class_name,lab_group,required_training\n2026001,张三,化学工程1班,A组,true\n",
            encoding="utf-8-sig",
        )
        monkeypatch.setattr(_tr, "TRAINING_ROSTER_TEMPLATE_FILE", template)

        client = TestClient(web_app.app)
        resp = client.get("/api/training/roster_template.csv")

        assert resp.status_code == 200
        assert "student_id,name,class_name" in resp.text
        assert "training_roster_template.csv" in resp.headers.get("content-disposition", "")
