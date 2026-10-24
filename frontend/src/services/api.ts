const API_BASE = "http://127.0.0.1:8765/api/v1";

export interface SystemInfo {
  cpu_usage_percent: number;
  ram_total_gb: number;
  ram_available_gb: number;
  ram_used_percent: number;
  disk_free_gb: number;
  disk_total_gb: number;
}

export interface HealthInfo {
  status: string;
  app: string;
  version: string;
  ollama: {
    online: boolean;
    available_models?: string[];
    primary_model_loaded?: boolean;
    error?: string;
  };
}

export interface FileItem {
  name: string;
  path: string;
  type: "file" | "directory";
  size?: number;
  children?: FileItem[];
}

export interface MessageSource {
  file_path: string;
  file_name: string;
  snippet: string;
  score: number;
}

export interface ChatAttachment {
  file_name: string;
  file_type: "image" | "video" | "document" | "audio" | "file";
  extension: string;
  file_size: number;
  file_size_human: string;
  preview_url?: string | null;
  metadata?: Record<string, any>;
  extracted_text?: string;
  summary?: string;
  storage_path?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: MessageSource[];
  attachments?: ChatAttachment[];
  created_at: string;
}

export interface SystemDrive {
  drive: string;
  name: string;
  total_gb: number;
  free_gb: number;
}

export interface BrowseDirectoryItem {
  name: string;
  path: string;
  is_project: boolean;
  modified: number;
}

export interface BrowseDirectoryResponse {
  status: string;
  current_path: string;
  parent_path: string | null;
  breadcrumbs: Array<{ name: string; path: string }>;
  directories: BrowseDirectoryItem[];
}

export const api = {
  async getHealth(): Promise<HealthInfo> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error("Backend offline");
    return res.json();
  },

  async getSystemInfo(): Promise<SystemInfo> {
    const res = await fetch(`${API_BASE}/system/info`);
    if (!res.ok) throw new Error("Failed to load system info");
    return res.json();
  },

  async getSystemDrives(): Promise<{ status: string; drives: SystemDrive[] }> {
    const res = await fetch(`${API_BASE}/system/drives`);
    if (!res.ok) throw new Error("Failed to get system drives");
    return res.json();
  },

  async browseDirectory(path?: string): Promise<BrowseDirectoryResponse> {
    const res = await fetch(`${API_BASE}/system/browse-directory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path || "" }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to browse directory");
    }
    return res.json();
  },

  async createDirectoryOnDisk(parentPath: string, folderName: string): Promise<{ status: string; path: string; name: string }> {
    const res = await fetch(`${API_BASE}/system/create-directory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parent_path: parentPath, folder_name: folderName }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create directory on disk");
    }
    return res.json();
  },

  async openWorkspace(path: string) {
    const res = await fetch(`${API_BASE}/workspace/open`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to open workspace");
    }
    return res.json();
  },

  async getTree(path: string): Promise<{ workspace_path: string; tree: FileItem[] }> {
    const res = await fetch(`${API_BASE}/workspace/tree?path=${encodeURIComponent(path)}`);
    if (!res.ok) throw new Error("Failed to load tree");
    return res.json();
  },

  async readFile(workspacePath: string, relativePath: string) {
    const res = await fetch(`${API_BASE}/workspace/read`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_path: workspacePath, relative_path: relativePath }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Cannot read file");
    }
    const data = await res.json();
    return data.file || data;
  },

  async searchWorkspace(workspaceId: string, query: string) {
    const res = await fetch(`${API_BASE}/workspace/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId, query }),
    });
    return res.json();
  },

  async reindexWorkspace(workspaceId: string, workspacePath: string) {
    const res = await fetch(`${API_BASE}/workspace/reindex`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId, workspace_path: workspacePath }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Reindex failed");
    }
    return res.json();
  },

  async createConversation(workspaceId: string, title: string = "New Chat") {
    const res = await fetch(`${API_BASE}/chat/conversation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId, title }),
    });
    return res.json();
  },

  async updateConversation(conversationId: string, title: string) {
    const res = await fetch(`${API_BASE}/chat/conversation/${conversationId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update conversation");
    }
    return res.json();
  },

  async deleteConversation(conversationId: string) {
    const res = await fetch(`${API_BASE}/chat/conversation/${conversationId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to delete conversation");
    }
    return res.json();
  },

  async clearWorkspaceConversations(workspaceId: string) {
    const res = await fetch(`${API_BASE}/chat/conversations/workspace/${workspaceId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to clear conversations");
    }
    return res.json();
  },

  async batchDeleteConversations(conversationIds: string[]) {
    const res = await fetch(`${API_BASE}/chat/conversations/batch-delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_ids: conversationIds }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to batch delete conversations");
    }
    return res.json();
  },

  async getConversations(workspaceId: string) {
    const res = await fetch(`${API_BASE}/chat/conversations?workspace_id=${workspaceId}`);
    return res.json();
  },

  async getMessages(conversationId: string): Promise<{ messages: ChatMessage[] }> {
    const res = await fetch(`${API_BASE}/chat/messages?conversation_id=${conversationId}`);
    return res.json();
  },

  async uploadChatAttachment(file: File, workspaceId?: string): Promise<{ status: string; attachment: ChatAttachment }> {
    const formData = new FormData();
    formData.append("file", file);
    if (workspaceId) {
      formData.append("workspace_id", workspaceId);
    }
    const res = await fetch(`${API_BASE}/chat/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Không thể tải lên tệp đính kèm");
    }
    return res.json();
  },

  async sendMessage(conversationId: string, content: string, model?: string, attachments?: ChatAttachment[]) {
    const res = await fetch(`${API_BASE}/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: conversationId, content, model, attachments }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Error generating response");
    }
    return res.json();
  },

  async analyzeRequirement(workspaceId: string, workspacePath: string, prompt: string): Promise<{ status: string; task_spec: TaskSpecification }> {
    const res = await fetch(`${API_BASE}/requirements/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId, workspace_path: workspacePath, prompt }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Requirement analysis failed");
    }
    return res.json();
  },

  async clarifyRequirement(taskId: string, questionId: string, chosenOption: string): Promise<{ status: string; task_spec: TaskSpecification }> {
    const res = await fetch(`${API_BASE}/requirements/clarify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId, question_id: questionId, chosen_option: chosenOption }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Clarification submission failed");
    }
    return res.json();
  },

  async approveRequirement(taskId: string, approved: boolean = true): Promise<{ status: string; task_spec: TaskSpecification }> {
    const res = await fetch(`${API_BASE}/requirements/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId, approved }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Approval action failed");
    }
    return res.json();
  },

  async getTaskSpecification(taskId: string): Promise<{ status: string; task_spec: TaskSpecification }> {
    const res = await fetch(`${API_BASE}/requirements/tasks/${taskId}`);
    if (!res.ok) throw new Error("Failed to load task specification");
    return res.json();
  },

  async getTaskVersions(taskId: string): Promise<{ status: string; versions: any[] }> {
    const res = await fetch(`${API_BASE}/requirements/tasks/${taskId}/versions`);
    if (!res.ok) throw new Error("Failed to load task versions");
    return res.json();
  },

  async createOrchestratorPlan(taskId: string) {
    const res = await fetch(`${API_BASE}/orchestrator/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to generate DAG plan");
    }
    return res.json();
  },

  async getOrchestratorPlan(taskId: string) {
    const res = await fetch(`${API_BASE}/orchestrator/plans/${taskId}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to load plan");
    }
    return res.json();
  },

  async executeOrchestratorPlan(taskId: string, workspacePath: string) {
    const res = await fetch(`${API_BASE}/orchestrator/execute/${taskId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId, workspace_path: workspacePath }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Plan execution failed");
    }
    return res.json();
  },

  async getOrchestratorAgents() {
    const res = await fetch(`${API_BASE}/orchestrator/agents`);
    if (!res.ok) throw new Error("Failed to load agent profiles");
    return res.json();
  },

  async getDomains() {
    const res = await fetch(`${API_BASE}/domains`);
    if (!res.ok) throw new Error("Failed to load domains");
    return res.json();
  },

  async auditDomainLicense(domainId: string) {
    const res = await fetch(`${API_BASE}/domains/${domainId}/license-audit`);
    if (!res.ok) throw new Error("License audit failed");
    return res.json();
  },

  async executeDomainAction(workspaceId: string, domainId: string, action: string, params: any = {}, permissions: string[] = []) {
    const res = await fetch(`${API_BASE}/domains/${domainId}/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspace_id: workspaceId,
        action,
        params,
        caller_permissions: permissions,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Domain action execution failed");
    }
    return res.json();
  },

  // --- Workspace Projects & File CRUD ---
  async listWorkspaces() {
    const res = await fetch(`${API_BASE}/workspace/list`);
    if (!res.ok) throw new Error("Failed to load workspace list");
    return res.json();
  },

  async removeWorkspace(workspaceId: string) {
    const res = await fetch(`${API_BASE}/workspace/${workspaceId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to remove workspace");
    return res.json();
  },

  async createNewWorkspace(parentPath: string, folderName: string) {
    const res = await fetch(`${API_BASE}/workspace/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parent_path: parentPath, folder_name: folderName }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create project");
    }
    return res.json();
  },

  async createFile(workspacePath: string, relativePath: string, content: string = "") {
    const res = await fetch(`${API_BASE}/workspace/file/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_path: workspacePath, relative_path: relativePath, content }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create file");
    }
    return res.json();
  },

  async createDirectory(workspacePath: string, relativePath: string) {
    const res = await fetch(`${API_BASE}/workspace/file/mkdir`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_path: workspacePath, relative_path: relativePath }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create folder");
    }
    return res.json();
  },

  async renameItem(workspacePath: string, oldPath: string, newPath: string) {
    const res = await fetch(`${API_BASE}/workspace/file/rename`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_path: workspacePath, old_path: oldPath, new_path: newPath }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to rename item");
    }
    return res.json();
  },

  async updateFile(workspaceId: string, workspacePath: string, relativePath: string, content: string) {
    const res = await fetch(`${API_BASE}/workspace/file/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspace_id: workspaceId,
        workspace_path: workspacePath,
        relative_path: relativePath,
        content,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to update file");
    }
    return res.json();
  },

  async deleteFile(workspaceId: string, workspacePath: string, relativePath: string) {
    const res = await fetch(`${API_BASE}/execution/file/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspace_id: workspaceId,
        workspace_path: workspacePath,
        relative_path: relativePath,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to delete file");
    }
    return res.json();
  },

  // --- Skills Engine CRUD ---
  async listSkills(workspaceId?: string) {
    const url = workspaceId ? `${API_BASE}/skills?workspace_id=${workspaceId}` : `${API_BASE}/skills`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load skills");
    return res.json();
  },

  async getSkill(skillId: string) {
    const res = await fetch(`${API_BASE}/skills/${skillId}`);
    if (!res.ok) throw new Error("Failed to load skill");
    return res.json();
  },

  async createSkill(skillData: { name: string; description: string; instructions: string; system_prompt?: string; tools?: string[]; workspace_id?: string }) {
    const res = await fetch(`${API_BASE}/skills`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(skillData),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create skill");
    }
    return res.json();
  },

  async updateSkill(skillId: string, skillData: { name: string; description: string; instructions: string; system_prompt?: string; enabled?: boolean }) {
    const res = await fetch(`${API_BASE}/skills/${skillId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(skillData),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to update skill");
    }
    return res.json();
  },

  async toggleSkill(skillId: string, enabled: boolean) {
    const res = await fetch(`${API_BASE}/skills/${skillId}/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    if (!res.ok) throw new Error("Failed to toggle skill");
    return res.json();
  },

  async deleteSkill(skillId: string) {
    const res = await fetch(`${API_BASE}/skills/${skillId}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to delete skill");
    }
    return res.json();
  },

  // --- MCP Servers CRUD ---
  async listMCPServers() {
    const res = await fetch(`${API_BASE}/mcp/servers`);
    if (!res.ok) throw new Error("Failed to load MCP servers");
    return res.json();
  },

  async addMCPServer(serverData: { name: string; command: string; args?: string[]; env?: Record<string, string>; transport?: string }) {
    const res = await fetch(`${API_BASE}/mcp/servers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(serverData),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to add MCP server");
    }
    return res.json();
  },

  async updateMCPServer(serverId: string, serverData: { name: string; command: string; args: string[]; env: Record<string, string>; enabled: boolean }) {
    const res = await fetch(`${API_BASE}/mcp/servers/${serverId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(serverData),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to update MCP server");
    }
    return res.json();
  },

  async deleteMCPServer(serverId: string) {
    const res = await fetch(`${API_BASE}/mcp/servers/${serverId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete MCP server");
    return res.json();
  },

  async pingMCPServer(serverId: string) {
    const res = await fetch(`${API_BASE}/mcp/servers/${serverId}/ping`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "MCP ping failed");
    }
    return res.json();
  },

  async executeMCPTool(serverId: string, toolName: string, args: any = {}) {
    const res = await fetch(`${API_BASE}/mcp/servers/${serverId}/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool_name: toolName, arguments: args }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "MCP tool execution failed");
    }
    return res.json();
  },
};

export interface VerifiedFact {
  fact: string;
  source_file: string;
  snippet?: string;
}

export interface UnresolvedQuestion {
  id: string;
  question: string;
  reason: string;
  suggested_options: string[];
  answered: boolean;
  chosen_option?: string;
}

export interface TaskSpecification {
  task_id: string;
  workspace_id: string;
  request_version: number;
  status: "READY" | "NEEDS_CLARIFICATION" | "NEEDS_APPROVAL" | "BLOCKED" | "UNSUPPORTED";
  goal: string;
  original_prompt: string;
  normalized_prompt: string;
  scope: {
    allowed_paths: string[];
    target_files: string[];
    banned_actions: string[];
  };
  constraints: string[];
  verified_facts: VerifiedFact[];
  assumptions: string[];
  unresolved_questions: UnresolvedQuestion[];
  approved_assumptions: string[];
  source_refs: string[];
  acceptance_criteria: string[];
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  required_permissions: string[];
  dependencies: string[];
  assigned_agent?: string;
  created_at: string;
  updated_at: string;
}
