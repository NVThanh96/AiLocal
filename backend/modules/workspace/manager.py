import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiosqlite

from backend.core.config import settings
from backend.core.database import get_db_connection
from backend.modules.security.broker import SecurityBroker

IGNORED_DIRECTORIES = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", "dist", "build", "target", ".idea", ".vscode",
    "temp_test_runs"
}

IGNORED_EXTENSIONS = {
    ".pyc", ".pyo", ".exe", ".dll", ".so", ".bin", ".iso", ".zip",
    ".tar", ".gz", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mp3"
}

class WorkspaceManager:
    """Manages workspace lifecycle, directory scanning, and FTS5 full-text indexing."""

    @classmethod
    async def open_workspace(cls, workspace_path: str) -> Dict[str, Any]:
        """Validate and open a workspace directory, registering it into SQLite."""
        path_obj = Path(workspace_path).resolve()
        if not path_obj.exists() or not path_obj.is_dir():
            raise ValueError(f"Directory does not exist or is not a directory: {workspace_path}")

        workspace_id = str(uuid.uuid5(uuid.NAMESPACE_URL, str(path_obj)))
        workspace_name = path_obj.name or str(path_obj)

        conn = await get_db_connection()
        try:
            await conn.execute("""
                INSERT INTO workspaces (id, path, name, last_opened_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(path) DO UPDATE SET last_opened_at = CURRENT_TIMESTAMP;
            """, (workspace_id, str(path_obj), workspace_name))
            await conn.commit()
            
            # Asynchronously index workspace files into FTS5
            await cls.index_workspace(workspace_id, path_obj)
        finally:
            await conn.close()

        return {
            "id": workspace_id,
            "name": workspace_name,
            "path": str(path_obj)
        }

    @classmethod
    def get_file_tree(cls, workspace_path: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Scan workspace directory and return a hierarchical tree structure."""
        root = Path(workspace_path).resolve()
        if not root.exists():
            return []

        def scan_dir(current_dir: Path, current_depth: int) -> List[Dict[str, Any]]:
            if current_depth > max_depth:
                return []
            
            items = []
            try:
                for entry in sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                    if entry.name in IGNORED_DIRECTORIES:
                        continue
                    if entry.is_dir():
                        children = scan_dir(entry, current_depth + 1)
                        items.append({
                            "name": entry.name,
                            "path": str(entry.relative_to(root)),
                            "type": "directory",
                            "children": children
                        })
                    else:
                        items.append({
                            "name": entry.name,
                            "path": str(entry.relative_to(root)),
                            "type": "file",
                            "size": entry.stat().st_size
                        })
            except PermissionError:
                pass
            return items

        return scan_dir(root, 1)

    @classmethod
    async def index_workspace(cls, workspace_id: str, root_path: Path):
        """Index text documents within the workspace using SQLite FTS5."""
        conn = await get_db_connection()
        try:
            # Clear old index for this workspace
            await conn.execute("DELETE FROM workspace_documents WHERE workspace_id = ?;", (workspace_id,))
            
            for path in root_path.rglob("*"):
                if any(part in IGNORED_DIRECTORIES for part in path.parts):
                    continue
                if path.is_file() and path.suffix.lower() not in IGNORED_EXTENSIONS:
                    if path.stat().st_size <= settings.MAX_FILE_READ_BYTES:
                        try:
                            content = path.read_text(encoding="utf-8", errors="ignore")
                            rel_path = str(path.relative_to(root_path)).replace("\\", "/")
                            if rel_path.startswith("storage/") or rel_path.endswith((".db", ".db-journal")):
                                continue
                            await conn.execute("""
                                INSERT INTO workspace_documents(workspace_id, file_path, file_name, content)
                                VALUES (?, ?, ?, ?);
                            """, (workspace_id, rel_path, path.name, content))
                        except Exception:
                            pass
            await conn.commit()
        finally:
            await conn.close()

    @classmethod
    async def search_workspace(cls, workspace_id: str, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Full-text search inside workspace documents using FTS5 BM25 ranking."""
        conn = await get_db_connection()
        try:
            cursor = await conn.execute("""
                SELECT file_path, file_name, snippet(workspace_documents, 3, '<mark>', '</mark>', '...', 12) as match_snippet, bm25(workspace_documents) as rank
                FROM workspace_documents
                WHERE workspace_id = ? AND workspace_documents MATCH ?
                  AND file_path NOT LIKE 'storage/%'
                  AND file_name NOT LIKE '%.db%'
                ORDER BY rank
                LIMIT ?;
            """, (workspace_id, query, limit))
            rows = await cursor.fetchall()
            return [
                {
                    "file_path": row["file_path"].replace("\\", "/"),
                    "file_name": row["file_name"],
                    "snippet": row["match_snippet"],
                    "score": round(row["rank"], 4)
                }
                for row in rows
            ]
        finally:
            await conn.close()

    @classmethod
    def read_file(cls, workspace_path: str, relative_path: str) -> Dict[str, Any]:
        """Safely read a file within workspace boundary (Read-Only)."""
        is_safe, resolved_path = SecurityBroker.validate_workspace_path(relative_path, workspace_path)
        if not is_safe:
            raise PermissionError(f"Access denied: Path '{relative_path}' is outside workspace boundary.")

        if not resolved_path.exists() or not resolved_path.is_file():
            raise FileNotFoundError(f"File not found: {relative_path}")

        file_size = resolved_path.stat().st_size
        if file_size > settings.MAX_FILE_READ_BYTES:
            raise ValueError(f"File size exceeds safety limit ({file_size} > {settings.MAX_FILE_READ_BYTES} bytes)")

        content = resolved_path.read_text(encoding="utf-8", errors="replace")
        return {
            "path": relative_path.replace("\\", "/"),
            "absolute_path": str(resolved_path),
            "size": file_size,
            "content": content
        }

    @classmethod
    async def list_workspaces(cls) -> List[Dict[str, Any]]:
        """List all previously opened workspaces/projects, pruning non-existent ones."""
        conn = await get_db_connection()
        try:
            cursor = await conn.execute(
                "SELECT id, path, name, created_at, last_opened_at FROM workspaces ORDER BY last_opened_at DESC"
            )
            rows = await cursor.fetchall()
            valid_workspaces = []
            for r in rows:
                if Path(r["path"]).exists():
                    valid_workspaces.append({
                        "id": r["id"],
                        "path": r["path"],
                        "name": r["name"],
                        "created_at": r["created_at"],
                        "last_opened_at": r["last_opened_at"]
                    })
                else:
                    await conn.execute("DELETE FROM workspaces WHERE id = ?", (r["id"],))
            await conn.commit()
            return valid_workspaces
        finally:
            await conn.close()

    @classmethod
    async def remove_workspace(cls, workspace_id: str) -> bool:
        """Remove a workspace from the registered projects list."""
        conn = await get_db_connection()
        try:
            await conn.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))
            await conn.commit()
            return True
        finally:
            await conn.close()

    @classmethod
    async def create_new_workspace(cls, parent_path: str, folder_name: str) -> Dict[str, Any]:
        """Create a new project folder on disk and register it."""
        target = (Path(parent_path) / folder_name).resolve()
        target.mkdir(parents=True, exist_ok=True)
        return await cls.open_workspace(str(target))

    @classmethod
    async def create_file(cls, workspace_path: str, relative_path: str, initial_content: str = "") -> Dict[str, Any]:
        """Create a new file within workspace boundary."""
        is_safe, resolved_path = SecurityBroker.validate_workspace_path(relative_path, workspace_path)
        if not is_safe:
            raise PermissionError(f"Access denied: '{relative_path}' is outside workspace boundary.")
        if resolved_path.exists():
            raise FileExistsError(f"File already exists: {relative_path}")

        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(initial_content, encoding="utf-8")
        return {"path": relative_path, "size": len(initial_content)}

    @classmethod
    async def create_directory(cls, workspace_path: str, relative_path: str) -> Dict[str, Any]:
        """Create a new directory within workspace boundary."""
        is_safe, resolved_path = SecurityBroker.validate_workspace_path(relative_path, workspace_path)
        if not is_safe:
            raise PermissionError(f"Access denied: '{relative_path}' is outside workspace boundary.")
        resolved_path.mkdir(parents=True, exist_ok=True)
        return {"path": relative_path, "type": "directory"}

    @classmethod
    async def rename_item(cls, workspace_path: str, old_path: str, new_path: str) -> Dict[str, Any]:
        """Rename a file or folder within workspace boundary."""
        is_safe_old, resolved_old = SecurityBroker.validate_workspace_path(old_path, workspace_path)
        is_safe_new, resolved_new = SecurityBroker.validate_workspace_path(new_path, workspace_path)
        if not is_safe_old or not is_safe_new:
            raise PermissionError("Access denied: path outside workspace boundary.")
        if not resolved_old.exists():
            raise FileNotFoundError(f"Source not found: {old_path}")
        if resolved_new.exists():
            raise FileExistsError(f"Target already exists: {new_path}")

        resolved_old.rename(resolved_new)
        return {"old_path": old_path, "new_path": new_path}

