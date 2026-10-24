"""
Phase 0 Baseline Verification Suite
Tests SQLite FTS5, Hardware & OS Metrics, Security Guards (Path Traversal, SSRF), and Toolchain.
All results are strictly evidenced with exit codes and execution benchmarks.
"""

import sys
import os
import time
import json
import socket
import ipaddress
import sqlite3
import subprocess
from pathlib import Path
from urllib.parse import urlparse

def test_sqlite_fts5():
    """Verify SQLite version and FTS5 full-text indexing engine functionality and latency."""
    start_time = time.perf_counter()
    db_path = ":memory:"
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # 1. Create table with FTS5
    cur.execute("""
        CREATE VIRTUAL TABLE workspace_documents USING fts5(
            file_path UNINDEXED,
            file_name,
            content,
            tokenize='unicode61 remove_diacritics 1'
        );
    """)
    
    # 2. Benchmark insertion of 500 documents
    sample_docs = [
        ("src/main.py", "main.py", "FastAPI local agent server running on localhost port 8000 with Ollama adapter"),
        ("src/security.py", "security.py", "Execution Broker guarding path traversal, SSRF and command allowlist"),
        ("src/crawler.py", "crawler.py", "HTTP web crawler with robots.txt parser and rate limiter"),
        ("src/memory.py", "memory.py", "Project Memory and Error Memory with SQLite backing and FTS5 search"),
        ("tests/test_agent.py", "test_agent.py", "Pytest suite verifying regression and acceptance criteria"),
    ]
    
    for i in range(100):
        for path, name, content in sample_docs:
            cur.execute(
                "INSERT INTO workspace_documents(file_path, file_name, content) VALUES (?, ?, ?)",
                (f"{path}_{i}", f"{name}_{i}", f"{content} iteration {i}")
            )
    con.commit()
    
    insert_duration = (time.perf_counter() - start_time) * 1000
    
    # 3. Test Full-Text Search query
    query_start = time.perf_counter()
    cur.execute("""
        SELECT file_path, file_name, snippet(workspace_documents, 2, '<b>', '</b>', '...', 10), bm25(workspace_documents)
        FROM workspace_documents
        WHERE workspace_documents MATCH 'SSRF OR Ollama'
        ORDER BY bm25(workspace_documents)
        LIMIT 10;
    """)
    rows = cur.fetchall()
    query_duration = (time.perf_counter() - query_start) * 1000
    
    con.close()
    
    assert len(rows) > 0, "FTS5 search returned 0 results"
    
    return {
        "status": "PASS",
        "sqlite_version": sqlite3.sqlite_version,
        "fts5_supported": True,
        "inserted_docs": 500,
        "insert_latency_ms": round(insert_duration, 2),
        "query_latency_ms": round(query_duration, 2),
        "sample_match_count": len(rows),
        "sample_snippet": rows[0][2]
    }

def test_workspace_path_sandbox():
    """Verify Path Traversal prevention logic within workspace boundary."""
    workspace_root = Path(r"H:\AiLocal").resolve()
    
    test_cases = [
        # (Input path, Expected to be safe)
        (r"H:\AiLocal\src\main.py", True),
        (r"H:\AiLocal\docs\mindmap.md", True),
        (r"H:\AiLocal\..\..\Windows\System32\calc.exe", False),
        (r"..\..\Windows\System32", False),
        (r"H:\AiLocal\temp_test_runs\test.txt", True),
        (r"C:\Users\AMIN\AppData", False),
        (r"H:\upgradePixel\MINDMAP.md", False),
    ]
    
    results = []
    all_passed = True
    
    for target, expected_safe in test_cases:
        try:
            resolved_target = (workspace_root / target).resolve() if not Path(target).is_absolute() else Path(target).resolve()
            is_safe = resolved_target == workspace_root or workspace_root in resolved_target.parents
        except Exception:
            is_safe = False
            
        check_passed = (is_safe == expected_safe)
        if not check_passed:
            all_passed = False
        results.append({
            "target": target,
            "expected_safe": expected_safe,
            "is_safe": is_safe,
            "passed": check_passed
        })
        
    return {
        "status": "PASS" if all_passed else "FAIL",
        "workspace_root": str(workspace_root),
        "total_test_cases": len(test_cases),
        "all_guards_effective": all_passed,
        "details": results
    }

def test_network_ssrf_guard():
    """Verify SSRF validation logic against private IPs, metadata IPs, and localhost."""
    test_urls = [
        ("http://127.0.0.1:8000/api", False),
        ("http://localhost:11434/api", False),
        ("http://169.254.169.254/latest/meta-data", False),
        ("http://192.168.1.1/admin", False),
        ("http://10.0.0.1/secret", False),
        ("https://huggingface.co/models", True),
        ("https://github.com/ollama/ollama", True),
        ("file:///C:/Windows/win.ini", False),
        ("ftp://internal.vault/data", False)
    ]
    
    def is_url_safe(url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            # Domain name, in production will resolve IP before connecting
            pass
        return True

    results = []
    all_passed = True
    for url, expected_safe in test_urls:
        actual_safe = is_url_safe(url)
        passed = (actual_safe == expected_safe)
        if not passed:
            all_passed = False
        results.append({
            "url": url,
            "expected_safe": expected_safe,
            "actual_safe": actual_safe,
            "passed": passed
        })

    return {
        "status": "PASS" if all_passed else "FAIL",
        "total_urls_tested": len(test_urls),
        "all_guards_effective": all_passed,
        "details": results
    }

def test_ollama_service_connectivity():
    """Check whether local Ollama server is active and reachable on 127.0.0.1:11434."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.5)
    result = sock.connect_ex(("127.0.0.1", 11434))
    sock.close()
    
    is_online = (result == 0)
    return {
        "status": "ONLINE" if is_online else "OFFLINE",
        "endpoint": "http://127.0.0.1:11434",
        "port_open": is_online,
        "recommendation": "Install or start Ollama service before starting Phase 1" if not is_online else "Ollama ready"
    }

def test_toolchain_audit():
    """Audit installed dev tools and versions."""
    tools = {}
    
    # Python
    tools["python"] = {
        "installed": True,
        "version": sys.version.split()[0],
        "executable": sys.executable
    }
    
    # Node
    try:
        out = subprocess.check_output(["node", "--version"], text=True).strip()
        tools["node"] = {"installed": True, "version": out}
    except Exception as e:
        tools["node"] = {"installed": False, "error": str(e)}

    # Git
    try:
        out = subprocess.check_output(["git", "--version"], text=True).strip()
        tools["git"] = {"installed": True, "version": out}
    except Exception as e:
        tools["git"] = {"installed": False, "error": str(e)}

    # Rust
    try:
        out = subprocess.check_output(["rustc", "--version"], text=True).strip()
        tools["rustc"] = {"installed": True, "version": out}
    except Exception as e:
        tools["rustc"] = {"installed": False, "note": "Required if compiling native Tauri desktop shell"}

    # Ollama CLI
    try:
        out = subprocess.check_output(["ollama", "--version"], text=True).strip()
        tools["ollama"] = {"installed": True, "version": out}
    except Exception as e:
        tools["ollama"] = {"installed": False, "note": "Required for local LLM inference"}

    return {
        "status": "PASS",
        "tools": tools
    }

def run_all_baseline_tests():
    print("=== RUNNING PHASE 0 BASELINE VERIFICATION TESTS ===")
    
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "Phase 0 - Audit & Baseline",
        "tests": {}
    }
    
    # 1. SQLite FTS5
    print("\n[1/5] Testing SQLite 3 + FTS5 engine...")
    fts5_res = test_sqlite_fts5()
    report["tests"]["sqlite_fts5"] = fts5_res
    print(f"  Result: {fts5_res['status']} (Insert 500 docs in {fts5_res['insert_latency_ms']}ms, Search in {fts5_res['query_latency_ms']}ms)")
    
    # 2. Workspace Path Sandbox
    print("\n[2/5] Testing Workspace Path Sandbox Boundary Guard...")
    path_res = test_workspace_path_sandbox()
    report["tests"]["workspace_sandbox"] = path_res
    print(f"  Result: {path_res['status']} ({path_res['total_test_cases']} path scenarios verified)")
    
    # 3. SSRF Guard
    print("\n[3/5] Testing Network SSRF & Private IP Guard...")
    ssrf_res = test_network_ssrf_guard()
    report["tests"]["network_ssrf_guard"] = ssrf_res
    print(f"  Result: {ssrf_res['status']} ({ssrf_res['total_urls_tested']} URL scenarios verified)")
    
    # 4. Ollama Connectivity
    print("\n[4/5] Testing Local Ollama Service Connectivity...")
    ollama_res = test_ollama_service_connectivity()
    report["tests"]["ollama_service"] = ollama_res
    print(f"  Result: {ollama_res['status']} ({ollama_res['endpoint']})")
    
    # 5. Toolchain Audit
    print("\n[5/5] Auditing System Toolchains...")
    toolchain_res = test_toolchain_audit()
    report["tests"]["toolchain_audit"] = toolchain_res
    print(f"  Result: {toolchain_res['status']}")
    
    # Save report to 48h TTL sandbox
    output_dir = Path(r"H:\AiLocal\temp_test_runs")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "phase0_baseline_report.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print(f"\n[EVIDENCE SAVED] Baseline report written to {report_file}")
    print("=== PHASE 0 BASELINE VERIFICATION COMPLETED ===")
    
    return report

if __name__ == "__main__":
    report = run_all_baseline_tests()
    # Exit with code 0 if critical tests pass
    critical_pass = (
        report["tests"]["sqlite_fts5"]["status"] == "PASS" and
        report["tests"]["workspace_sandbox"]["status"] == "PASS" and
        report["tests"]["network_ssrf_guard"]["status"] == "PASS"
    )
    sys.exit(0 if critical_pass else 1)
