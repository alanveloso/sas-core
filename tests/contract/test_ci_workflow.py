"""Contract: CI workflow covers P1-004 gate jobs (no invented PASS)."""

from __future__ import annotations

import yaml

from tests.support.repo import REPO_ROOT

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

REQUIRED_JOBS = {
    "lint",
    "typecheck",
    "unit",
    "integration-sqlite",
    "integration-postgres",
    "docker",
    "smoke-mtls",
    "winnforum-subset-dry-run",
}


def test_ci_workflow_exists_and_lists_required_jobs():
    assert WORKFLOW.is_file(), "P1-004 requires .github/workflows/ci.yml"
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert data["name"] == "ci"
    jobs = set(data["jobs"])
    missing = REQUIRED_JOBS - jobs
    assert not missing, sorted(missing)
    # Avoid a misleading job id that looks like an official harness execution.
    assert "winnforum-subset" not in jobs


def test_ci_workflow_uploads_winnforum_artifacts_without_claiming_pass():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "--dry-run" in text
    assert "upload-artifact" in text
    assert "winnforum-dry-run" in text
    assert "status=passing" not in text
    assert "not an official suite run" in text


def test_ci_workflow_runs_postgres_and_mtls_smoke():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "SAS_TEST_DATABASE_URL" in text
    assert "tools.generate_dev_certs" in text
    assert "tools.smoke_mtls" in text
    assert "ruff check" in text
    assert "mypy compliance tools" in text
