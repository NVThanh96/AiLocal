import os
import shutil
import psutil
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Query, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.database import init_db
from backend.modules.security.broker import SecurityBroker
from backend.modules.workspace.manager import WorkspaceManager
from backend.modules.model.adapter import OllamaAdapter, MockAdapter
from backend.modules.chat.manager import ChatManager
from backend.modules.media.parser import MediaParser
from backend.modules.requirement.engine import RequirementIntelligenceEngine
from backend.modules.requirement.schema import TaskSpecification, TaskStatus, RiskLevel
from backend.modules.execution.broker import ExecutionBroker, CheckpointManager, AuditLogger
from backend.modules.crawler.engine import CrawlEngine
from backend.modules.memory.engine import MemoryEngine
from backend.modules.retention.manager import RetentionManager
from backend.modules.agents.qa_dev import QADevAgent
from backend.modules.orchestrator.engine import orchestrator_engine
from backend.modules.orchestrator.registry import list_agent_profiles
from backend.modules.domains.registry import domain_registry

# Choose default model adapter
ollama_adapter = OllamaAdapter(base_url=settings.OLLAMA_BASE_URL, default_model=settings.PRIMARY_MODEL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB schema is created
    await init_db()
    from backend.modules.skills.manager import SkillManager
    from backend.modules.mcp.manager import MCPManager
    await SkillManager.init_builtin_skills()
    await MCPManager.init_default_servers()
    yield
    # Shutdown: Cleanups if needed

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS restricted strictly to localhost origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "tauri://localhost"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Request / Response Models -----------------

class WorkspaceOpenRequest(BaseModel):
    path: str = Field(..., description="Absolute path of workspace directory")

class WorkspaceSearchRequest(BaseModel):
    workspace_id: str
    query: str
    limit: Optional[int] = 15

class FileReadRequest(BaseModel):
    workspace_path: str
    relative_path: str

class ConversationCreateRequest(BaseModel):
    workspace_id: str
    title: Optional[str] = "New Chat"

class ConversationUpdateRequest(BaseModel):
    title: str

class BatchDeleteConversationsRequest(BaseModel):
    conversation_ids: List[str]

class WorkspaceReindexRequest(BaseModel):
    workspace_id: str
    workspace_path: str

class ChatMessageRequest(BaseModel):
    conversation_id: str
    content: str
    model: Optional[str] = None
    use_mock: Optional[bool] = False
    attachments: Optional[List[Dict[str, Any]]] = None

class RequirementAnalyzeRequest(BaseModel):
    workspace_id: str
    workspace_path: str
    prompt: str

class RequirementClarifyRequest(BaseModel):
    task_id: str
    question_id: str
    chosen_option: str

class RequirementApproveRequest(BaseModel):
    task_id: str
    approved: bool = True

# ----------------- API Endpoints -----------------

@app.get("/api/v1/health")
async def health_check():
    """Health status check of Backend, SQLite and Ollama Adapter."""
    ollama_health = await ollama_adapter.check_health()
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "ollama": ollama_health
    }

@app.get("/api/v1/system/info")
async def system_info():
    """Get system and hardware utilization metrics."""
    cpu_usage = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    disk = shutil.disk_usage(str(settings.BASE_DIR))
    
    return {
        "cpu_usage_percent": cpu_usage,
        "ram_total_gb": round(ram.total / (1024**3), 2),
        "ram_available_gb": round(ram.available / (1024**3), 2),
        "ram_used_percent": ram.percent,
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2)
    }

class BrowseDirectoryRequest(BaseModel):
    path: Optional[str] = Field(None, description="Path to browse, defaults to current directory")

class CreateDirectoryRequest(BaseModel):
    parent_path: str = Field(..., description="Parent directory path")
    folder_name: str = Field(..., description="New folder name")

@app.get("/api/v1/system/drives")
async def get_system_drives():
    """List all available Windows drives or mounted roots."""
    import string
    drives = []
    for letter in string.ascii_uppercase:
        drive_path = f"{letter}:\\"
        if os.path.exists(drive_path):
            try:
                usage = shutil.disk_usage(drive_path)
                drives.append({
                    "drive": drive_path,
                    "name": f"Disk ({letter}:)",
                    "total_gb": round(usage.total / (1024**3), 1),
                    "free_gb": round(usage.free / (1024**3), 1)
                })
            except Exception:
                drives.append({
                    "drive": drive_path,
                    "name": f"Disk ({letter}:)",
                    "total_gb": 0,
                    "free_gb": 0
                })
    return {"status": "ok", "drives": drives}

@app.post("/api/v1/system/browse-directory")
async def browse_directory(req: BrowseDirectoryRequest):
    """Browse subdirectories of a given path safely with breadcrumbs and project indicators."""
    target_path = Path(req.path).resolve() if req.path and req.path.strip() else Path.cwd()
    if not target_path.exists() or not target_path.is_dir():
        if target_path.drive and Path(target_path.drive + "\\").exists():
            target_path = Path(target_path.drive + "\\")
        else:
            target_path = Path.cwd()

    parents = list(reversed([target_path] + list(target_path.parents)))
    breadcrumbs = [{"name": x.name or x.drive or str(x), "path": str(x)} for x in parents]

    directories = []
    try:
        for entry in target_path.iterdir():
            if not entry.is_dir():
                continue
            name = entry.name
            if name.startswith("$") or name in ("System Volume Information", "Recovery", "$Recycle.Bin", ".git"):
                continue
            
            is_proj = (entry / "package.json").exists() or (entry / "requirements.txt").exists() or (entry / "pyproject.toml").exists() or (entry / "Cargo.toml").exists()
            try:
                mtime = entry.stat().st_mtime
            except Exception:
                mtime = 0

            directories.append({
                "name": name,
                "path": str(entry),
                "is_project": is_proj,
                "modified": mtime
            })
    except PermissionError:
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read directory: {str(e)}")

    directories.sort(key=lambda d: d["name"].lower())
    parent_path = str(target_path.parent) if target_path.parent != target_path else None

    return {
        "status": "ok",
        "current_path": str(target_path),
        "parent_path": parent_path,
        "breadcrumbs": breadcrumbs,
        "directories": directories
    }

@app.post("/api/v1/system/create-directory")
async def create_directory_on_disk(req: CreateDirectoryRequest):
    """Create a new folder at the specified parent directory."""
    parent = Path(req.parent_path).resolve()
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(status_code=400, detail="Parent directory does not exist")
    folder_name = req.folder_name.strip()
    if not folder_name or "/" in folder_name or "\\" in folder_name:
        raise HTTPException(status_code=400, detail="Invalid folder name")
    new_dir = parent / folder_name
    new_dir.mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "path": str(new_dir), "name": new_dir.name}

@app.post("/api/v1/workspace/open")
async def open_workspace(req: WorkspaceOpenRequest):
    """Open and index a local workspace directory."""
    try:
        result = await WorkspaceManager.open_workspace(req.path)
        return {"status": "success", "workspace": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/workspace/tree")
async def get_workspace_tree(path: str = Query(..., description="Workspace root path")):
    """Get file and directory tree within the workspace."""
    if not Path(path).exists():
        raise HTTPException(status_code=404, detail="Workspace directory not found")
    tree = WorkspaceManager.get_file_tree(path)
    return {"workspace_path": path, "tree": tree}

@app.post("/api/v1/workspace/search")
async def search_workspace_documents(req: WorkspaceSearchRequest):
    """Search workspace documents using FTS5 BM25 ranking."""
    try:
        matches = await WorkspaceManager.search_workspace(req.workspace_id, req.query, limit=req.limit or 15)
        return {"query": req.query, "matches": matches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

async def _trigger_reindex(workspace_path: str, workspace_id: Optional[str] = None):
    """Background helper to keep SQLite FTS5 index in sync on file mutations."""
    try:
        if not workspace_id:
            conn = await get_db_connection()
            cursor = await conn.execute("SELECT id FROM workspaces WHERE path = ?", (str(Path(workspace_path).resolve()),))
            row = await cursor.fetchone()
            await conn.close()
            if row:
                workspace_id = row["id"]
        if workspace_id and Path(workspace_path).exists():
            await WorkspaceManager.index_workspace(workspace_id, Path(workspace_path))
    except Exception:
        pass

@app.post("/api/v1/workspace/read")
async def read_workspace_file(req: FileReadRequest):
    """Read a file safely within workspace boundary."""
    try:
        data = WorkspaceManager.read_file(req.workspace_path, req.relative_path)
        return {"status": "success", "file": data}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except FileNotFoundError as fe:
        raise HTTPException(status_code=404, detail=str(fe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/chat/conversation")
async def create_chat_conversation(req: ConversationCreateRequest):
    """Create a new chat conversation session."""
    conv = await ChatManager.create_conversation(req.workspace_id, req.title or "New Chat")
    return {"status": "success", "conversation": conv}

@app.put("/api/v1/chat/conversation/{conversation_id}")
async def update_chat_conversation(conversation_id: str, req: ConversationUpdateRequest):
    """Update conversation title."""
    success = await ChatManager.update_conversation_title(conversation_id, req.title)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "conversation_id": conversation_id, "title": req.title}

@app.delete("/api/v1/chat/conversation/{conversation_id}")
async def delete_chat_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    success = await ChatManager.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "conversation_id": conversation_id}

@app.delete("/api/v1/chat/conversations/workspace/{workspace_id}")
async def clear_workspace_conversations(workspace_id: str):
    """Clear all conversations for a workspace."""
    count = await ChatManager.clear_workspace_conversations(workspace_id)
    return {"status": "success", "cleared_count": count}

@app.post("/api/v1/chat/conversations/batch-delete")
async def batch_delete_conversations(req: BatchDeleteConversationsRequest):
    """Batch delete multiple selected conversations and their messages."""
    deleted_count = await ChatManager.delete_conversations_batch(req.conversation_ids)
    return {"status": "success", "deleted_count": deleted_count}

@app.post("/api/v1/workspace/reindex")
async def reindex_workspace(req: WorkspaceReindexRequest):
    """Explicitly trigger SQLite FTS5 re-indexing for a workspace."""
    try:
        await WorkspaceManager.index_workspace(req.workspace_id, Path(req.workspace_path))
        return {"status": "success", "message": f"Successfully reindexed workspace {req.workspace_id}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/chat/conversations")
async def list_chat_conversations(workspace_id: str = Query(...)):
    """List all conversations for a workspace."""
    conversations = await ChatManager.get_history(workspace_id)
    return {"workspace_id": workspace_id, "conversations": conversations}

@app.get("/api/v1/chat/messages")
async def list_conversation_messages(conversation_id: str = Query(...)):
    """List messages within a conversation."""
    messages = await ChatManager.get_messages(conversation_id)
    return {"conversation_id": conversation_id, "messages": messages}

@app.post("/api/v1/chat/upload")
async def upload_chat_attachment(
    file: UploadFile = File(...),
    workspace_id: Optional[str] = Form(None)
):
    """Upload an image, video, document, or audio file, analyze it with MediaParser, and return metadata & preview."""
    try:
        import uuid
        upload_dir = Path("storage/uploads") / (workspace_id or "global")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        safe_filename = file.filename or "uploaded_file"
        unique_name = f"{uuid.uuid4().hex[:12]}_{safe_filename}"
        dest_path = upload_dir / unique_name

        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Deep analysis with MediaParser (Images, Videos with ffprobe/ffmpeg, Documents/PDF)
        analysis = await MediaParser.analyze_file(dest_path, original_filename=safe_filename)
        analysis["storage_path"] = str(dest_path).replace("\\", "/")

        return {
            "status": "success",
            "attachment": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tải lên và phân tích tệp: {str(e)}")

@app.post("/api/v1/chat/message")
async def send_chat_message(req: ChatMessageRequest):
    """Send user message, ground with workspace FTS5 evidence and multimodal attachments, and obtain response."""
    adapter = MockAdapter() if req.use_mock else ollama_adapter
    try:
        reply = await ChatManager.process_user_message(
            conversation_id=req.conversation_id,
            user_prompt=req.content,
            adapter=adapter,
            model=req.model,
            attachments=req.attachments
        )
        return {"status": "success", "response": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- Requirement Intelligence Endpoints -----------------

@app.post("/api/v1/requirements/analyze")
async def analyze_requirement(req: RequirementAnalyzeRequest):
    """Analyze user prompt through 5-step clarification gate, gather evidence, and freeze Task Spec."""
    try:
        spec = await RequirementIntelligenceEngine.analyze_prompt(
            workspace_id=req.workspace_id,
            workspace_path=req.workspace_path,
            user_prompt=req.prompt
        )
        return {"status": "success", "task_spec": spec}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/requirements/clarify")
async def answer_clarification(req: RequirementClarifyRequest):
    """Submit answer to clarification question, updating Task Specification."""
    try:
        spec = await RequirementIntelligenceEngine.answer_clarification(
            task_id=req.task_id,
            question_id=req.question_id,
            chosen_option=req.chosen_option
        )
        return {"status": "success", "task_spec": spec}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/requirements/approve")
async def approve_requirement_action(req: RequirementApproveRequest):
    """User approves or rejects high-risk task execution."""
    try:
        spec = await RequirementIntelligenceEngine.approve_task(
            task_id=req.task_id,
            approved=req.approved
        )
        return {"status": "success", "task_spec": spec}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/requirements/tasks/{task_id}")
async def get_task_specification(task_id: str):
    """Fetch task specification detail."""
    spec = await RequirementIntelligenceEngine.get_task(task_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success", "task_spec": spec}

@app.get("/api/v1/requirements/tasks/{task_id}/versions")
async def get_task_version_history(task_id: str):
    """Fetch version audit trail for task specification."""
    versions = await RequirementIntelligenceEngine.get_task_versions(task_id)
    return {"status": "success", "versions": versions}

# ----------------- Phase 3: Safe Execution & Sandbox Endpoints -----------------

class FileWriteRequest(BaseModel):
    workspace_id: str
    workspace_path: str
    relative_path: str
    content: str

class FileDeleteRequest(BaseModel):
    workspace_id: str
    workspace_path: str
    relative_path: str

class RollbackRequest(BaseModel):
    checkpoint_id: str

class TerminalRunRequest(BaseModel):
    workspace_id: str
    workspace_path: str
    executable: str
    args: List[str] = []
    timeout_seconds: Optional[int] = 30

@app.post("/api/v1/execution/file/write")
async def execute_file_write(req: FileWriteRequest):
    """Safely write/modify file with pre-modification checkpoint and diff."""
    try:
        res = await ExecutionBroker.write_file(
            workspace_id=req.workspace_id,
            workspace_path=req.workspace_path,
            relative_path=req.relative_path,
            new_content=req.content
        )
        return {"status": "success", "execution": res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/execution/file/delete")
async def execute_file_delete(req: FileDeleteRequest):
    """Safely delete file with pre-deletion checkpoint for rollback."""
    try:
        res = await ExecutionBroker.delete_file(
            workspace_id=req.workspace_id,
            workspace_path=req.workspace_path,
            relative_path=req.relative_path
        )
        asyncio.create_task(_trigger_reindex(req.workspace_path, req.workspace_id))
        return {"status": "success", "execution": res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except FileNotFoundError as fe:
        raise HTTPException(status_code=404, detail=str(fe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/execution/rollback")
async def execute_rollback(req: RollbackRequest):
    """Rollback file changes using checkpoint ID."""
    try:
        res = await CheckpointManager.rollback(req.checkpoint_id)
        return {"status": "success", "rollback": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/execution/terminal/run")
async def execute_terminal_command(req: TerminalRunRequest):
    """Execute command safely in sandboxed environment with executable allowlist."""
    try:
        res = await ExecutionBroker.run_sandboxed_command(
            workspace_id=req.workspace_id,
            workspace_path=req.workspace_path,
            executable=req.executable,
            args=req.args,
            timeout_seconds=req.timeout_seconds or 30
        )
        return {"status": "success", "result": res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/execution/audit")
async def get_audit_logs(workspace_id: Optional[str] = None, limit: int = 50):
    """Query recent security and execution audit events."""
    from backend.core.database import get_db_connection
    conn = await get_db_connection()
    try:
        if workspace_id:
            cursor = await conn.execute("""
                SELECT id, action, target, status, exit_code, duration_ms, details_json, created_at
                FROM audit_logs
                WHERE workspace_id = ?
                ORDER BY created_at DESC LIMIT ?;
            """, (workspace_id, limit))
        else:
            cursor = await conn.execute("""
                SELECT id, action, target, status, exit_code, duration_ms, details_json, created_at
                FROM audit_logs
                ORDER BY created_at DESC LIMIT ?;
            """, (limit,))
        rows = await cursor.fetchall()
        return {"status": "success", "logs": [dict(r) for r in rows]}
    finally:
        await conn.close()

# ----------------- Phase 4: Crawl & Knowledge Acquisition Endpoints -----------------

class CrawlSourceRequest(BaseModel):
    workspace_id: str
    workspace_path: str
    source_type: str = Field(..., description="'web' or 'local'")
    target_uri: str = Field(..., description="URL or relative file path")

@app.post("/api/v1/crawler/crawl")
async def execute_crawl_source(req: CrawlSourceRequest):
    """Execute crawl pipeline for web URL or local file, store provenance and index."""
    try:
        res = await CrawlEngine.crawl_source(
            workspace_id=req.workspace_id,
            workspace_path=req.workspace_path,
            source_type=req.source_type,
            target_uri=req.target_uri
        )
        return {"status": "success", "crawl": res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/crawler/jobs")
async def list_crawl_jobs(workspace_id: str = Query(...)):
    """List crawl jobs for a workspace."""
    from backend.core.database import get_db_connection
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            SELECT id, source_type, target_url, status, documents_count, created_at, updated_at
            FROM crawl_jobs
            WHERE workspace_id = ?
            ORDER BY created_at DESC;
        """, (workspace_id,))
        rows = await cursor.fetchall()
        return {"status": "success", "jobs": [dict(r) for r in rows]}
    finally:
        await conn.close()

@app.get("/api/v1/crawler/documents")
async def list_crawl_documents(workspace_id: str = Query(...)):
    """List indexed crawl documents and metadata."""
    from backend.core.database import get_db_connection
    conn = await get_db_connection()
    try:
        cursor = await conn.execute("""
            SELECT id, job_id, canonical_url, title, content_hash, byte_size, trust_level, created_at
            FROM crawl_documents
            WHERE workspace_id = ?
            ORDER BY created_at DESC;
        """, (workspace_id,))
        rows = await cursor.fetchall()
        return {"status": "success", "documents": [dict(r) for r in rows]}
    finally:
        await conn.close()

# ----------------- Phase 5: Memory, Retention & QA Endpoints -----------------

class ProjectMemoryRequest(BaseModel):
    workspace_id: str
    category: str
    title: str
    content: str

class ErrorMemoryRecordRequest(BaseModel):
    workspace_id: str
    raw_error: str
    root_cause: Optional[str] = None
    attempted_fixes: Optional[List[str]] = []
    verified_patch: Optional[str] = None
    regression_test: Optional[str] = None
    is_verified: bool = False

class ErrorLookupRequest(BaseModel):
    workspace_id: str
    raw_error: str

class QARunRequest(BaseModel):
    workspace_id: str
    workspace_path: str
    test_path: Optional[str] = "tests"

class RetentionCleanupRequest(BaseModel):
    dry_run: bool = True
    max_age_hours: Optional[float] = 48.0

@app.post("/api/v1/memory/project")
async def save_project_decision(req: ProjectMemoryRequest):
    """Save an architectural rule or decision into Project Memory."""
    mid = await MemoryEngine.save_project_decision(req.workspace_id, req.category, req.title, req.content)
    return {"status": "success", "memory_id": mid}

@app.get("/api/v1/memory/project")
async def get_project_decisions(workspace_id: str = Query(...)):
    """Fetch project decisions for a workspace."""
    decisions = await MemoryEngine.get_project_decisions(workspace_id)
    return {"status": "success", "decisions": decisions}

@app.post("/api/v1/memory/errors")
async def record_error_memory(req: ErrorMemoryRecordRequest):
    """Record an error signature, root cause, and verified patch into Error Memory."""
    eid = await MemoryEngine.record_error(
        req.workspace_id, req.raw_error, req.root_cause,
        req.attempted_fixes, req.verified_patch, req.regression_test, req.is_verified
    )
    return {"status": "success", "error_id": eid}

@app.post("/api/v1/memory/errors/lookup")
async def lookup_similar_error(req: ErrorLookupRequest):
    """Lookup known solutions for an error signature to prevent error repetition."""
    res = await MemoryEngine.find_similar_error(req.workspace_id, req.raw_error)
    return {"status": "success", "match": res}

@app.post("/api/v1/qa/run")
async def run_qa_tests(req: QARunRequest):
    """Execute test suite via automated QA Agent and verify regressions."""
    res = await QADevAgent.run_tests(req.workspace_id, req.workspace_path, req.test_path or "tests")
    return {"status": "success", "test_report": res}

@app.post("/api/v1/retention/cleanup")
async def run_retention_cleanup(req: RetentionCleanupRequest):
    """Execute retention policy cleanup (48h TTL for temp runs, 7 days for logs)."""
    res = RetentionManager.cleanup_expired_artifacts(dry_run=req.dry_run, max_age_hours=req.max_age_hours or 48.0)
    return {"status": "success", "cleanup_report": res}

# --- Phase 6: Orchestrator Request Models & Endpoints ---

class OrchestratorPlanRequest(BaseModel):
    task_id: str

class OrchestratorExecuteRequest(BaseModel):
    task_id: str
    workspace_path: str

@app.post("/api/v1/orchestrator/plan")
async def create_orchestrator_plan(req: OrchestratorPlanRequest):
    """Decompose TaskSpecification into a DAG plan with specialist agent assignments."""
    try:
        plan = await orchestrator_engine.create_plan_for_task(req.task_id)
        return {"status": "success", "plan": plan.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/orchestrator/plans/{task_id}")
async def get_orchestrator_plan(task_id: str):
    """Retrieve DAG plan and subtasks for a task."""
    plan = await orchestrator_engine.get_plan(task_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"status": "success", "plan": plan.model_dump()}

@app.post("/api/v1/orchestrator/execute/{task_id}")
async def execute_orchestrator_plan(task_id: str, req: OrchestratorExecuteRequest):
    """Execute/resume DAG plan with atomic checkpointing and multi-agent coordination."""
    try:
        plan = await orchestrator_engine.execute_plan(task_id, Path(req.workspace_path))
        return {"status": "success", "plan": plan.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/orchestrator/cancel/{task_id}")
async def cancel_orchestrator_plan(task_id: str):
    """Cancel execution of a task plan."""
    success = await orchestrator_engine.cancel_plan(task_id)
    return {"status": "success", "cancelled": success}

@app.get("/api/v1/orchestrator/agents")
async def list_orchestrator_agents():
    """List registered specialist agents, roles, capabilities, and permission limits."""
    return {"status": "success", "agents": list_agent_profiles()}

# --- Phase 7: Domain Expansion Request Models & Endpoints ---

class DomainExecuteRequest(BaseModel):
    workspace_id: str
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    caller_permissions: List[str] = Field(default_factory=list)

@app.get("/api/v1/domains")
async def list_domains():
    """List all supported domain capability manifests and tool suites."""
    return {"status": "success", "domains": domain_registry.list_domains()}

@app.get("/api/v1/domains/{domain_id}")
async def get_domain_manifest(domain_id: str):
    """Retrieve capability manifest for a specific domain."""
    manifest = domain_registry.get_domain(domain_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_id}' not found")
    return {"status": "success", "manifest": manifest.model_dump()}

@app.get("/api/v1/domains/{domain_id}/license-audit")
async def audit_domain_license(domain_id: str):
    """Verify license compliance and zero hidden cloud costs for a domain."""
    try:
        audit = domain_registry.license_safety_audit(domain_id)
        return {"status": "success", "audit": audit}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@app.post("/api/v1/domains/{domain_id}/execute")
async def execute_domain_action(domain_id: str, req: DomainExecuteRequest):
    """Execute domain action with strict caller permission validation."""
    try:
        res = await domain_registry.execute_domain_action(
            workspace_id=req.workspace_id,
            domain_id=domain_id,
            action=req.action,
            params=req.params,
            caller_permissions=req.caller_permissions
        )
        return {"status": "success", "execution": res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Workspace Projects & File CRUD Endpoints ---

class WorkspaceCreateRequest(BaseModel):
    parent_path: str
    folder_name: str

class FileCreateRequest(BaseModel):
    workspace_path: str
    relative_path: str
    content: Optional[str] = ""

class DirectoryCreateRequest(BaseModel):
    workspace_path: str
    relative_path: str

class ItemRenameRequest(BaseModel):
    workspace_path: str
    old_path: str
    new_path: str

class FileUpdateRequest(BaseModel):
    workspace_id: str
    workspace_path: str
    relative_path: str
    content: str

@app.get("/api/v1/workspace/list")
async def list_workspaces():
    """List all previously opened workspaces/projects."""
    workspaces = await WorkspaceManager.list_workspaces()
    return {"status": "success", "workspaces": workspaces}

@app.delete("/api/v1/workspace/{workspace_id}")
async def remove_workspace(workspace_id: str):
    """Remove a project from the recent workspaces list."""
    removed = await WorkspaceManager.remove_workspace(workspace_id)
    return {"status": "success", "removed": removed}

@app.post("/api/v1/workspace/create")
async def create_workspace(req: WorkspaceCreateRequest):
    """Create a new project directory on disk and register it."""
    try:
        ws = await WorkspaceManager.create_new_workspace(req.parent_path, req.folder_name)
        return {"status": "success", "workspace": ws}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/workspace/file/create")
async def create_file(req: FileCreateRequest):
    """Create a new file within the workspace boundary."""
    try:
        res = await WorkspaceManager.create_file(req.workspace_path, req.relative_path, req.content or "")
        asyncio.create_task(_trigger_reindex(req.workspace_path))
        return {"status": "success", "file": res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except FileExistsError as fe:
        raise HTTPException(status_code=409, detail=str(fe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/workspace/file/mkdir")
async def create_directory(req: DirectoryCreateRequest):
    """Create a new directory within the workspace boundary."""
    try:
        res = await WorkspaceManager.create_directory(req.workspace_path, req.relative_path)
        return {"status": "success", "directory": res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/workspace/file/rename")
async def rename_item(req: ItemRenameRequest):
    """Rename a file or folder within the workspace boundary."""
    try:
        res = await WorkspaceManager.rename_item(req.workspace_path, req.old_path, req.new_path)
        asyncio.create_task(_trigger_reindex(req.workspace_path))
        return {"status": "success", "renamed": res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except FileNotFoundError as fne:
        raise HTTPException(status_code=404, detail=str(fne))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/workspace/file/update")
async def update_file_content(req: FileUpdateRequest):
    """Safely update file content with atomic checkpoint and rollback support."""
    try:
        res = await ExecutionBroker.write_file(
            workspace_id=req.workspace_id,
            workspace_path=req.workspace_path,
            relative_path=req.relative_path,
            new_content=req.content
        )
        asyncio.create_task(_trigger_reindex(req.workspace_path, req.workspace_id))
        return {"status": "success", "updated": res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Skills CRUD Endpoints ---

class SkillCreateRequest(BaseModel):
    name: str
    description: str
    instructions: str
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    workspace_id: Optional[str] = None

class SkillUpdateRequest(BaseModel):
    name: str
    description: str
    instructions: str
    system_prompt: Optional[str] = None
    enabled: Optional[bool] = None

class SkillToggleRequest(BaseModel):
    enabled: bool

@app.get("/api/v1/skills")
async def list_skills(workspace_id: Optional[str] = None):
    """List all registered and built-in skills."""
    from backend.modules.skills.manager import SkillManager
    skills = await SkillManager.list_skills(workspace_id)
    return {"status": "success", "skills": skills}

@app.get("/api/v1/skills/{skill_id}")
async def get_skill(skill_id: str):
    """Get single skill details."""
    from backend.modules.skills.manager import SkillManager
    skill = await SkillManager.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "success", "skill": skill}

@app.post("/api/v1/skills")
async def create_skill(req: SkillCreateRequest):
    """Create a new custom skill with SKILL.md-compatible instructions."""
    from backend.modules.skills.manager import SkillManager
    try:
        res = await SkillManager.create_skill(
            name=req.name,
            description=req.description,
            instructions=req.instructions,
            system_prompt=req.system_prompt,
            tools=req.tools,
            workspace_id=req.workspace_id
        )
        return {"status": "success", "skill": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/v1/skills/{skill_id}")
async def update_skill(skill_id: str, req: SkillUpdateRequest):
    """Update skill description, instructions or enabled status."""
    from backend.modules.skills.manager import SkillManager
    try:
        res = await SkillManager.update_skill(
            skill_id=skill_id,
            name=req.name,
            description=req.description,
            instructions=req.instructions,
            system_prompt=req.system_prompt,
            enabled=req.enabled
        )
        return {"status": "success", "skill": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/skills/{skill_id}/toggle")
async def toggle_skill(skill_id: str, req: SkillToggleRequest):
    """Toggle skill enabled state."""
    from backend.modules.skills.manager import SkillManager
    success = await SkillManager.toggle_skill(skill_id, req.enabled)
    return {"status": "success", "enabled": req.enabled}

@app.delete("/api/v1/skills/{skill_id}")
async def delete_skill(skill_id: str):
    """Delete a custom skill."""
    from backend.modules.skills.manager import SkillManager
    try:
        deleted = await SkillManager.delete_skill(skill_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Skill not found")
        return {"status": "success", "deleted": True}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

# --- MCP Server CRUD Endpoints ---

class MCPServerAddRequest(BaseModel):
    name: str
    command: str
    args: Optional[List[str]] = Field(default_factory=list)
    env: Optional[Dict[str, str]] = Field(default_factory=dict)
    transport: Optional[str] = "stdio"

class MCPServerUpdateRequest(BaseModel):
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]
    enabled: bool

class MCPToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

@app.get("/api/v1/mcp/servers")
async def list_mcp_servers():
    """List configured Model Context Protocol (MCP) servers."""
    from backend.modules.mcp.manager import MCPManager
    servers = await MCPManager.list_servers()
    return {"status": "success", "servers": servers}

@app.post("/api/v1/mcp/servers")
async def add_mcp_server(req: MCPServerAddRequest):
    """Add a new local/remote MCP server configuration."""
    from backend.modules.mcp.manager import MCPManager
    try:
        res = await MCPManager.add_server(
            name=req.name,
            command=req.command,
            args=req.args,
            env=req.env,
            transport=req.transport or "stdio"
        )
        return {"status": "success", "server": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/v1/mcp/servers/{server_id}")
async def update_mcp_server(server_id: str, req: MCPServerUpdateRequest):
    """Update MCP server configuration."""
    from backend.modules.mcp.manager import MCPManager
    try:
        res = await MCPManager.update_server(
            server_id=server_id,
            name=req.name,
            command=req.command,
            args=req.args,
            env=req.env,
            enabled=req.enabled
        )
        return {"status": "success", "server": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/v1/mcp/servers/{server_id}")
async def delete_mcp_server(server_id: str):
    """Remove MCP server configuration."""
    from backend.modules.mcp.manager import MCPManager
    deleted = await MCPManager.delete_server(server_id)
    return {"status": "success", "deleted": deleted}

@app.post("/api/v1/mcp/servers/{server_id}/ping")
async def ping_mcp_server(server_id: str):
    """Test connection and discover tools from MCP server."""
    from backend.modules.mcp.manager import MCPManager
    try:
        res = await MCPManager.test_connection(server_id)
        return {"status": "success", "connection": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/mcp/servers/{server_id}/execute")
async def execute_mcp_tool(server_id: str, req: MCPToolExecuteRequest):
    """Execute an MCP tool call over JSON-RPC 2.0 protocol."""
    from backend.modules.mcp.manager import MCPManager
    try:
        res = await MCPManager.execute_tool(server_id, req.tool_name, req.arguments)
        return {"status": "success", "execution": res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
