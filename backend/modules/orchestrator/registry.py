from enum import Enum
from typing import Dict, List, Set, Optional
from pydantic import BaseModel, Field

class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCH_AGENT = "research_agent"
    DEVELOPMENT_AGENT = "development_agent"
    QA_AGENT = "qa_agent"
    SECURITY_REVIEWER = "security_reviewer"

class AgentProfile(BaseModel):
    role: AgentRole
    name: str
    description: str
    allowed_permissions: Set[str]
    capabilities: List[str]
    max_concurrency: int = 1

AGENT_REGISTRY: Dict[AgentRole, AgentProfile] = {
    AgentRole.ORCHESTRATOR: AgentProfile(
        role=AgentRole.ORCHESTRATOR,
        name="Orchestrator Specialist",
        description="Coordinates multi-agent DAG execution, state reconciliation, and final synthesis reporting.",
        allowed_permissions={"workspace.read"},
        capabilities=["dag_planning", "task_dispatching", "state_reconciliation", "synthesis_reporting"],
        max_concurrency=1
    ),
    AgentRole.SECURITY_REVIEWER: AgentProfile(
        role=AgentRole.SECURITY_REVIEWER,
        name="Security Reviewer",
        description="Audits planned actions, permission boundaries, command injection guards, and approval gates.",
        allowed_permissions={"workspace.read"},
        capabilities=["security_audit", "permission_verification", "risk_classification", "secret_leak_audit"],
        max_concurrency=2
    ),
    AgentRole.RESEARCH_AGENT: AgentProfile(
        role=AgentRole.RESEARCH_AGENT,
        name="Research Specialist",
        description="Gathers codebase context, doc verification, crawl intelligence, and factual citation extraction.",
        allowed_permissions={"workspace.read", "network.fetch"},
        capabilities=["workspace_search", "document_extraction", "provenance_tracking", "source_verification"],
        max_concurrency=2
    ),
    AgentRole.DEVELOPMENT_AGENT: AgentProfile(
        role=AgentRole.DEVELOPMENT_AGENT,
        name="Development Specialist",
        description="Generates precise file diffs, executes verified modifications via ExecutionBroker, and applies patches.",
        allowed_permissions={"workspace.read", "workspace.write", "terminal.execute"},
        capabilities=["code_generation", "diff_patching", "atomic_write", "rollback_execution"],
        max_concurrency=1
    ),
    AgentRole.QA_AGENT: AgentProfile(
        role=AgentRole.QA_AGENT,
        name="QA & Test Specialist",
        description="Executes automated test suites, verifies zero-regression, and captures execution evidence.",
        allowed_permissions={"workspace.read", "terminal.execute"},
        capabilities=["test_execution", "regression_verification", "assertion_audit", "test_report_generation"],
        max_concurrency=1
    )
}

def get_agent_profile(role: str) -> Optional[AgentProfile]:
    try:
        agent_role = AgentRole(role)
        return AGENT_REGISTRY.get(agent_role)
    except ValueError:
        return None

def validate_agent_permission(role: str, permission: str) -> bool:
    """
    Guarantees no agent can escalate its permissions beyond its registered profile.
    """
    profile = get_agent_profile(role)
    if not profile:
        return False
    return permission in profile.allowed_permissions

def list_agent_profiles() -> List[Dict]:
    return [
        {
            "role": p.role.value,
            "name": p.name,
            "description": p.description,
            "allowed_permissions": list(p.allowed_permissions),
            "capabilities": p.capabilities,
            "max_concurrency": p.max_concurrency
        }
        for p in AGENT_REGISTRY.values()
    ]
