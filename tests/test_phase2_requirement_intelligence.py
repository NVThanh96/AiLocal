import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings
from backend.core.database import init_db
from backend.modules.workspace.manager import WorkspaceManager
from backend.modules.requirement.engine import RequirementIntelligenceEngine
from backend.modules.requirement.schema import TaskStatus, RiskLevel

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    asyncio.run(init_db())

@pytest.mark.asyncio
async def test_clear_requirement_is_ready():
    """Verify that a specific, safe requirement is assessed as READY with LOW risk."""
    workspace_path = str(settings.BASE_DIR)
    ws = await WorkspaceManager.open_workspace(workspace_path)

    spec = await RequirementIntelligenceEngine.analyze_prompt(
        workspace_id=ws["id"],
        workspace_path=workspace_path,
        user_prompt="Đọc nội dung file masterImplementationPrompt.md và kiểm tra các phase"
    )

    assert spec.status == TaskStatus.READY
    assert spec.risk_level == RiskLevel.LOW
    assert len(spec.unresolved_questions) == 0
    # Verified facts should have automatically found masterImplementationPrompt.md
    assert any("masterImplementationPrompt.md" in fact.fact for fact in spec.verified_facts)
    assert "masterImplementationPrompt.md" in spec.scope["target_files"]

@pytest.mark.asyncio
async def test_ambiguous_requirement_needs_clarification():
    """Verify that an ambiguous requirement triggers NEEDS_CLARIFICATION and generates questions."""
    workspace_path = str(settings.BASE_DIR)
    ws = await WorkspaceManager.open_workspace(workspace_path)

    spec = await RequirementIntelligenceEngine.analyze_prompt(
        workspace_id=ws["id"],
        workspace_path=workspace_path,
        user_prompt="Hãy sửa lỗi và tối ưu"
    )

    assert spec.status == TaskStatus.NEEDS_CLARIFICATION
    assert len(spec.unresolved_questions) > 0
    q = spec.unresolved_questions[0]
    assert len(q.suggested_options) > 0

    # User answers the question
    updated_spec = await RequirementIntelligenceEngine.answer_clarification(
        task_id=spec.task_id,
        question_id=q.id,
        chosen_option="Chỉ xem xét và tạo báo cáo đề xuất (Read-only)"
    )

    assert updated_spec.status == TaskStatus.READY
    assert updated_spec.request_version == 2
    assert any("Chỉ xem xét" in a for a in updated_spec.approved_assumptions)

@pytest.mark.asyncio
async def test_destructive_requirement_needs_approval():
    """Verify that destructive operations (delete) are classified as HIGH risk and require approval."""
    workspace_path = str(settings.BASE_DIR)
    ws = await WorkspaceManager.open_workspace(workspace_path)

    spec = await RequirementIntelligenceEngine.analyze_prompt(
        workspace_id=ws["id"],
        workspace_path=workspace_path,
        user_prompt="Xóa file storage/test_dump.sql khỏi hệ thống"
    )

    assert spec.status == TaskStatus.NEEDS_APPROVAL
    assert spec.risk_level == RiskLevel.HIGH
    assert "workspace.delete" in spec.required_permissions

    # Test rejection
    rejected_spec = await RequirementIntelligenceEngine.approve_task(spec.task_id, approved=False)
    assert rejected_spec.status == TaskStatus.BLOCKED
    assert rejected_spec.request_version == 2

    # Test re-approval
    approved_spec = await RequirementIntelligenceEngine.approve_task(spec.task_id, approved=True)
    assert approved_spec.status == TaskStatus.READY
    assert approved_spec.request_version == 3

@pytest.mark.asyncio
async def test_task_version_audit_trail():
    """Verify that task versions are immutably archived for auditability."""
    workspace_path = str(settings.BASE_DIR)
    ws = await WorkspaceManager.open_workspace(workspace_path)

    spec = await RequirementIntelligenceEngine.analyze_prompt(
        workspace_id=ws["id"],
        workspace_path=workspace_path,
        user_prompt="sửa lỗi"
    )
    q_id = spec.unresolved_questions[0].id
    await RequirementIntelligenceEngine.answer_clarification(spec.task_id, q_id, "backend/")

    versions = await RequirementIntelligenceEngine.get_task_versions(spec.task_id)
    assert len(versions) >= 2
    assert versions[0]["version"] == 1
    assert versions[1]["version"] == 2
    assert versions[0]["status"] == "NEEDS_CLARIFICATION"
    assert versions[1]["status"] == "READY"

def test_api_requirement_endpoints():
    """Verify REST API endpoints for requirement intelligence."""
    with TestClient(app) as client:
        # 1. Analyze
        res = client.post("/api/v1/requirements/analyze", json={
            "workspace_id": "ws-test-123",
            "workspace_path": str(settings.BASE_DIR),
            "prompt": "Đọc file MINDMAP.md và tổng hợp"
        })
        assert res.status_code == 200
        data = res.json()["task_spec"]
        assert data["status"] == "READY"
        task_id = data["task_id"]

        # 2. Get task detail
        res_get = client.get(f"/api/v1/requirements/tasks/{task_id}")
        assert res_get.status_code == 200
        assert res_get.json()["task_spec"]["task_id"] == task_id

        # 3. Get version history
        res_ver = client.get(f"/api/v1/requirements/tasks/{task_id}/versions")
        assert res_ver.status_code == 200
        assert len(res_ver.json()["versions"]) >= 1
