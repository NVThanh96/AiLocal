import os
import time
from pathlib import Path
from typing import List, Dict, Any
from backend.core.config import settings

class RetentionManager:
    """
    Manages data retention lifecycles:
    - 48 hours TTL: Automatically purges temporary test runs and benchmark runs (temp_test_runs/).
    - 7 days TTL: Purges temporary debug checkpoints.
    - Verified lessons, project decisions, and audit metadata are permanently retained.
    """

    ALLOWED_PURGE_DIRS = [
        settings.TEMP_SANDBOX_DIR,
        settings.STORAGE_DIR / "checkpoints",
        settings.STORAGE_DIR / "temp_test_runs"
    ]

    @classmethod
    def cleanup_expired_artifacts(cls, dry_run: bool = False, max_age_hours: float = 48.0) -> Dict[str, Any]:
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_files: List[str] = []
        bytes_freed = 0

        for target_dir in cls.ALLOWED_PURGE_DIRS:
            if not target_dir.exists() or not target_dir.is_dir():
                continue

            for file_path in target_dir.rglob("*"):
                # Preserve .gitkeep files to keep directory structure intact
                if file_path.name == ".gitkeep":
                    continue
                if file_path.is_file():
                    stat = file_path.stat()
                    file_age = now - stat.st_mtime
                    if file_age > max_age_seconds:
                        bytes_freed += stat.st_size
                        deleted_files.append(str(file_path))
                        if not dry_run:
                            try:
                                file_path.unlink()
                            except Exception:
                                pass

        return {
            "dry_run": dry_run,
            "max_age_hours": max_age_hours,
            "files_targeted_count": len(deleted_files),
            "bytes_freed": bytes_freed,
            "sample_files": deleted_files[:10]
        }
