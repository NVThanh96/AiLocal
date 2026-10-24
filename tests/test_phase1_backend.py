import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings
from backend.core.database import init_db
from backend.modules.security.broker import SecurityBroker
from backend.modules.workspace.manager import WorkspaceManager
from backend.modules.model.adapter import OllamaAdapter, MockAdapter
from backend.modules.chat.manager import ChatManager

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    asyncio.run(init_db())

def test_security_broker_path_traversal():
    """Verify that path traversal attempts outside workspace are blocked."""
    root = settings.BASE_DIR
    
    # Safe paths
    is_safe, resolved = SecurityBroker.validate_workspace_path("README.md", root)
    assert is_safe
    assert root in resolved.parents or resolved == root

    # Traversal attack
    is_safe_bad, resolved_bad = SecurityBroker.validate_workspace_path(r"..\..\..\Windows\System32", root)
    assert not is_safe_bad

def test_security_broker_ssrf():
    """Verify that SSRF attempts to private networks or loopback are blocked."""
    safe, msg = SecurityBroker.validate_network_url("http://127.0.0.1:8000")
    assert not safe
    
    safe_priv, msg_priv = SecurityBroker.validate_network_url("http://192.168.1.1/setup")
    assert not safe_priv
    
    safe_pub, msg_pub = SecurityBroker.validate_network_url("https://huggingface.co/models")
    assert safe_pub

@pytest.mark.asyncio
async def test_workspace_manager_lifecycle():
    """Test opening workspace, scanning tree, indexing documents and FTS5 search."""
    workspace_path = str(settings.BASE_DIR)
    
    # 1. Open workspace
    res = await WorkspaceManager.open_workspace(workspace_path)
    assert res["id"] is not None
    assert res["name"] is not None
    
    # 2. Get file tree
    tree = WorkspaceManager.get_file_tree(workspace_path)
    assert len(tree) > 0
    # Ensure ignored directories like .git or temp_test_runs are excluded
    item_names = [item["name"] for item in tree]
    assert ".git" not in item_names
    assert "temp_test_runs" not in item_names
    
    # 3. FTS5 Search
    matches = await WorkspaceManager.search_workspace(res["id"], "Ollama OR Workspace", limit=5)
    assert isinstance(matches, list)

@pytest.mark.asyncio
async def test_chat_manager_with_mock():
    """Test conversation creation, message persistence, and mock grounding."""
    workspace_path = str(settings.BASE_DIR)
    ws = await WorkspaceManager.open_workspace(workspace_path)
    
    # Create conversation
    conv = await ChatManager.create_conversation(ws["id"], "Test Conversation")
    assert conv["id"] is not None
    
    # Process message with MockAdapter
    adapter = MockAdapter()
    reply = await ChatManager.process_user_message(
        conversation_id=conv["id"],
        user_prompt="Explain the purpose of this workspace",
        adapter=adapter
    )
    assert reply["role"] == "assistant"
    assert "[MOCK ASSISTANT RESPONSE]" in reply["content"]

    # Verify history
    messages = await ChatManager.get_messages(conv["id"])
    assert len(messages) == 2  # 1 user + 1 assistant
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

def test_fastapi_endpoints():
    """Test REST API endpoints using TestClient."""
    with TestClient(app) as client:
        # Health check
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["ollama"]["online"] is True

        # System info
        res_sys = client.get("/api/v1/system/info")
        assert res_sys.status_code == 200
        sys_data = res_sys.json()
        assert "ram_total_gb" in sys_data
        assert "disk_free_gb" in sys_data

        # Open workspace
        res_ws = client.post("/api/v1/workspace/open", json={"path": str(settings.BASE_DIR)})
        assert res_ws.status_code == 200
        ws_id = res_ws.json()["workspace"]["id"]

        # Tree
        res_tree = client.get(f"/api/v1/workspace/tree?path={settings.BASE_DIR}")
        assert res_tree.status_code == 200
        assert "tree" in res_tree.json()

        # Chat
        res_conv = client.post("/api/v1/chat/conversation", json={"workspace_id": ws_id, "title": "API Test Chat"})
        assert res_conv.status_code == 200
        conv_id = res_conv.json()["conversation"]["id"]

        # Send message with use_mock=True
        res_msg = client.post("/api/v1/chat/message", json={
            "conversation_id": conv_id,
            "content": "Hello AI",
            "use_mock": True
        })
        assert res_msg.status_code == 200
        assert "response" in res_msg.json()
