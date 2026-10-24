import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings
from backend.core.database import init_db
from backend.modules.workspace.manager import WorkspaceManager
from backend.modules.execution.broker import ExecutionBroker, CheckpointManager, AuditLogger

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    asyncio.run(init_db())

@pytest.mark.asyncio
async def test_file_write_diff_and_rollback():
    """Verify safe file write, automatic diff creation, checkpoint generation, and rollback."""
    workspace_path = str(settings.BASE_DIR)
    ws = await WorkspaceManager.open_workspace(workspace_path)
    test_rel_path = "temp_test_runs/test_sandbox_file.txt"

    # 1. Create file
    content_v1 = "Line 1: Initial content\nLine 2: Important configuration"
    res_v1 = await ExecutionBroker.write_file(ws["id"], workspace_path, test_rel_path, content_v1)
    assert res_v1["action"] == "create"
    assert res_v1["checkpoint_id"] is not None
    assert Path(res_v1["absolute_path"]).read_text(encoding="utf-8") == content_v1

    # 2. Modify file
    content_v2 = "Line 1: Initial content\nLine 2: Modified configuration!\nLine 3: Extra line"
    res_v2 = await ExecutionBroker.write_file(ws["id"], workspace_path, test_rel_path, content_v2)
    assert res_v2["action"] == "modify"
    assert "Modified configuration!" in res_v2["diff"]
    checkpoint_v2 = res_v2["checkpoint_id"]

    # 3. Rollback to v1 state using checkpoint_v2
    rollback_res = await CheckpointManager.rollback(checkpoint_v2)
    assert rollback_res["restored"] is True
    assert Path(res_v1["absolute_path"]).read_text(encoding="utf-8") == content_v1

    # 4. Cleanup via safe delete
    del_res = await ExecutionBroker.delete_file(ws["id"], workspace_path, test_rel_path)
    assert del_res["deleted"] is True
    assert not Path(res_v1["absolute_path"]).exists()

@pytest.mark.asyncio
async def test_path_traversal_is_blocked():
    """Verify that writing or deleting files outside workspace boundary is blocked."""
    workspace_path = str(settings.BASE_DIR)
    ws = await WorkspaceManager.open_workspace(workspace_path)

    # Path traversal write
    with pytest.raises(PermissionError):
        await ExecutionBroker.write_file(ws["id"], workspace_path, r"..\..\outside.txt", "Malicious")

    # Path traversal delete
    with pytest.raises(PermissionError):
        await ExecutionBroker.delete_file(ws["id"], workspace_path, r"C:\Windows\System32\calc.exe")

@pytest.mark.asyncio
async def test_command_sandbox_allowlist_and_injection_guard():
    """Verify command allowlist, argument isolation, and prevention of command injection."""
    workspace_path = str(settings.BASE_DIR)
    ws = await WorkspaceManager.open_workspace(workspace_path)

    # 1. Allowed command runs cleanly
    res = await ExecutionBroker.run_sandboxed_command(
        workspace_id=ws["id"],
        workspace_path=workspace_path,
        executable="python",
        args=["-c", "print('sandbox_test_ok')"]
    )
    assert res["exit_code"] == 0
    assert "sandbox_test_ok" in res["stdout"]

    # 2. Unauthorized executable is denied
    with pytest.raises(PermissionError):
        await ExecutionBroker.run_sandboxed_command(
            workspace_id=ws["id"],
            workspace_path=workspace_path,
            executable="powershell.exe",
            args=["-Command", "Get-Process"]
        )

    # 3. Command injection attempt (shell metacharacters treated as literal string arguments)
    res_inject = await ExecutionBroker.run_sandboxed_command(
        workspace_id=ws["id"],
        workspace_path=workspace_path,
        executable="python",
        args=["-c", "import sys; print(sys.argv[1])", "hello & calc.exe | echo hacked"]
    )
    assert res_inject["exit_code"] == 0
    # The metacharacters remain a harmless literal string
    assert "hello & calc.exe | echo hacked" in res_inject["stdout"]

def test_audit_logger_secret_masking():
    """Verify that secrets (tokens, api keys, passwords) are masked in audit logs."""
    sensitive_cmd = "git clone https://user:ghp_1234567890abcdef123456@github.com/repo.git api_key='sk-abcdef1234567890'"
    masked = AuditLogger.mask_secrets(sensitive_cmd)
    assert "ghp_" not in masked
    assert "sk-" not in masked
    assert "[REDACTED_SECRET]" in masked

def test_api_execution_endpoints():
    """Verify REST API execution endpoints."""
    with TestClient(app) as client:
        # Write
        res_write = client.post("/api/v1/execution/file/write", json={
            "workspace_id": "ws-exec-test",
            "workspace_path": str(settings.BASE_DIR),
            "relative_path": "temp_test_runs/api_test_file.txt",
            "content": "API execution test"
        })
        assert res_write.status_code == 200
        data = res_write.json()["execution"]
        checkpoint_id = data["checkpoint_id"]

        # Rollback
        res_rb = client.post("/api/v1/execution/rollback", json={
            "checkpoint_id": checkpoint_id
        })
        assert res_rb.status_code == 200

        # Run command
        res_cmd = client.post("/api/v1/execution/terminal/run", json={
            "workspace_id": "ws-exec-test",
            "workspace_path": str(settings.BASE_DIR),
            "executable": "git",
            "args": ["--version"]
        })
        assert res_cmd.status_code == 200
        assert "git version" in res_cmd.json()["result"]["stdout"]

        # Audit logs
        res_audit = client.get("/api/v1/execution/audit?workspace_id=ws-exec-test")
        assert res_audit.status_code == 200
        assert len(res_audit.json()["logs"]) >= 1
