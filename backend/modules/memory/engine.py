import re
import uuid
import json
import time
from typing import List, Dict, Any, Optional
from backend.core.database import get_db_connection

class MemoryEngine:
    """
    Unified Memory Layer:
    - Project Memory (Architecture decisions, coding standards).
    - Knowledge Memory (Verified skills, procedures).
    - Error Memory (Error signatures, root causes, regression proofs).
    """

    @staticmethod
    def normalize_error_signature(error_text: str) -> str:
        """Strip memory addresses, timestamps, and line numbers to create stable signature."""
        clean = re.sub(r'0x[0-9a-fA-F]+', '0x...', error_text)
        clean = re.sub(r'\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s]*', '', clean)
        clean = re.sub(r'line \d+', 'line N', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:200]

    # ----------------- Project Memory -----------------
    @classmethod
    async def save_project_decision(cls, workspace_id: str, category: str, title: str, content: str) -> str:
        mem_id = str(uuid.uuid4())
        conn = await get_db_connection()
        try:
            await conn.execute("""
                INSERT INTO project_memory (id, workspace_id, category, title, content)
                VALUES (?, ?, ?, ?, ?);
            """, (mem_id, workspace_id, category, title, content))
            await conn.commit()
            return mem_id
        finally:
            await conn.close()

    @classmethod
    async def get_project_decisions(cls, workspace_id: str) -> List[Dict[str, Any]]:
        conn = await get_db_connection()
        try:
            cursor = await conn.execute("""
                SELECT id, category, title, content, created_at
                FROM project_memory
                WHERE workspace_id = ?
                ORDER BY created_at DESC;
            """, (workspace_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    # ----------------- Error Memory -----------------
    @classmethod
    async def record_error(
        cls,
        workspace_id: str,
        raw_error: str,
        root_cause: Optional[str] = None,
        attempted_fixes: Optional[List[str]] = None,
        verified_patch: Optional[str] = None,
        regression_test: Optional[str] = None,
        is_verified: bool = False
    ) -> str:
        error_id = str(uuid.uuid4())
        signature = cls.normalize_error_signature(raw_error)
        fixes_json = json.dumps(attempted_fixes or [], default=str)

        conn = await get_db_connection()
        try:
            await conn.execute("""
                INSERT INTO error_memory (id, workspace_id, error_signature, environment_context, root_cause, attempted_fixes, verified_patch, regression_test, is_verified)
                VALUES (?, ?, ?, 'Windows 11 / Python 3.12 / Local GPU', ?, ?, ?, ?, ?);
            """, (error_id, workspace_id, signature, root_cause, fixes_json, verified_patch, regression_test, 1 if is_verified else 0))
            await conn.commit()
            return error_id
        finally:
            await conn.close()

    @classmethod
    async def find_similar_error(cls, workspace_id: str, raw_error: str) -> Optional[Dict[str, Any]]:
        signature = cls.normalize_error_signature(raw_error)
        conn = await get_db_connection()
        try:
            cursor = await conn.execute("""
                SELECT id, error_signature, root_cause, attempted_fixes, verified_patch, regression_test, is_verified
                FROM error_memory
                WHERE workspace_id = ? AND error_signature = ?
                ORDER BY updated_at DESC LIMIT 1;
            """, (workspace_id, signature))
            row = await cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["attempted_fixes"] = json.loads(res["attempted_fixes"])
            return res
        finally:
            await conn.close()

    @classmethod
    async def upgrade_to_verified_lesson(cls, error_id: str) -> bool:
        """Promote an error patch to verified status after test passes."""
        conn = await get_db_connection()
        try:
            cursor = await conn.execute("SELECT workspace_id, error_signature, verified_patch FROM error_memory WHERE id = ?;", (error_id,))
            row = await cursor.fetchone()
            if not row or not row["verified_patch"]:
                return False

            await conn.execute("UPDATE error_memory SET is_verified = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (error_id,))
            
            # Record in knowledge memory
            knowledge_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO knowledge_memory (id, workspace_id, skill_name, procedure_text, verified, source_ref)
                VALUES (?, ?, ?, ?, 1, ?);
            """, (knowledge_id, row["workspace_id"], f"Fix: {row['error_signature'][:40]}", row["verified_patch"], f"error_id:{error_id}"))
            await conn.commit()
            return True
        finally:
            await conn.close()
