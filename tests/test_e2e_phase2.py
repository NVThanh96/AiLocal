"""
End-to-End Verification Test for Phase 2: Requirement Intelligence Gate
Verifies:
1. Parse & Ambiguity Detection (NEEDS_CLARIFICATION).
2. Clarification Question Resolution & Version Bump.
3. High-Risk Action Detection & Safety Approval Gate (NEEDS_APPROVAL -> BLOCKED / READY).
4. Immutable Version Audit Trail in SQLite.
Saves verified report to temp_test_runs/phase2_e2e_evidence.json.
"""

import sys
import time
import json
import httpx
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BACKEND_URL = "http://127.0.0.1:8765/api/v1"
WORKSPACE_DIR = r"H:\AiLocal"

def run_phase2_e2e_test():
    print("=== STARTING PHASE 2 REQUIREMENT INTELLIGENCE E2E TEST ===")
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "Phase 2 - Requirement Intelligence",
        "scenarios": {}
    }

    client = httpx.Client(base_url=BACKEND_URL, timeout=30.0)

    # 1. Open Workspace
    res_ws = client.post("/workspace/open", json={"path": WORKSPACE_DIR})
    assert res_ws.status_code == 200
    workspace_id = res_ws.json()["workspace"]["id"]
    print(f"[Setup] Workspace opened: {workspace_id}")

    # ----------------- Scenario A: Ambiguity & Clarification Flow -----------------
    print("\n[Scenario A] Testing Ambiguous Request -> NEEDS_CLARIFICATION...")
    ambiguous_prompt = "Hãy sửa lỗi và tối ưu hệ thống"
    res_amb = client.post("/requirements/analyze", json={
        "workspace_id": workspace_id,
        "workspace_path": WORKSPACE_DIR,
        "prompt": ambiguous_prompt
    })
    assert res_amb.status_code == 200, f"Analyze failed: {res_amb.text}"
    spec_amb = res_amb.json()["task_spec"]
    
    assert spec_amb["status"] == "NEEDS_CLARIFICATION", "Ambiguous prompt was not classified as NEEDS_CLARIFICATION"
    assert len(spec_amb["unresolved_questions"]) > 0, "No clarification questions generated"
    question = spec_amb["unresolved_questions"][0]
    task_id_amb = spec_amb["task_id"]
    
    print(f"  PASS: Classified as {spec_amb['status']}. Generated question: '{question['question']}'")
    print(f"  Options: {question['suggested_options']}")

    # Submit Clarification Choice
    print("  Submitting user clarification answer...")
    chosen_opt = "Chỉ áp dụng trong thư mục backend/"
    res_clarify = client.post("/requirements/clarify", json={
        "task_id": task_id_amb,
        "question_id": question["id"],
        "chosen_option": chosen_opt
    })
    assert res_clarify.status_code == 200
    clarified_spec = res_clarify.json()["task_spec"]
    assert clarified_spec["status"] == "READY", "Task did not transition to READY after clarification"
    assert clarified_spec["request_version"] == 2, "Task version was not incremented"
    print(f"  PASS: Task transitioned to {clarified_spec['status']} (v{clarified_spec['request_version']})")

    report["scenarios"]["scenario_a_clarification"] = {
        "status": "PASS",
        "prompt": ambiguous_prompt,
        "initial_status": spec_amb["status"],
        "question": question["question"],
        "chosen_option": chosen_opt,
        "final_status": clarified_spec["status"],
        "final_version": clarified_spec["request_version"]
    }

    # ----------------- Scenario B: High-Risk Action & Approval Gate -----------------
    print("\n[Scenario B] Testing Destructive Request -> NEEDS_APPROVAL Gate...")
    high_risk_prompt = "Xóa file storage/old_cache.dump"
    res_risk = client.post("/requirements/analyze", json={
        "workspace_id": workspace_id,
        "workspace_path": WORKSPACE_DIR,
        "prompt": high_risk_prompt
    })
    assert res_risk.status_code == 200
    spec_risk = res_risk.json()["task_spec"]
    assert spec_risk["status"] == "NEEDS_APPROVAL", "Destructive task did not require approval"
    assert spec_risk["risk_level"] == "HIGH", "Risk level was not HIGH"
    assert "workspace.delete" in spec_risk["required_permissions"]
    task_id_risk = spec_risk["task_id"]
    print(f"  PASS: Classified as {spec_risk['status']} with risk level {spec_risk['risk_level']}.")

    # Test Rejection
    print("  Testing user Rejection...")
    res_reject = client.post("/requirements/approve", json={
        "task_id": task_id_risk,
        "approved": False
    })
    assert res_reject.status_code == 200
    rejected_spec = res_reject.json()["task_spec"]
    assert rejected_spec["status"] == "BLOCKED"
    print("  PASS: Rejection transitioned task to BLOCKED.")

    # Test Approval
    print("  Testing user Approval...")
    res_approve = client.post("/requirements/approve", json={
        "task_id": task_id_risk,
        "approved": True
    })
    assert res_approve.status_code == 200
    approved_spec = res_approve.json()["task_spec"]
    assert approved_spec["status"] == "READY"
    print(f"  PASS: Approval transitioned task to READY (v{approved_spec['request_version']}).")

    report["scenarios"]["scenario_b_approval_gate"] = {
        "status": "PASS",
        "prompt": high_risk_prompt,
        "initial_status": spec_risk["status"],
        "risk_level": spec_risk["risk_level"],
        "required_permissions": spec_risk["required_permissions"],
        "rejected_status": rejected_spec["status"],
        "approved_status": approved_spec["status"],
        "final_version": approved_spec["request_version"]
    }

    # ----------------- Scenario C: Version Audit Trail -----------------
    print("\n[Scenario C] Verifying Task Version Audit Trail in SQLite...")
    res_ver = client.get(f"/requirements/tasks/{task_id_risk}/versions")
    assert res_ver.status_code == 200
    versions = res_ver.json()["versions"]
    assert len(versions) == 3, f"Expected 3 versions, got {len(versions)}"
    assert versions[0]["status"] == "NEEDS_APPROVAL"
    assert versions[1]["status"] == "BLOCKED"
    assert versions[2]["status"] == "READY"
    print(f"  PASS: Immutable version audit trail verified with {len(versions)} sequential snapshots.")

    report["scenarios"]["scenario_c_version_audit"] = {
        "status": "PASS",
        "version_count": len(versions),
        "history": [{"version": v["version"], "status": v["status"], "created_at": v["created_at"]} for v in versions]
    }

    # Save complete evidence report to 48h TTL sandbox
    output_dir = Path(r"H:\AiLocal\temp_test_runs")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "phase2_e2e_evidence.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print(f"\n[EVIDENCE RECORDED] Phase 2 E2E Evidence saved to {report_file}")
    print("=== PHASE 2 REQUIREMENT INTELLIGENCE VERIFICATION SUCCEEDED ===")

if __name__ == "__main__":
    try:
        run_phase2_e2e_test()
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Phase 2 E2E Test failed: {str(e)}")
        sys.exit(1)
