from __future__ import annotations

import generate_release_readiness_dashboard as grd


def test_classify_priority() -> None:
    assert grd.classify_priority("route_success_rate too low") == "P0"
    assert grd.classify_priority("failover fail streak exceeded") == "P0"
    assert grd.classify_priority("latency_p95_ms too high") == "P1"
    assert grd.classify_priority("unknown issue") == "P2"


def test_build_blocker_rows_topn() -> None:
    rows = grd.build_blocker_rows(
        [
            {"profile": "demo", "violations": ["route_success_rate too low", "override mode not allowed"]},
            {"profile": "prod", "violations": ["route_success_rate too low"]},
        ],
        top_n=10,
    )
    assert len(rows) == 2
    assert rows[0]["reason"] == "route_success_rate too low"
    assert rows[0]["count"] == "2"
    assert rows[0]["priority"] == "P0"
    assert rows[0]["profiles"] == "demo,prod"


def test_build_action_plan_rows() -> None:
    blockers = [
        {
            "rank": "1",
            "reason": "route_success_rate too low",
            "count": "2",
            "profiles": "demo,prod",
            "priority": "P0",
            "recommended_action": "Recover route.",
        }
    ]
    plan = grd.build_action_plan_rows(blockers, {})
    assert len(plan) == 1
    assert plan[0]["task_id"] == "REL-FIX-01"
    assert plan[0]["priority"] == "P0"
    assert plan[0]["status"] == "todo"


def test_build_action_plan_rows_preserve_existing_assignment() -> None:
    blockers = [
        {
            "rank": "2",
            "reason": "route_timeout_rate too high",
            "count": "1",
            "profiles": "prod",
            "priority": "P0",
            "recommended_action": "Tune timeout.",
        }
    ]
    existing = {
        "route_timeout_rate too high": {
            "task_id": "REL-FIX-99",
            "status": "in_progress",
            "owner": "alice",
            "eta": "2026-04-02",
        }
    }
    plan = grd.build_action_plan_rows(blockers, existing)
    assert plan[0]["task_id"] == "REL-FIX-99"
    assert plan[0]["status"] == "in_progress"
    assert plan[0]["owner"] == "alice"
    assert plan[0]["eta"] == "2026-04-02"


def test_load_existing_action_plan(tmp_path) -> None:
    csv_path = tmp_path / "release_fix_plan_auto.csv"
    csv_path.write_text(
        "task_id,priority,status,owner,eta,profiles,blocking_reason,recommended_action,verification_step\n"
        "REL-FIX-01,P0,in_progress,alice,2026-04-02,prod,route_timeout_rate too high,fix,re-run\n",
        encoding="utf-8",
    )
    existing = grd.load_existing_action_plan(csv_path)
    assert "route_timeout_rate too high" in existing
    assert existing["route_timeout_rate too high"]["owner"] == "alice"
