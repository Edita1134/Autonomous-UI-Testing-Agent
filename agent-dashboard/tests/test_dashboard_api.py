from dataclasses import replace
from fastapi.testclient import TestClient

import dashboard.app as dashboard_app


client = TestClient(dashboard_app.app)


def test_dashboard_index_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_sample_issues_endpoint(monkeypatch, tmp_path):
    issues = tmp_path / "issues"
    issues.mkdir()
    (issues / "checkout.md").write_text("# Checkout\n\n## Acceptance Criteria\n- AC1: Checkout works", encoding="utf-8")
    monkeypatch.setattr(dashboard_app, "settings", replace(dashboard_app.settings, agent_dir=tmp_path))

    response = client.get("/api/issues")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "checkout"


def test_github_issue_endpoint(monkeypatch):
    monkeypatch.setattr(
        dashboard_app,
        "fetch_issue_markdown",
        lambda settings, number: f"# Issue {number}\n\n## Acceptance Criteria\n- AC1: Works",
    )

    response = client.get("/api/github/issues/42")

    assert response.status_code == 200
    assert response.json()["number"] == 42
    assert "Issue 42" in response.json()["markdown"]


def test_invalid_run_id_is_rejected():
    response = client.get("/api/runs/../../secret")
    assert response.status_code in (400, 404)
