import re
import sys
from typing import Dict, Any, Optional
from backend.modules.execution.broker import ExecutionBroker
from backend.modules.memory.engine import MemoryEngine

class QADevAgent:
    """
    Automated QA and Development Agent:
    - Executes test suites in sandboxed environment.
    - Captures exit codes, passes, and failures.
    - Integrates with Error Memory to prevent regression.
    """

    @classmethod
    async def run_tests(
        cls,
        workspace_id: str,
        workspace_path: str,
        test_path: str = "tests"
    ) -> Dict[str, Any]:
        pytest_exe = sys.executable.replace("python.exe", "pytest.exe")
        
        res = await ExecutionBroker.run_sandboxed_command(
            workspace_id=workspace_id,
            workspace_path=workspace_path,
            executable=pytest_exe,
            args=[test_path, "-v", "--tb=short"],
            timeout_seconds=60
        )

        stdout = res["stdout"]
        exit_code = res["exit_code"]

        passed_match = re.search(r'(\d+)\s+passed', stdout)
        failed_match = re.search(r'(\d+)\s+failed', stdout)

        passed_count = int(passed_match.group(1)) if passed_match else 0
        failed_count = int(failed_match.group(1)) if failed_match else 0

        similar_fix = None
        if exit_code != 0 and failed_count > 0:
            # Query Error Memory for known solutions
            similar_fix = await MemoryEngine.find_similar_error(workspace_id, res["stderr"] or stdout)

        return {
            "status": "PASSED" if exit_code == 0 else "FAILED",
            "exit_code": exit_code,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "duration_ms": res["duration_ms"],
            "stdout": stdout,
            "has_known_fix": similar_fix is not None,
            "suggested_fix": similar_fix.get("verified_patch") if similar_fix else None
        }
