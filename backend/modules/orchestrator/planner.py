import uuid
from enum import Enum
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from backend.modules.orchestrator.registry import AgentRole, validate_agent_permission
from backend.modules.requirement.schema import TaskSpecification, RiskLevel

class SubTaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class SubTask(BaseModel):
    id: str = Field(default_factory=lambda: f"subtask_{uuid.uuid4().hex[:8]}")
    title: str
    assigned_agent: AgentRole
    depends_on: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    status: SubTaskStatus = SubTaskStatus.PENDING
    input_context: Dict[str, Any] = Field(default_factory=dict)
    result_output: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2

class TaskDAGPlan(BaseModel):
    id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    task_id: str
    workspace_id: str
    version: int = 1
    status: str = "draft"  # draft, ready, in_progress, completed, failed, cancelled
    subtasks: List[SubTask] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class DAGPlanner:
    """
    Constructs, validates, and organizes subtasks into an acyclic dependency graph.
    """
    @staticmethod
    def detect_cycles(subtasks: List[SubTask]) -> bool:
        """
        Uses Kahn's algorithm / in-degree tracking to detect cycles.
        Returns True if a cycle exists, False if acyclic.
        """
        adj: Dict[str, List[str]] = {st.id: [] for st in subtasks}
        in_degree: Dict[str, int] = {st.id: 0 for st in subtasks}

        for st in subtasks:
            for dep in st.depends_on:
                if dep in adj:
                    adj[dep].append(st.id)
                    in_degree[st.id] += 1

        queue = [st_id for st_id, deg in in_degree.items() if deg == 0]
        visited_count = 0

        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for neighbor in adj.get(curr, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited_count < len(subtasks)

    @staticmethod
    def get_execution_batches(subtasks: List[SubTask]) -> List[List[SubTask]]:
        """
        Returns waves of subtasks that can be executed concurrently in order of dependencies.
        """
        if DAGPlanner.detect_cycles(subtasks):
            raise ValueError("Circular dependency detected in subtask DAG!")

        subtask_map = {st.id: st for st in subtasks}
        completed_ids: Set[str] = set()
        batches: List[List[SubTask]] = []
        remaining_ids = set(subtask_map.keys())

        while remaining_ids:
            # Subtasks whose dependencies are all met
            batch = [
                subtask_map[st_id]
                for st_id in remaining_ids
                if all(dep in completed_ids for dep in subtask_map[st_id].depends_on)
            ]
            if not batch:
                # Deadlock or unresolvable dependency
                break

            batches.append(batch)
            for st in batch:
                completed_ids.add(st.id)
                remaining_ids.remove(st.id)

        return batches

    @staticmethod
    def plan_from_task_spec(task_spec: TaskSpecification) -> TaskDAGPlan:
        """
        Decomposes a TaskSpecification into a multi-agent DAG plan.
        """
        subtasks: List[SubTask] = []

        # 1. Security Review node
        sec_subtask = SubTask(
            title=f"Security Review for {task_spec.goal[:40]}",
            assigned_agent=AgentRole.SECURITY_REVIEWER,
            required_permissions=["workspace.read"],
            input_context={
                "risk_level": task_spec.risk_level.value,
                "required_permissions": task_spec.required_permissions,
                "goal": task_spec.goal
            }
        )
        subtasks.append(sec_subtask)

        # 2. Research / Context gathering node
        res_subtask = SubTask(
            title="Gather Workspace Context & Relevant Sources",
            assigned_agent=AgentRole.RESEARCH_AGENT,
            depends_on=[sec_subtask.id],
            required_permissions=["workspace.read"],
            input_context={
                "scope": task_spec.scope,
                "constraints": task_spec.constraints,
                "verified_facts": task_spec.verified_facts
            }
        )
        subtasks.append(res_subtask)

        # 3. Development / Implementation node
        dev_subtask = SubTask(
            title="Execute Implementation & Apply File Changes",
            assigned_agent=AgentRole.DEVELOPMENT_AGENT,
            depends_on=[res_subtask.id],
            required_permissions=["workspace.read", "workspace.write"],
            input_context={
                "goal": task_spec.goal,
                "acceptance_criteria": task_spec.acceptance_criteria
            }
        )
        subtasks.append(dev_subtask)

        # 4. QA Verification node
        qa_subtask = SubTask(
            title="Run Acceptance & Regression Test Suite",
            assigned_agent=AgentRole.QA_AGENT,
            depends_on=[dev_subtask.id],
            required_permissions=["workspace.read", "terminal.execute"],
            input_context={
                "acceptance_criteria": task_spec.acceptance_criteria
            }
        )
        subtasks.append(qa_subtask)

        # 5. Final Synthesis / Orchestrator reporting node
        synth_subtask = SubTask(
            title="Consolidate Execution Evidence & Produce Final Report",
            assigned_agent=AgentRole.ORCHESTRATOR,
            depends_on=[qa_subtask.id],
            required_permissions=["workspace.read"],
            input_context={
                "task_id": task_spec.task_id
            }
        )
        subtasks.append(synth_subtask)

        plan = TaskDAGPlan(
            task_id=task_spec.task_id,
            workspace_id=task_spec.workspace_id,
            subtasks=subtasks,
            status="ready"
        )
        return plan
