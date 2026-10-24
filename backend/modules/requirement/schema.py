from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import time

class TaskStatus(str, Enum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNSUPPORTED = "UNSUPPORTED"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class VerifiedFact(BaseModel):
    fact: str
    source_file: str
    snippet: Optional[str] = None

class UnresolvedQuestion(BaseModel):
    id: str
    question: str
    reason: str
    suggested_options: List[str] = []
    answered: bool = False
    chosen_option: Optional[str] = None

class TaskSpecification(BaseModel):
    task_id: str
    workspace_id: str
    request_version: int = 1
    status: TaskStatus
    goal: str
    original_prompt: str
    normalized_prompt: str
    scope: Dict[str, Any] = Field(default_factory=lambda: {
        "allowed_paths": [],
        "target_files": [],
        "banned_actions": []
    })
    constraints: List[str] = []
    verified_facts: List[VerifiedFact] = []
    assumptions: List[str] = []
    unresolved_questions: List[UnresolvedQuestion] = []
    approved_assumptions: List[str] = []
    source_refs: List[str] = []
    acceptance_criteria: List[str] = []
    risk_level: RiskLevel = RiskLevel.LOW
    required_permissions: List[str] = []
    dependencies: List[str] = []
    assigned_agent: Optional[str] = "Orchestrator"
    resource_budget: Dict[str, Any] = Field(default_factory=lambda: {
        "max_duration_seconds": 300,
        "max_tool_calls": 20,
        "max_files_modified": 5
    })
    created_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    updated_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    execution_evidence: List[Dict[str, Any]] = []
    final_report: Optional[str] = None
