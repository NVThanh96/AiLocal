import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_file_read_variants_and_size():
    """Verify read_workspace_file handles forward slashes, backslashes and returns real content."""
    variants = [
        "docs/FULL_IMPLEMENTATION_REPORT.md",
        "docs\\FULL_IMPLEMENTATION_REPORT.md",
        "\\docs\\FULL_IMPLEMENTATION_REPORT.md",
        "/docs/FULL_IMPLEMENTATION_REPORT.md"
    ]
    for rel_path in variants:
        res = client.post("/api/v1/workspace/read", json={
            "workspace_path": str(Path.cwd()),
            "relative_path": rel_path
        })
        assert res.status_code == 200, f"Failed on path: {rel_path}"
        data = res.json()["file"]
        assert data["size"] > 1000
        assert "content" in data
        assert len(data["content"]) > 1000
        assert "/" in data["path"] or "\\" not in data["path"]

def test_conversation_crud_lifecycle():
    """Verify conversation creation, rename, listing, and deletion."""
    # 1. Create
    res = client.post("/api/v1/chat/conversation", json={
        "workspace_id": "test_workspace_crud",
        "title": "Initial Session Title"
    })
    assert res.status_code == 200
    conv_id = res.json()["conversation"]["id"]
    assert res.json()["conversation"]["title"] == "Initial Session Title"

    # 2. Rename (PUT)
    res_rename = client.put(f"/api/v1/chat/conversation/{conv_id}", json={
        "title": "Renamed Session Title"
    })
    assert res_rename.status_code == 200
    assert res_rename.json()["title"] == "Renamed Session Title"

    # 3. List
    res_list = client.get(f"/api/v1/chat/conversations?workspace_id=test_workspace_crud")
    assert res_list.status_code == 200
    convs = res_list.json()["conversations"]
    assert any(c["id"] == conv_id and c["title"] == "Renamed Session Title" for c in convs)

    # 4. Delete (DELETE)
    res_del = client.delete(f"/api/v1/chat/conversation/{conv_id}")
    assert res_del.status_code == 200

    # 5. Verify gone
    res_list_after = client.get(f"/api/v1/chat/conversations?workspace_id=test_workspace_crud")
    assert not any(c["id"] == conv_id for c in res_list_after.json()["conversations"])

def test_conversation_batch_delete():
    """Verify batch deletion of multiple conversations in a single API call."""
    ws_id = "test_ws_batch_delete"
    # 1. Create 3 conversations
    ids = []
    for i in range(1, 4):
        res = client.post("/api/v1/chat/conversation", json={
            "workspace_id": ws_id,
            "title": f"Batch Test Conv {i}"
        })
        assert res.status_code == 200
        ids.append(res.json()["conversation"]["id"])

    assert len(ids) == 3

    # 2. Batch delete 2 of them
    batch_res = client.post("/api/v1/chat/conversations/batch-delete", json={
        "conversation_ids": [ids[0], ids[1]]
    })
    assert batch_res.status_code == 200
    assert batch_res.json()["deleted_count"] == 2

    # 3. List and verify ids[0] and ids[1] are gone, ids[2] remains
    list_res = client.get(f"/api/v1/chat/conversations?workspace_id={ws_id}")
    assert list_res.status_code == 200
    remaining_ids = [c["id"] for c in list_res.json()["conversations"]]
    assert ids[0] not in remaining_ids
    assert ids[1] not in remaining_ids
    assert ids[2] in remaining_ids

    # 4. Clean up the last one
    client.delete(f"/api/v1/chat/conversation/{ids[2]}")

def test_vietnamese_detection():
    """Verify ChatManager.is_vietnamese accurately detects Vietnamese questions."""
    from backend.modules.chat.manager import ChatManager
    
    assert ChatManager.is_vietnamese("Kiểm toán an toàn mã nguồn, ranh giới sandbox và các tệp cấu hình") is True
    assert ChatManager.is_vietnamese("Tôi cần viết một hàm Python để tính tổng") is True
    assert ChatManager.is_vietnamese("kiem tra giup toi code nay") is True
    assert ChatManager.is_vietnamese("Sửa lỗi giao diện bị tràn chữ") is True
    assert ChatManager.is_vietnamese("Can you review this code for security vulnerabilities?") is False
    assert ChatManager.is_vietnamese("How to run unit tests in Python?") is False
    assert ChatManager.is_vietnamese("") is False


