import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.database import init_db
from backend.modules.skills.manager import SkillManager
from backend.modules.mcp.manager import MCPManager

client = TestClient(app)

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    await SkillManager.init_builtin_skills()
    await MCPManager.init_default_servers()

@pytest.mark.asyncio
async def test_workspace_projects_and_file_crud(tmp_path):
    ws_dir = tmp_path / "test_project_crud"
    ws_dir.mkdir()

    # 1. Open Workspace
    resp_open = client.post("/api/v1/workspace/open", json={"path": str(ws_dir)})
    assert resp_open.status_code == 200
    ws_id = resp_open.json()["workspace"]["id"]

    # 2. List Workspaces
    resp_list = client.get("/api/v1/workspace/list")
    assert resp_list.status_code == 200
    workspaces = resp_list.json()["workspaces"]
    assert any(w["id"] == ws_id for w in workspaces)

    # 3. Create File in Workspace
    resp_create_file = client.post("/api/v1/workspace/file/create", json={
        "workspace_path": str(ws_dir),
        "relative_path": "src/main.py",
        "content": "print('hello world')\n"
    })
    assert resp_create_file.status_code == 200
    assert (ws_dir / "src" / "main.py").exists()

    # 4. Update File with Checkpoint Diff
    resp_update = client.post("/api/v1/workspace/file/update", json={
        "workspace_id": ws_id,
        "workspace_path": str(ws_dir),
        "relative_path": "src/main.py",
        "content": "print('hello antigravity')\n"
    })
    assert resp_update.status_code == 200
    assert (ws_dir / "src" / "main.py").read_text(encoding="utf-8") == "print('hello antigravity')\n"

    # 5. Rename Item
    resp_rename = client.post("/api/v1/workspace/file/rename", json={
        "workspace_path": str(ws_dir),
        "old_path": "src/main.py",
        "new_path": "src/app.py"
    })
    assert resp_rename.status_code == 200
    assert not (ws_dir / "src" / "main.py").exists()
    assert (ws_dir / "src" / "app.py").exists()

    # 6. Create Directory
    resp_mkdir = client.post("/api/v1/workspace/file/mkdir", json={
        "workspace_path": str(ws_dir),
        "relative_path": "src/components"
    })
    assert resp_mkdir.status_code == 200
    assert (ws_dir / "src" / "components").is_dir()

    # 7. Remove Workspace
    resp_del_ws = client.delete(f"/api/v1/workspace/{ws_id}")
    assert resp_del_ws.status_code == 200

@pytest.mark.asyncio
async def test_skills_engine_and_crud():
    # 1. List skills (built-ins must exist)
    resp_skills = client.get("/api/v1/skills")
    assert resp_skills.status_code == 200
    skills = resp_skills.json()["skills"]
    assert len(skills) >= 16
    names = {s["name"] for s in skills}
    assert "clean-code" in names
    assert "systematic-debugging" in names
    assert "codebase-mindmap-sentinel" in names
    assert "anti-hallucination-grounding" in names
    assert "anti-ui-slop" in names
    assert "codebase-design" in names
    assert "repo-tool-safety-license-auditor" in names

    # 2. Create Custom Skill
    resp_create = client.post("/api/v1/skills", json={
        "name": "custom-domain-skill",
        "description": "A custom user skill for domain testing",
        "instructions": "# Custom Instructions\nFollow domain patterns strictly."
    })
    assert resp_create.status_code == 200
    skill_id = resp_create.json()["skill"]["id"]

    # 3. Get Custom Skill
    resp_get = client.get(f"/api/v1/skills/{skill_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["skill"]["name"] == "custom-domain-skill"

    # 4. Toggle Skill
    resp_toggle = client.post(f"/api/v1/skills/{skill_id}/toggle", json={"enabled": False})
    assert resp_toggle.status_code == 200
    assert resp_toggle.json()["enabled"] is False

    # 5. Delete Custom Skill
    resp_delete = client.delete(f"/api/v1/skills/{skill_id}")
    assert resp_delete.status_code == 200

    # 6. Deleting built-in skill must be blocked
    clean_code_skill = next(s for s in skills if s["name"] == "clean-code")
    resp_del_builtin = client.delete(f"/api/v1/skills/{clean_code_skill['id']}")
    assert resp_del_builtin.status_code == 400

@pytest.mark.asyncio
async def test_mcp_servers_and_tool_execution():
    # 1. List MCP servers
    resp_servers = client.get("/api/v1/mcp/servers")
    assert resp_servers.status_code == 200
    servers = resp_servers.json()["servers"]
    assert len(servers) >= 8
    server_names = {s["name"] for s in servers}
    assert "local-filesystem" in server_names
    assert "sqlite-inspector" in server_names
    assert "git-sentinel" in server_names
    assert "code-syntax-ast-analyzer" in server_names
    assert "dependency-security-auditor" in server_names
    assert "test-runner-diagnostics" in server_names
    assert "env-config-guard" in server_names
    assert "web-knowledge-crawler" in server_names

    # 2. Add New MCP Server
    resp_add = client.post("/api/v1/mcp/servers", json={
        "name": "custom-sqlite-mcp",
        "command": "python",
        "args": ["-m", "sqlite_mcp"],
        "transport": "stdio"
    })
    assert resp_add.status_code == 200
    server_id = resp_add.json()["server"]["id"]

    # 3. Ping / Test connection
    resp_ping = client.post(f"/api/v1/mcp/servers/{server_id}/ping")
    assert resp_ping.status_code == 200
    assert resp_ping.json()["connection"]["status"] == "connected"

    # 4. Execute MCP tool
    resp_exec = client.post(f"/api/v1/mcp/servers/{server_id}/execute", json={
        "tool_name": "query_readonly",
        "arguments": {"sql": "SELECT 1"}
    })
    assert resp_exec.status_code == 200
    assert resp_exec.json()["execution"]["status"] == "success"

    # 5. Delete MCP Server
    resp_del = client.delete(f"/api/v1/mcp/servers/{server_id}")
    assert resp_del.status_code == 200

@pytest.mark.asyncio
async def test_system_drives_and_directory_explorer(tmp_path):
    # 1. Test get drives
    resp_drives = client.get("/api/v1/system/drives")
    assert resp_drives.status_code == 200
    drives = resp_drives.json()["drives"]
    assert isinstance(drives, list)
    assert len(drives) > 0

    # 2. Test browse directory
    test_dir = tmp_path / "browse_test"
    test_dir.mkdir()
    (test_dir / "subfolder_a").mkdir()
    (test_dir / "subfolder_b").mkdir()
    (test_dir / "file.txt").write_text("hello")

    resp_browse = client.post("/api/v1/system/browse-directory", json={"path": str(test_dir)})
    assert resp_browse.status_code == 200
    data = resp_browse.json()
    assert data["status"] == "ok"
    assert data["current_path"] == str(test_dir)
    dir_names = [d["name"] for d in data["directories"]]
    assert "subfolder_a" in dir_names
    assert "subfolder_b" in dir_names
    assert "file.txt" not in dir_names

    # 3. Test create directory on disk
    resp_create = client.post("/api/v1/system/create-directory", json={
        "parent_path": str(test_dir),
        "folder_name": "new_project_dir"
    })
    assert resp_create.status_code == 200
    assert (test_dir / "new_project_dir").is_dir()
