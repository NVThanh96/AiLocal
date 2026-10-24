import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.database import init_db
from backend.modules.domains.manifests import DomainId, CORE_DOMAIN_MANIFESTS
from backend.modules.domains.registry import domain_registry

client = TestClient(app)

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()

def test_all_core_domains_manifests_registered():
    domains = domain_registry.list_domains()
    assert len(domains) == 8
    domain_ids = {d["domain_id"] for d in domains}
    expected_ids = {
        "research", "design", "finance", "ceo_strategy",
        "marketing", "media", "translation", "browser_automation"
    }
    assert domain_ids == expected_ids

    for d in domains:
        assert len(d["tools"]) > 0
        assert len(d["required_permissions"]) > 0
        assert len(d["acceptance_criteria"]) > 0
        assert d["risk_assessment"] in ["LOW", "MEDIUM", "HIGH"]
        assert d["license_type"] in ["MIT", "Apache-2.0", "BSD"]

def test_domain_license_safety_audit():
    for d_id in DomainId:
        audit = domain_registry.license_safety_audit(d_id.value)
        assert audit["is_permissive"] is True
        assert audit["commercial_use_allowed"] is True
        assert audit["no_copyleft_restrictions"] is True
        assert audit["status"] == "APPROVED"

@pytest.mark.asyncio
async def test_domain_permission_gating_and_isolation():
    workspace_id = "ws_dom_test"

    # 1. Media domain requires ["workspace.read", "workspace.write", "media.generate"]
    # Calling without permissions must raise PermissionError
    with pytest.raises(PermissionError, match="Missing required permissions"):
        await domain_registry.execute_domain_action(
            workspace_id=workspace_id,
            domain_id="media",
            action="format_short_video",
            params={"format": "1080x1920_60fps"},
            caller_permissions=["workspace.read"]  # Missing write and media.generate
        )

    # 2. Calling with all permissions must succeed
    res = await domain_registry.execute_domain_action(
        workspace_id=workspace_id,
        domain_id="media",
        action="format_short_video",
        params={"format": "1080x1920_60fps"},
        caller_permissions=["workspace.read", "workspace.write", "media.generate"]
    )
    assert res["status"] == "completed"
    assert res["result"]["media_manifest"]["resolution"] == "1080x1920"
    assert res["result"]["media_manifest"]["aspect_ratio"] == "9:16"
    assert res["result"]["media_manifest"]["fps"] == 60
    assert res["result"]["qc_passed"] is True

@pytest.mark.asyncio
async def test_domain_execution_deterministic_handlers():
    ws_id = "ws_handlers_test"

    # Research
    res_res = await domain_registry.execute_domain_action(
        ws_id, "research", "deep_search", {"topic": "Local FTS5"},
        caller_permissions=["workspace.read", "network.fetch"]
    )
    assert len(res_res["result"]["citations"]) >= 2
    assert res_res["result"]["acceptance_met"] is True

    # Design
    res_des = await domain_registry.execute_domain_action(
        ws_id, "design", "generate_tokens", {"theme": "dark"},
        caller_permissions=["workspace.read", "workspace.write"]
    )
    assert res_des["result"]["wcag_aa_compliant"] is True
    assert "sm: 640px" in res_des["result"]["responsive_breakpoints"]

    # Finance
    res_fin = await domain_registry.execute_domain_action(
        ws_id, "finance", "audit_ledger", {"budget": 1000},
        caller_permissions=["workspace.read"]
    )
    assert res_fin["result"]["cloud_cost_usd"] == 0.0
    assert res_fin["result"]["double_entry_verified"] is True

    # Marketing
    res_mkt = await domain_registry.execute_domain_action(
        ws_id, "marketing", "generate_hooks", {"product": "AiLocal"},
        caller_permissions=["workspace.read", "workspace.write"]
    )
    assert len(res_mkt["result"]["viral_hooks"]) >= 2
    assert len(res_mkt["result"]["banned_ai_words_detected"]) == 0

    # Translation
    res_trn = await domain_registry.execute_domain_action(
        ws_id, "translation", "localize", {"text": "Workspace boundary sandbox", "target_lang": "vi"},
        caller_permissions=["workspace.read"]
    )
    assert res_trn["result"]["glossary_match_pct"] == 100.0

def test_domain_api_endpoints():
    # 1. List Domains
    resp_list = client.get("/api/v1/domains")
    assert resp_list.status_code == 200
    assert len(resp_list.json()["domains"]) == 8

    # 2. Get Domain Manifest
    resp_manifest = client.get("/api/v1/domains/research")
    assert resp_manifest.status_code == 200
    assert resp_manifest.json()["manifest"]["domain_id"] == "research"

    # 3. License Audit
    resp_audit = client.get("/api/v1/domains/research/license-audit")
    assert resp_audit.status_code == 200
    assert resp_audit.json()["audit"]["status"] == "APPROVED"

    # 4. Execute without permissions -> 403
    resp_denied = client.post("/api/v1/domains/research/execute", json={
        "workspace_id": "ws_api_test",
        "action": "deep_search",
        "params": {"topic": "Local SQLite"},
        "caller_permissions": []  # Missing required
    })
    assert resp_denied.status_code == 403

    # 5. Execute with permissions -> 200
    resp_ok = client.post("/api/v1/domains/research/execute", json={
        "workspace_id": "ws_api_test",
        "action": "deep_search",
        "params": {"topic": "Local SQLite"},
        "caller_permissions": ["workspace.read", "network.fetch"]
    })
    assert resp_ok.status_code == 200
    assert resp_ok.json()["execution"]["status"] == "completed"
