import asyncio
import logging
from typing import Optional, Set, Dict
from pathlib import Path
from backend.core.database import get_db_connection

logger = logging.getLogger("orchestrator.file_lock")

class FileLockManager:
    """
    Manages concurrent file access across multi-agent executions.
    Guarantees no two agents write to the same file simultaneously.
    Provides re-entrant locking per subtask and persistent tracking.
    """
    def __init__(self):
        self._in_memory_locks: Dict[str, str] = {}  # canonical_path -> locked_by_subtask
        self._async_locks: Dict[str, asyncio.Lock] = {}

    def _normalize_path(self, file_path: str) -> str:
        return str(Path(file_path).resolve()).lower()

    async def acquire_lock(self, file_path: str, locked_by: str, timeout: float = 5.0) -> bool:
        norm_path = self._normalize_path(file_path)
        
        # Check re-entrancy
        if self._in_memory_locks.get(norm_path) == locked_by:
            return True

        if norm_path not in self._async_locks:
            self._async_locks[norm_path] = asyncio.Lock()

        try:
            acquired = await asyncio.wait_for(self._async_locks[norm_path].acquire(), timeout=timeout)
            if acquired:
                self._in_memory_locks[norm_path] = locked_by
                
                # Persist to database
                conn = await get_db_connection()
                try:
                    await conn.execute(
                        "INSERT OR REPLACE INTO file_locks (file_path, locked_by_subtask) VALUES (?, ?)",
                        (norm_path, locked_by)
                    )
                    await conn.commit()
                finally:
                    await conn.close()
                logger.info(f"Lock acquired on {norm_path} by {locked_by}")
                return True
        except asyncio.TimeoutError:
            logger.warning(f"Lock timeout ({timeout}s) on {norm_path} requested by {locked_by}")
            return False
        return False

    async def release_lock(self, file_path: str, locked_by: str) -> bool:
        norm_path = self._normalize_path(file_path)
        if self._in_memory_locks.get(norm_path) != locked_by:
            logger.warning(f"Subtask {locked_by} attempted to release unowned lock on {norm_path}")
            return False

        del self._in_memory_locks[norm_path]
        if norm_path in self._async_locks and self._async_locks[norm_path].locked():
            self._async_locks[norm_path].release()

        conn = await get_db_connection()
        try:
            await conn.execute("DELETE FROM file_locks WHERE file_path = ?", (norm_path,))
            await conn.commit()
        finally:
            await conn.close()
        logger.info(f"Lock released on {norm_path} by {locked_by}")
        return True

    async def release_all_locks(self, locked_by: str) -> int:
        released = 0
        held_paths = [p for p, owner in self._in_memory_locks.items() if owner == locked_by]
        for path in held_paths:
            if await self.release_lock(path, locked_by):
                released += 1
        return released

    def is_locked(self, file_path: str) -> Optional[str]:
        norm_path = self._normalize_path(file_path)
        return self._in_memory_locks.get(norm_path)

file_lock_manager = FileLockManager()
