import uuid
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from backend.core.database import get_db_connection
from backend.modules.workspace.manager import WorkspaceManager
from backend.modules.security.broker import SecurityBroker
from backend.modules.requirement.schema import (
    TaskSpecification, TaskStatus, RiskLevel,
    VerifiedFact, UnresolvedQuestion
)

DESTRUCTIVE_KEYWORDS = {
    "xóa", "delete", "remove", "drop", "purge", "rm", "truncate", "format"
}

HIGH_RISK_PERMISSIONS = {
    "terminal.execute": ["chạy lệnh", "terminal", "exec", "powershell", "bash", "cmd"],
    "workspace.delete": ["xóa file", "delete file", "remove file", "xóa thư mục"],
    "package.install": ["cài đặt", "install package", "pip install", "npm install"],
    "external_data_transfer": ["gửi dữ liệu ra ngoài", "upload", "push"]
}

AMBIGUOUS_PATTERNS = [
    r"sửa lỗi(?!.*trong|.*ở|.*file)",
    r"tối ưu(?!.*trong|.*ở|.*file)",
    r"xóa các file(?!.*tên|.*được chỉ định)",
    r"làm đẹp(?!.*trong|.*ở|.*file)",
    r"fix bugs?(?!.*in|.*file)"
]

class RequirementIntelligenceEngine:
    """
    Requirement Intelligence Engine:
    Executes Step A (Parse) -> Step B (Gather Evidence) -> Step C (Assess Ambiguity)
    -> Step D (Targeted Clarification) -> Step E (Freeze Task Specification).
    """

    @classmethod
    async def analyze_prompt(
        cls,
        workspace_id: str,
        workspace_path: str,
        user_prompt: str,
        existing_task_id: Optional[str] = None
    ) -> TaskSpecification:
        task_id = existing_task_id or str(uuid.uuid4())
        normalized_prompt = user_prompt.strip()

        # ----------------- Step A: Parse -----------------
        prompt_lower = normalized_prompt.lower()
        
        # Detect goal
        goal = normalized_prompt.split(".")[0] if "." in normalized_prompt else normalized_prompt
        
        # Detect required permissions & risk level
        required_permissions = ["workspace.read"]
        risk_level = RiskLevel.LOW
        constraints = [
            "Không can thiệp ngoài thư mục workspace được cấp quyền.",
            "Không tải dữ liệu lên dịch vụ đám mây."
        ]
        banned_actions = []

        is_destructive = any(kw in prompt_lower for kw in DESTRUCTIVE_KEYWORDS)
        if is_destructive:
            risk_level = RiskLevel.HIGH
            required_permissions.append("workspace.delete")
            banned_actions.append("Xóa các file gốc không có bản sao lưu (rollback backup).")

        for perm, triggers in HIGH_RISK_PERMISSIONS.items():
            if any(t in prompt_lower for t in triggers):
                if perm not in required_permissions:
                    required_permissions.append(perm)
                if perm in ("package.install", "terminal.execute", "external_data_transfer"):
                    risk_level = RiskLevel.HIGH

        # Extract potential file paths mentioned in prompt
        # Regex captures words with file extensions or directory paths
        potential_files = re.findall(r'[\w\-./\\]+\.[a-zA-Z0-9]+', user_prompt)

        # ----------------- Step B: Gather Evidence -----------------
        verified_facts: List[VerifiedFact] = []
        source_refs: List[str] = []
        target_files: List[str] = []

        root_path = Path(workspace_path).resolve()

        for file_ref in potential_files:
            clean_ref = file_ref.strip("./\\")
            target_path = root_path / clean_ref
            if target_path.exists() and target_path.is_file():
                stat = target_path.stat()
                verified_facts.append(VerifiedFact(
                    fact=f"Tệp '{clean_ref}' tồn tại trong workspace.",
                    source_file=clean_ref,
                    snippet=f"Kích thước: {stat.st_size} bytes, lần sửa đổi cuối: {time.ctime(stat.st_mtime)}"
                ))
                source_refs.append(clean_ref)
                target_files.append(clean_ref)

        # Query FTS5 for additional relevant files if keywords exist
        keywords = re.findall(r'[\w]+', user_prompt)
        valid_kw = [w for w in keywords if len(w) >= 3][:4]
        if valid_kw:
            try:
                fts_query = " OR ".join([f'"{w}"' for w in valid_kw])
                search_results = await WorkspaceManager.search_workspace(workspace_id, fts_query, limit=3)
                for res in search_results:
                    if res["file_path"] not in source_refs:
                        source_refs.append(res["file_path"])
                        verified_facts.append(VerifiedFact(
                            fact=f"Tìm thấy tệp liên quan '{res['file_name']}' với điểm BM25 {res['score']}.",
                            source_file=res["file_path"],
                            snippet=res["snippet"]
                        ))
            except Exception:
                pass

        # ----------------- Step C: Assess Ambiguity -----------------
        unresolved_questions: List[UnresolvedQuestion] = []
        status = TaskStatus.READY

        # Check for ambiguity patterns
        is_ambiguous = any(re.search(pat, prompt_lower) for pat in AMBIGUOUS_PATTERNS) or (len(normalized_prompt.split()) < 3)

        if is_ambiguous:
            status = TaskStatus.NEEDS_CLARIFICATION
            unresolved_questions.append(UnresolvedQuestion(
                id=str(uuid.uuid4())[:8],
                question="Yêu cầu hiện tại mang tính chung chung. Bạn muốn chỉ định cụ thể các tệp hoặc phạm vi nào?",
                reason="Thiếu phạm vi tác động cụ thể có thể dẫn đến thay đổi sai tệp.",
                suggested_options=[
                    "Áp dụng cho toàn bộ dự án",
                    "Chỉ áp dụng trong thư mục backend/",
                    "Chỉ áp dụng trong thư mục frontend/",
                    "Chỉ xem xét và tạo báo cáo đề xuất (Read-only)"
                ]
            ))
        elif is_destructive or risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            status = TaskStatus.NEEDS_APPROVAL
            constraints.append("Cần người dùng phê duyệt trước khi thực thi các thao tác có side-effect cao.")
        else:
            status = TaskStatus.READY

        # Build acceptance criteria
        acceptance_criteria = [
            f"Thực hiện thành công mục tiêu: '{goal}'",
            "Không phá vỡ các chức năng hiện có của dự án (Zero Regression).",
            "Mọi tệp tạo mới hoặc sửa đổi phải vượt qua bài kiểm tra tính hợp lệ."
        ]
        if target_files:
            acceptance_criteria.append(f"Tác động đúng vào các tệp mục tiêu: {', '.join(target_files)}")

        # ----------------- Step E: Freeze Task Specification -----------------
        task_spec = TaskSpecification(
            task_id=task_id,
            workspace_id=workspace_id,
            request_version=1,
            status=status,
            goal=goal,
            original_prompt=user_prompt,
            normalized_prompt=normalized_prompt,
            scope={
                "allowed_paths": [str(root_path)],
                "target_files": target_files,
                "banned_actions": banned_actions
            },
            constraints=constraints,
            verified_facts=verified_facts,
            assumptions=["Môi trường và các dependency trong workspace giữ nguyên."],
            unresolved_questions=unresolved_questions,
            source_refs=source_refs,
            acceptance_criteria=acceptance_criteria,
            risk_level=risk_level,
            required_permissions=required_permissions
        )

        # Persist task specification to SQLite
        await cls.persist_task(task_spec)
        return task_spec

    @classmethod
    async def persist_task(cls, spec: TaskSpecification):
        """Save task specification and create an immutable version entry."""
        conn = await get_db_connection()
        try:
            spec_json = spec.model_dump_json()
            # Upsert into tasks table
            await conn.execute("""
                INSERT INTO tasks (id, workspace_id, request_version, status, goal, risk_level, spec_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    request_version = excluded.request_version,
                    status = excluded.status,
                    goal = excluded.goal,
                    risk_level = excluded.risk_level,
                    spec_json = excluded.spec_json,
                    updated_at = CURRENT_TIMESTAMP;
            """, (spec.task_id, spec.workspace_id, spec.request_version, spec.status.value, spec.goal, spec.risk_level.value, spec_json))

            # Insert immutable snapshot into task_versions table
            version_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO task_versions (id, task_id, version, status, spec_json)
                VALUES (?, ?, ?, ?, ?);
            """, (version_id, spec.task_id, spec.request_version, spec.status.value, spec_json))

            await conn.commit()
        finally:
            await conn.close()

    @classmethod
    async def get_task(cls, task_id: str) -> Optional[TaskSpecification]:
        """Fetch a task specification by ID."""
        conn = await get_db_connection()
        try:
            cursor = await conn.execute("SELECT spec_json FROM tasks WHERE id = ?;", (task_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return TaskSpecification.model_validate_json(row["spec_json"])
        finally:
            await conn.close()

    @classmethod
    async def get_task_versions(cls, task_id: str) -> List[Dict[str, Any]]:
        """Fetch history of task versions for auditing."""
        conn = await get_db_connection()
        try:
            cursor = await conn.execute("""
                SELECT version, status, spec_json, created_at
                FROM task_versions
                WHERE task_id = ?
                ORDER BY version ASC;
            """, (task_id,))
            rows = await cursor.fetchall()
            return [
                {
                    "version": r["version"],
                    "status": r["status"],
                    "spec": json.loads(r["spec_json"]),
                    "created_at": r["created_at"]
                }
                for r in rows
            ]
        finally:
            await conn.close()

    @classmethod
    async def answer_clarification(
        cls,
        task_id: str,
        question_id: str,
        chosen_option: str
    ) -> TaskSpecification:
        """User answers a clarification question, transitioning task toward READY."""
        spec = await cls.get_task(task_id)
        if not spec:
            raise ValueError(f"Task '{task_id}' not found.")

        # Update answered question
        for q in spec.unresolved_questions:
            if q.id == question_id:
                q.answered = True
                q.chosen_option = chosen_option
                spec.approved_assumptions.append(f"Quyết định người dùng: {q.question} -> '{chosen_option}'")

        # Check if all questions are answered
        remaining_unanswered = [q for q in spec.unresolved_questions if not q.answered]
        if not remaining_unanswered:
            if spec.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                spec.status = TaskStatus.NEEDS_APPROVAL
            else:
                spec.status = TaskStatus.READY

        spec.request_version += 1
        spec.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        await cls.persist_task(spec)
        return spec

    @classmethod
    async def approve_task(cls, task_id: str, approved: bool = True) -> TaskSpecification:
        """User approves or rejects high-risk action, transitioning to READY or BLOCKED."""
        spec = await cls.get_task(task_id)
        if not spec:
            raise ValueError(f"Task '{task_id}' not found.")

        if approved:
            spec.status = TaskStatus.READY
            spec.approved_assumptions.append("Người dùng đã phê duyệt hành động rủi ro cao.")
        else:
            spec.status = TaskStatus.BLOCKED
            spec.constraints.append("Người dùng từ chối cấp quyền phê duyệt hành động.")

        spec.request_version += 1
        spec.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        await cls.persist_task(spec)
        return spec
