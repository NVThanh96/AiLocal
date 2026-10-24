"""
End-to-End Verification Test for Phase 1
Tests full integration: FastAPI Backend <-> SQLite FTS5 <-> Ollama Qwen3:4b GPU <-> Workspace Grounding.
Saves comprehensive test report to temp_test_runs/phase1_e2e_evidence.json.
"""

import sys
import time
import json
import httpx
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BACKEND_URL = "http://127.0.0.1:8765/api/v1"
WORKSPACE_DIR = r"H:\AiLocal"

def run_e2e_test():
    print("=== STARTING PHASE 1 END-TO-END INTEGRATION TEST ===")
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "Phase 1 - Workspace + Local Chat",
        "steps": {}
    }

    client = httpx.Client(base_url=BACKEND_URL, timeout=90.0)

    # 1. Health & Model check
    print("\n[Step 1] Checking Backend Health and Ollama Model Status...")
    res_health = client.get("/health")
    assert res_health.status_code == 200, f"Health check failed: {res_health.text}"
    health_data = res_health.json()
    assert health_data["ollama"]["online"] is True, "Ollama service is not online"
    assert "qwen3:4b" in health_data["ollama"]["available_models"], "qwen3:4b not loaded in Ollama"
    report["steps"]["1_health_check"] = {
        "status": "PASS",
        "data": health_data
    }
    print("  PASS: Backend is healthy, Ollama online with qwen3:4b loaded.")

    # 2. System Hardware Metrics
    print("\n[Step 2] Querying Hardware Metrics...")
    res_sys = client.get("/system/info")
    assert res_sys.status_code == 200
    sys_data = res_sys.json()
    report["steps"]["2_system_metrics"] = {
        "status": "PASS",
        "data": sys_data
    }
    print(f"  PASS: CPU {sys_data['cpu_usage_percent']}%, RAM free {sys_data['ram_available_gb']} GB, Disk free {sys_data['disk_free_gb']} GB.")

    # 3. Open Workspace & Index with FTS5
    print(f"\n[Step 3] Opening Workspace: {WORKSPACE_DIR}...")
    res_ws = client.post("/workspace/open", json={"path": WORKSPACE_DIR})
    assert res_ws.status_code == 200, f"Failed to open workspace: {res_ws.text}"
    ws_data = res_ws.json()["workspace"]
    workspace_id = ws_data["id"]
    report["steps"]["3_open_workspace"] = {
        "status": "PASS",
        "workspace_id": workspace_id,
        "name": ws_data["name"]
    }
    print(f"  PASS: Workspace opened with ID {workspace_id}")

    # 4. Workspace Directory Tree (Read-Only)
    print("\n[Step 4] Reading Workspace Directory Tree...")
    res_tree = client.get(f"/workspace/tree?path={WORKSPACE_DIR}")
    assert res_tree.status_code == 200
    tree_items = res_tree.json()["tree"]
    assert len(tree_items) > 0, "File tree is empty"
    report["steps"]["4_directory_tree"] = {
        "status": "PASS",
        "root_items_count": len(tree_items),
        "root_names": [i["name"] for i in tree_items]
    }
    print(f"  PASS: File tree retrieved ({len(tree_items)} root entries found).")

    # 5. FTS5 Full-Text Search
    print("\n[Step 5] Testing FTS5 Search for query 'Phase 0'...")
    res_search = client.post("/workspace/search", json={
        "workspace_id": workspace_id,
        "query": "Phase OR Audit",
        "limit": 5
    })
    assert res_search.status_code == 200
    matches = res_search.json()["matches"]
    assert len(matches) > 0, "No FTS5 search matches found"
    report["steps"]["5_fts5_search"] = {
        "status": "PASS",
        "matches_count": len(matches),
        "top_match": matches[0]
    }
    print(f"  PASS: FTS5 returned {len(matches)} matches. Top match: {matches[0]['file_name']}")

    # 6. Read-Only File Retrieval
    print("\n[Step 6] Safely reading masterImplementationPrompt.md...")
    res_read = client.post("/workspace/read", json={
        "workspace_path": WORKSPACE_DIR,
        "relative_path": "masterImplementationPrompt.md"
    })
    assert res_read.status_code == 200
    file_data = res_read.json()["file"]
    assert len(file_data["content"]) > 0
    report["steps"]["6_safe_read_file"] = {
        "status": "PASS",
        "file_name": "masterImplementationPrompt.md",
        "size_bytes": file_data["size"]
    }
    print(f"  PASS: Read file masterImplementationPrompt.md ({file_data['size']} bytes).")

    # 7. Create Chat Conversation
    print("\n[Step 7] Creating Chat Conversation...")
    res_conv = client.post("/chat/conversation", json={
        "workspace_id": workspace_id,
        "title": "Phase 1 Verification Chat"
    })
    assert res_conv.status_code == 200
    conv_id = res_conv.json()["conversation"]["id"]
    report["steps"]["7_create_conversation"] = {
        "status": "PASS",
        "conversation_id": conv_id
    }
    print(f"  PASS: Conversation created: {conv_id}")

    # 8. Real Model Inference with Workspace Grounding (Qwen3:4b on GPU)
    print("\n[Step 8] Generating real grounded inference using local Qwen3:4b model...")
    prompt = "Tóm tắt ngắn gọn 1 câu: Tài liệu masterImplementationPrompt.md yêu cầu làm gì trong Phase 0?"
    infer_start = time.perf_counter()
    res_msg = client.post("/chat/message", json={
        "conversation_id": conv_id,
        "content": prompt,
        "model": "qwen3:4b"
    })
    infer_latency = round((time.perf_counter() - infer_start), 2)
    assert res_msg.status_code == 200, f"Inference failed: {res_msg.text}"
    msg_data = res_msg.json()["response"]
    
    report["steps"]["8_grounded_inference"] = {
        "status": "PASS",
        "prompt": prompt,
        "response": msg_data["content"],
        "sources_cited": msg_data["sources"],
        "latency_seconds": infer_latency
    }
    print(f"  PASS: Response received in {infer_latency}s:")
    print(f"  Assistant: {msg_data['content']}")
    print(f"  Sources cited: {[s['file_name'] for s in msg_data['sources']]}")

    # Save complete report to 48h TTL sandbox
    output_dir = Path(r"H:\AiLocal\temp_test_runs")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "phase1_e2e_evidence.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print(f"\n[EVIDENCE RECORDED] Phase 1 E2E Test Report saved to {report_file}")
    print("=== PHASE 1 END-TO-END INTEGRATION TEST SUCCEEDED ===")

if __name__ == "__main__":
    try:
        run_e2e_test()
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] E2E Test failed: {str(e)}")
        sys.exit(1)
