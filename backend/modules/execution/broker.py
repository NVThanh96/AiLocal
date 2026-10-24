import os
import re
import uuid
import time
import shutil
import difflib
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from backend.core.config import settings
from backend.core.database import get_db_connection
from backend.modules.security.broker import SecurityBroker

# Permitted terminal executables allowlist (strictly no raw shell interpreters)
ALLOWED_EXECUTABLES = {
    "python": [r".*\.venv\\Scripts\\python\.exe", r".*python\.exe", r"python"],
    "pytest": [r".*\.venv\\Scripts\\pytest\.exe", r".*pytest\.exe", r"pytest"],
    "pip": [r".*\.venv\\Scripts\\pip\.exe", r".*pip\.exe", r"pip"],
    "node": [r".*node\.exe", r"node"],
    "npm": [r".*npm\.cmd", r".*npm\.exe", r"npm"],
    "git": [r".*git\.exe", r"git"]
}

SECRET_PATTERNS = [
    r"ghp_[a-zA-Z0-9]{15,}",
    r"sk-[a-zA-Z0-9_\-]{15,}",
    r"(?i)https?://[^:\s]+:([^@\s]+)@",
    r"(?i)api[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?",
    r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})",
    r"(?i)password\s*[:=]\s*['\"]?([^'\"\s]+)['\"]?",
    r"(?i)token\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?"
]

class AuditLogger:
    """Audit logger recording security and side-effect events with secret sanitization."""

    @staticmethod
    def mask_secrets(text: str) -> str:
        masked = text
        for pat in SECRET_PATTERNS:
            masked = re.sub(pat, r"[REDACTED_SECRET]", masked)
        return masked

    @classmethod
    async def log_event(
        cls,
        action: str,
        target: str,
        status: str,
        workspace_id: Optional[str] = None,
        exit_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        event_id = str(uuid.uuid4())
        safe_target = cls.mask_secrets(target)
        details_str = cls.mask_secrets(json_dumps_safe(details or {}))

        conn = await get_db_connection()
        try:
            await conn.execute("""
                INSERT INTO audit_logs (id, workspace_id, action, target, status, exit_code, duration_ms, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (event_id, workspace_id, action, safe_target, status, exit_code, duration_ms, details_str))
            await conn.commit()
            return event_id
        finally:
            await conn.close()

def json_dumps_safe(obj: Any) -> str:
    import json
    return json.dumps(obj, default=str)

class CheckpointManager:
    """Manages pre-modification file snapshots for rollback safety."""

    CHECKPOINT_DIR = settings.STORAGE_DIR / "checkpoints"

    @classmethod
    def _ensure_dir(cls):
        cls.CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    async def create_checkpoint(cls, workspace_id: str, resolved_file: Path, action: str) -> str:
        cls._ensure_dir()
        checkpoint_id = str(uuid.uuid4())
        backup_file = cls.CHECKPOINT_DIR / f"{checkpoint_id}_{resolved_file.name}"

        # If file currently exists, back it up. If creating new file, mark empty.
        if resolved_file.exists():
            shutil.copy2(resolved_file, backup_file)
        else:
            backup_file.touch()

        conn = await get_db_connection()
        try:
            await conn.execute("""
                INSERT INTO checkpoints (id, workspace_id, file_path, backup_path, action)
                VALUES (?, ?, ?, ?, ?);
            """, (checkpoint_id, workspace_id, str(resolved_file), str(backup_file), action))
            await conn.commit()
            return checkpoint_id
        finally:
            await conn.close()

    @classmethod
    async def rollback(cls, checkpoint_id: str) -> Dict[str, Any]:
        conn = await get_db_connection()
        try:
            cursor = await conn.execute("""
                SELECT workspace_id, file_path, backup_path, action
                FROM checkpoints
                WHERE id = ?;
            """, (checkpoint_id,))
            row = await cursor.fetchone()
            if not row:
                raise ValueError(f"Checkpoint '{checkpoint_id}' not found.")

            target_file = Path(row["file_path"])
            backup_file = Path(row["backup_path"])

            if row["action"] == "create":
                # Created new file, rollback by removing it
                if target_file.exists():
                    target_file.unlink()
            else:
                # Modified or deleted file, restore from backup
                if backup_file.exists():
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_file, target_file)

            await AuditLogger.log_event(
                action="checkpoint.rollback",
                target=str(target_file),
                status="SUCCESS",
                workspace_id=row["workspace_id"],
                details={"checkpoint_id": checkpoint_id, "original_action": row["action"]}
            )

            return {
                "checkpoint_id": checkpoint_id,
                "file_path": str(target_file),
                "restored": True
            }
        finally:
            await conn.close()

class ExecutionBroker:
    """
    Central Execution Broker:
    - Path normalization and boundary validation.
    - Automated pre-execution diff generation.
    - Atomic checkpointing and rollback support.
    - Terminal command sandbox with executable allowlist.
    """

    @staticmethod
    def generate_diff(original_content: str, new_content: str, filename: str = "file") -> str:
        orig_lines = original_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines, new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}"
        )
        return "".join(diff)

    @classmethod
    async def write_file(
        cls,
        workspace_id: str,
        workspace_path: str,
        relative_path: str,
        new_content: str
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        is_safe, resolved_path = SecurityBroker.validate_workspace_path(relative_path, workspace_path)
        if not is_safe:
            await AuditLogger.log_event("file.write", relative_path, "DENIED_PATH_TRAVERSAL", workspace_id)
            raise PermissionError(f"Security Alert: Path '{relative_path}' violates workspace boundary.")

        action = "modify" if resolved_path.exists() else "create"
        old_content = resolved_path.read_text(encoding="utf-8", errors="replace") if resolved_path.exists() else ""
        diff_text = cls.generate_diff(old_content, new_content, resolved_path.name)

        # 1. Create checkpoint
        checkpoint_id = await CheckpointManager.create_checkpoint(workspace_id, resolved_path, action)

        # 2. Write file safely
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(new_content, encoding="utf-8")

        duration = (time.perf_counter() - start) * 1000
        await AuditLogger.log_event(
            action="file.write",
            target=str(resolved_path),
            status="SUCCESS",
            workspace_id=workspace_id,
            duration_ms=round(duration, 2),
            details={"checkpoint_id": checkpoint_id, "action": action, "size": len(new_content)}
        )

        return {
            "path": relative_path,
            "absolute_path": str(resolved_path),
            "action": action,
            "checkpoint_id": checkpoint_id,
            "diff": diff_text
        }

    @classmethod
    async def delete_file(
        cls,
        workspace_id: str,
        workspace_path: str,
        relative_path: str
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        is_safe, resolved_path = SecurityBroker.validate_workspace_path(relative_path, workspace_path)
        if not is_safe:
            await AuditLogger.log_event("file.delete", relative_path, "DENIED_PATH_TRAVERSAL", workspace_id)
            raise PermissionError(f"Security Alert: Path '{relative_path}' violates workspace boundary.")

        if not resolved_path.exists():
            raise FileNotFoundError(f"File '{relative_path}' not found.")

        # 1. Create checkpoint before delete
        checkpoint_id = await CheckpointManager.create_checkpoint(workspace_id, resolved_path, "delete")

        # 2. Delete file
        resolved_path.unlink()

        duration = (time.perf_counter() - start) * 1000
        await AuditLogger.log_event(
            action="file.delete",
            target=str(resolved_path),
            status="SUCCESS",
            workspace_id=workspace_id,
            duration_ms=round(duration, 2),
            details={"checkpoint_id": checkpoint_id}
        )

        return {
            "path": relative_path,
            "absolute_path": str(resolved_path),
            "deleted": True,
            "checkpoint_id": checkpoint_id
        }

    @classmethod
    async def run_sandboxed_command(
        cls,
        workspace_id: str,
        workspace_path: str,
        executable: str,
        args: List[str],
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Executes a command safely inside the sandbox:
        - Only allowlisted executables.
        - Strict argument array (no shell string concatenation, shell=False).
        - Working directory confined to workspace.
        """
        start = time.perf_counter()

        # Check executable allowlist
        exec_lower = executable.lower().strip()
        matched = False
        for allowed_key, patterns in ALLOWED_EXECUTABLES.items():
            if allowed_key == exec_lower or any(re.match(p, exec_lower) for p in patterns):
                matched = True
                break

        if not matched:
            await AuditLogger.log_event("terminal.execute", executable, "DENIED_UNAUTHORIZED_EXECUTABLE", workspace_id)
            raise PermissionError(f"Execution Denied: '{executable}' is not in the allowed executable sandbox registry.")

        # Verify cwd boundary
        root = Path(workspace_path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Workspace cwd does not exist: {workspace_path}")

        # Assemble command array
        cmd = [executable] + args

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(root),
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            duration = (time.perf_counter() - start) * 1000

            stdout_clean = AuditLogger.mask_secrets(proc.stdout)
            stderr_clean = AuditLogger.mask_secrets(proc.stderr)

            await AuditLogger.log_event(
                action="terminal.execute",
                target=" ".join(cmd),
                status="SUCCESS" if proc.returncode == 0 else "FAILED",
                workspace_id=workspace_id,
                exit_code=proc.returncode,
                duration_ms=round(duration, 2)
            )

            return {
                "command": cmd,
                "exit_code": proc.returncode,
                "stdout": stdout_clean,
                "stderr": stderr_clean,
                "duration_ms": round(duration, 2)
            }
        except subprocess.TimeoutExpired:
            duration = (time.perf_counter() - start) * 1000
            await AuditLogger.log_event(
                action="terminal.execute",
                target=" ".join(cmd),
                status="TIMEOUT",
                workspace_id=workspace_id,
                duration_ms=round(duration, 2)
            )
            raise TimeoutError(f"Command timed out after {timeout_seconds} seconds.")
