import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.database import init_db
from backend.modules.orchestrator.registry import (
    AgentRole, AGENT_REGISTRY, validate_agent_permission, list_agent_profiles
)
from backend.modules.orchestrator.planner import SubTask, SubTaskStatus, DAGPlanner
from backend.modules.orchestrator.file_lock import file_lock_manager
from backend.modules.orchestrator.engine import orchestrator_engine
from backend.modules.requirement.schema import TaskSpecification, RiskLevel, TaskStatus

client = TestClient(app)

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()

@pytest.mark.asyncio
async def test_dag_planner_cycle_detection_and_batches():
    # 1. Normal Diamond DAG: st1 -> (st2, st3) -> st4
    st1 = SubTask(id="st1", title="Task 1", assigned_agent=AgentRole.SECURITY_REVIEWER)
    st2 = SubTask(id="st2", title="Task 2", assigned_agent=AgentRole.RESEARCH_AGENT, depends_on=["st1"])
    st3 = SubTask(id="st3", title="Task 3", assigned_agent=AgentRole.RESEARCH_AGENT, depends_on=["st1"])
    st4 = SubTask(id="st4", title="Task 4", assigned_agent=AgentRole.ORCHESTRATOR, depends_on=["st2", "st3"])

    subtasks = [st1, st2, st3, st4]
    assert DAGPlanner.detect_cycles(subtasks) is False

    batches = DAGPlanner.get_execution_batches(subtasks)
    assert len(batches) == 3
    assert [st.id for st in batches[0]] == ["st1"]
    assert set(st.id for st in batches[1]) == {"st2", "st3"}
    assert [st.id for st in batches[2]] == ["st4"]

    # 2. Cycle Detection: c1 -> c2 -> c1
    c1 = SubTask(id="c1", title="Cycle 1", assigned_agent=AgentRole.ORCHESTRATOR, depends_on=["c2"])
    c2 = SubTask(id="c2", title="Cycle 2", assigned_agent=AgentRole.ORCHESTRATOR, depends_on=["c1"])
    assert DAGPlanner.detect_cycles([c1, c2]) is True

    with pytest.raises(ValueError, match="Circular dependency detected"):
        DAGPlanner.get_execution_batches([c1, c2])

def test_agent_registry_and_permission_boundaries():
    profiles = list_agent_profiles()
    assert len(profiles) >= 5
    roles = {p["role"] for p in profiles}
    assert "orchestrator" in roles
    assert "research_agent" in roles
    assert "development_agent" in roles
    assert "qa_agent" in roles
    assert "security_reviewer" in roles

    # Security Reviewer is read-only
    assert validate_agent_permission("security_reviewer", "workspace.read") is True
    assert validate_agent_permission("security_reviewer", "workspace.write") is False
    assert validate_agent_permission("security_reviewer", "terminal.execute") is False

    # QA Agent can execute terminal, but cannot write files
    assert validate_agent_permission("qa_agent", "terminal.execute") is True
    assert validate_agent_permission("qa_agent", "workspace.write") is False

    # Dev Agent can write files and execute
    assert validate_agent_permission("development_agent", "workspace.write") is True
    assert validate_agent_permission("development_agent", "terminal.execute") is True

@pytest.mark.asyncio
async def test_file_lock_manager_concurrency():
    test_path = "H:/AiLocal/temp_test_runs/concurrent_file.py"
    
    # Subtask A acquires lock
    locked_a = await file_lock_manager.acquire_lock(test_path, "subtask_A", timeout=1.0)
    assert locked_a is True
    assert file_lock_manager.is_locked(test_path) == "subtask_A"

    # Re-entrancy: Subtask A acquires again -> True
    assert await file_lock_manager.acquire_lock(test_path, "subtask_A") is True

    # Subtask B tries to acquire same lock with 0.1s timeout -> False
    locked_b = await file_lock_manager.acquire_lock(test_path, "subtask_B", timeout=0.1)
    assert locked_b is False

    # Subtask A releases lock
    released = await file_lock_manager.release_lock(test_path, "subtask_A")
    assert released is True
    assert file_lock_manager.is_locked(test_path) is None

    # Now Subtask B can acquire
    locked_b = await file_lock_manager.acquire_lock(test_path, "subtask_B", timeout=1.0)
    assert locked_b is True
    assert file_lock_manager.is_locked(test_path) == "subtask_B"
    await file_lock_manager.release_lock(test_path, "subtask_B")

@pytest.mark.asyncio
async def test_orchestrator_failure_containment_and_blocked_propagation(tmp_path):
    # Setup test workspace
    ws_dir = tmp_path / "ws_orch"
    ws_dir.mkdir()
    
    # Create task spec
    from backend.core.database import get_db_connection
    import uuid
    import json
    task_id = f"test_orch_task_fail_{uuid.uuid4().hex[:6]}"
    workspace_id = f"ws_orch_{uuid.uuid4().hex[:6]}"
    
    spec = TaskSpecification(
        task_id=task_id,
        workspace_id=workspace_id,
        goal="Test failure containment",
        original_prompt="Test failure containment",
        normalized_prompt="test failure containment",
        status=TaskStatus.READY,
        risk_level=RiskLevel.LOW,
        acceptance_criteria=["Must block dependents if step 1 fails"]
    )
    
    conn = await get_db_connection()
    try:
        await conn.execute(
            "INSERT OR REPLACE INTO workspaces (id, path, name) VALUES (?, ?, ?)",
            (workspace_id, str(ws_dir), "Orch WS")
        )
        await conn.execute(
            "INSERT OR REPLACE INTO tasks (id, workspace_id, status, goal, risk_level, spec_json) VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, workspace_id, spec.status.value, spec.goal, spec.risk_level.value, spec.model_dump_json())
        )
        await conn.commit()
    finally:
        await conn.close()

    plan = await orchestrator_engine.create_plan_for_task(task_id)
    assert len(plan.subtasks) >= 3

    # Artificially assign an unauthorized permission to the first subtask to induce failure
    first_st = plan.subtasks[0]
    first_st.required_permissions.append("unauthorized.root.permission")
    conn = await get_db_connection()
    try:
        await conn.execute(
            "UPDATE subtasks SET required_permissions = ? WHERE id = ?",
            (json.dumps(first_st.required_permissions), first_st.id)
        )
        await conn.commit()
    finally:
        await conn.close()

    # Execute plan
    executed_plan = await orchestrator_engine.execute_plan(task_id, ws_dir)
    assert executed_plan.status in ["failed", "blocked"]
    
    # First subtask must be failed
    updated_first = next(st for st in executed_plan.subtasks if st.id == first_st.id)
    assert updated_first.status == SubTaskStatus.FAILED

    # Downstream subtask must be BLOCKED (not run blindly)
    downstream = next(st for st in executed_plan.subtasks if first_st.id in st.depends_on)
    assert downstream.status == SubTaskStatus.BLOCKED

def test_orchestrator_api_lifecycle(tmp_path):
    ws_dir = tmp_path / "ws_api_orch"
    ws_dir.mkdir()

    # 1. Open workspace
    resp_ws = client.post("/api/v1/workspace/open", json={"path": str(ws_dir)})
    assert resp_ws.status_code == 200
    ws_id = resp_ws.json()["workspace"]["id"]

    # 2. Intake task requirement
    resp_req = client.post("/api/v1/requirements/analyze", json={
        "workspace_id": ws_id,
        "workspace_path": str(ws_dir),
        "prompt": "Build local calculator module with tests."
    })
    assert resp_req.status_code == 200
    task_id = resp_req.json()["task_spec"]["task_id"]

    # 3. Create Orchestrator Plan
    resp_plan = client.post("/api/v1/orchestrator/plan", json={"task_id": task_id})
    assert resp_plan.status_code == 200
    plan_data = resp_plan.json()["plan"]
    assert len(plan_data["subtasks"]) >= 4

    # 4. Get Plan
    resp_get = client.get(f"/api/v1/orchestrator/plans/{task_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["plan"]["id"] == plan_data["id"]

    # 5. Execute Plan
    resp_exec = client.post(f"/api/v1/orchestrator/execute/{task_id}", json={
        "task_id": task_id,
        "workspace_path": str(ws_dir)
    })
    assert resp_exec.status_code == 200
    assert resp_exec.json()["plan"]["status"] in ["completed", "completed_with_warnings"]

    # 6. List Agents
    resp_agents = client.get("/api/v1/orchestrator/agents")
    assert resp_agents.status_code == 200
    assert len(resp_agents.json()["agents"]) >= 5
