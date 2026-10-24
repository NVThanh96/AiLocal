import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings
from backend.core.database import init_db
from backend.modules.workspace.manager import WorkspaceManager
from backend.modules.memory.engine import MemoryEngine
from backend.modules.retention.manager import RetentionManager
from backend.modules.agents.qa_dev import QADevAgent

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    asyncio.run(init_db())

@pytest.mark.asyncio
async def test_project_memory_lifecycle():
    """Verify storing architectural rules and retrieving project decisions."""
    workspace_path = str(settings.BASE_DIR)
    ws = await WorkspaceManager.open_workspace(workspace_path)

    mid = await MemoryEngine.save_project_decision(
        workspace_id=ws["id"],
        category="Architecture",
        title="Local-First Data Policy",
        content="All AI model inference must run strictly on localhost port 11434 with zero cloud transmission."
    )
    assert mid is not None

    decisions = await MemoryEngine.get_project_decisions(ws["id"])
    assert len(decisions) >= 1
    assert decisions[0]["title"] == "Local-First Data Policy"

@pytest.mark.asyncio
async def test_error_memory_and_prevention_of_repetition():
    """Verify error signature normalization, known-fix lookup, and promotion to verified lesson."""
    workspace_path = str(settings.BASE_DIR)
    ws = await WorkspaceManager.open_workspace(workspace_path)

    raw_err = "UnicodeEncodeError: 'charmap' codec can't encode character at line 42 at 0x7ffd1234 2026-10-20T12:00:00"
    
    # 1. Record error with verified fix
    eid = await MemoryEngine.record_error(
        workspace_id=ws["id"],
        raw_error=raw_err,
        root_cause="Windows terminal standard out defaults to cp1252 instead of utf-8",
        attempted_fixes=["chcp 65001", "sys.stdout.reconfigure(encoding='utf-8')"],
        verified_patch="sys.stdout.reconfigure(encoding='utf-8')",
        regression_test="tests/test_e2e_phase1.py",
        is_verified=False
    )
    assert eid is not None

    # 2. Lookup similar error with different line and timestamp
    similar_err = "UnicodeEncodeError: 'charmap' codec can't encode character at line 89 at 0x7ffd9999 2026-10-20T18:30:00"
    found = await MemoryEngine.find_similar_error(ws["id"], similar_err)
    assert found is not None
    assert found["verified_patch"] == "sys.stdout.reconfigure(encoding='utf-8')"

    # 3. Upgrade to verified lesson
    promoted = await MemoryEngine.upgrade_to_verified_lesson(eid)
    assert promoted is True

@pytest.mark.asyncio
async def test_qa_agent_test_runner():
    """Verify QA Agent can execute test target and return structured pass metrics."""
    workspace_path = str(settings.BASE_DIR)
    ws = await WorkspaceManager.open_workspace(workspace_path)

    # Run specifically phase 0 baseline test
    res = await QADevAgent.run_tests(ws["id"], workspace_path, test_path="tests/test_phase0_baseline.py")
    assert res["status"] == "PASSED"
    assert res["exit_code"] == 0
    assert res["passed_count"] >= 5

def test_retention_manager_dry_run_and_gitkeep_protection():
    """Verify retention cleanup respects dry-run and protects .gitkeep files."""
    report = RetentionManager.cleanup_expired_artifacts(dry_run=True, max_age_hours=0.0001)
    assert report["dry_run"] is True
    # .gitkeep files should never be targeted for deletion
    assert not any(f.endswith(".gitkeep") for f in report["sample_files"])

def test_api_memory_and_qa_endpoints():
    """Verify Phase 5 REST API endpoints."""
    with TestClient(app) as client:
        # Save project memory
        res_mem = client.post("/api/v1/memory/project", json={
            "workspace_id": "ws-mem-test",
            "category": "Testing",
            "title": "Regression Rule",
            "content": "All phases must achieve 100% passing tests."
        })
        assert res_mem.status_code == 200

        # Error lookup
        res_lookup = client.post("/api/v1/memory/errors/lookup", json={
            "workspace_id": "ws-mem-test",
            "raw_error": "NonExistentError: test"
        })
        assert res_lookup.status_code == 200

        # Retention cleanup
        res_ret = client.post("/api/v1/retention/cleanup", json={
            "dry_run": True,
            "max_age_hours": 48.0
        })
        assert res_ret.status_code == 200
        assert "cleanup_report" in res_ret.json()
