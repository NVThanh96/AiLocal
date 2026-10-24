import { useState, useEffect } from "react";
import {
  Sparkles,
  Server,
  Plus,
  Trash2,
  Save,
  CheckCircle2,
  Play,
  X,
  Code,
  Sliders,
  RefreshCw,
  Terminal,
  Search
} from "lucide-react";
import { api } from "../services/api";
import {
  toastSuccess,
  alertSuccess,
  alertError,
  confirmDialog
} from "../utils/alerts";

interface CustomizationsModalProps {
  workspaceId: string;
  onClose: () => void;
}

export function CustomizationsModal({ workspaceId, onClose }: CustomizationsModalProps) {
  const [activeTab, setActiveTab] = useState<"skills" | "mcp">("skills");

  // --- Skills State ---
  const [skills, setSkills] = useState<any[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<any | null>(null);
  const [isEditingSkill, setIsEditingSkill] = useState(false);
  const [isCreatingSkill, setIsCreatingSkill] = useState(false);
  const [newSkillData, setNewSkillData] = useState({
    name: "",
    description: "",
    system_prompt: "",
    instructions: "# Skill Instructions\n\n1. Rule 1...\n2. Rule 2...",
  });

  // --- MCP Servers State ---
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [selectedServer, setSelectedServer] = useState<any | null>(null);
  const [isAddingServer, setIsAddingServer] = useState(false);
  const [newServerData, setNewServerData] = useState({
    name: "",
    command: "python",
    args: "",
    env: "",
    transport: "stdio",
  });
  const [testToolOutput, setTestToolOutput] = useState<any | null>(null);
  const [isExecutingTool, setIsExecutingTool] = useState(false);
  const [skillFilter, setSkillFilter] = useState("");
  const [mcpFilter, setMcpFilter] = useState("");

  useEffect(() => {
    loadSkills();
    loadMcpServers();
  }, [workspaceId]);

  const loadSkills = async () => {
    try {
      const res = await api.listSkills(workspaceId);
      setSkills(res.skills || []);
      if (res.skills?.length > 0 && !selectedSkill) {
        setSelectedSkill(res.skills[0]);
      }
    } catch (err) {
      console.error("Failed to load skills:", err);
    }
  };

  const loadMcpServers = async () => {
    try {
      const res = await api.listMCPServers();
      setMcpServers(res.servers || []);
      if (res.servers?.length > 0 && !selectedServer) {
        setSelectedServer(res.servers[0]);
      }
    } catch (err) {
      console.error("Failed to load MCP servers:", err);
    }
  };

  // --- Skill Actions ---
  const handleToggleSkill = async (skillId: string, currentStatus: boolean) => {
    try {
      await api.toggleSkill(skillId, !currentStatus);
      await loadSkills();
      if (selectedSkill?.id === skillId) {
        setSelectedSkill({ ...selectedSkill, enabled: !currentStatus });
      }
      toastSuccess(`Đã ${!currentStatus ? "kích hoạt" : "vô hiệu hóa"} skill`);
    } catch (err: any) {
      alertError("Lỗi bật/tắt skill", err.message);
    }
  };

  const handleSaveSkill = async () => {
    if (!selectedSkill) return;
    try {
      await api.updateSkill(selectedSkill.id, {
        name: selectedSkill.name,
        description: selectedSkill.description,
        instructions: selectedSkill.instructions,
        system_prompt: selectedSkill.system_prompt,
      });
      setIsEditingSkill(false);
      await loadSkills();
      toastSuccess("Đã lưu skill thành công!");
    } catch (err: any) {
      alertError("Lỗi lưu skill", err.message);
    }
  };

  const handleCreateSkill = async () => {
    if (!newSkillData.name.trim()) return alertError("Thiếu tên skill", "Vui lòng nhập tên cho skill mới");
    try {
      await api.createSkill({
        ...newSkillData,
        workspace_id: workspaceId,
      });
      setIsCreatingSkill(false);
      setNewSkillData({
        name: "",
        description: "",
        system_prompt: "",
        instructions: "# Skill Instructions\n\n1. Rule 1...",
      });
      await loadSkills();
      toastSuccess(`Đã tạo skill: ${newSkillData.name}`);
    } catch (err: any) {
      alertError("Lỗi tạo skill", err.message);
    }
  };

  const handleDeleteSkill = async (skillId: string) => {
    const confirmed = await confirmDialog({
      title: "Xác nhận xóa skill",
      text: "Bạn có chắc chắn muốn xóa skill này khỏi hệ thống không?",
      confirmText: "Xóa Skill",
      cancelText: "Hủy",
      isDestructive: true,
    });
    if (!confirmed) return;

    try {
      await api.deleteSkill(skillId);
      setSelectedSkill(null);
      await loadSkills();
      toastSuccess("Đã xóa skill thành công");
    } catch (err: any) {
      alertError("Lỗi xóa skill", err.message);
    }
  };

  // --- MCP Actions ---
  const handleAddMcpServer = async () => {
    if (!newServerData.name.trim() || !newServerData.command.trim()) {
      return alertError("Thiếu thông tin", "Vui lòng nhập tên và command cho MCP server");
    }
    try {
      const argsArray = newServerData.args
        ? newServerData.args.split(" ").filter((a) => a.trim())
        : [];
      let envObj = {};
      if (newServerData.env.trim()) {
        try {
          envObj = JSON.parse(newServerData.env);
        } catch {
          newServerData.env.split("\n").forEach((line) => {
            const [k, v] = line.split("=");
            if (k && v) (envObj as any)[k.trim()] = v.trim();
          });
        }
      }
      await api.addMCPServer({
        name: newServerData.name.trim(),
        command: newServerData.command.trim(),
        args: argsArray,
        env: envObj,
        transport: newServerData.transport,
      });
      setIsAddingServer(false);
      setNewServerData({ name: "", command: "python", args: "", env: "", transport: "stdio" });
      await loadMcpServers();
      toastSuccess(`Đã thêm MCP server: ${newServerData.name}`);
    } catch (err: any) {
      alertError("Lỗi thêm MCP server", err.message);
    }
  };

  const handlePingServer = async (serverId: string) => {
    try {
      const res = await api.pingMCPServer(serverId);
      await loadMcpServers();
      if (selectedServer?.id === serverId) {
        setSelectedServer({ ...selectedServer, status: "connected", tools: res.connection.tools });
      }
      alertSuccess("Kết nối MCP thành công!", `Phát hiện ${res.connection.tools_count} công cụ khả dụng.`);
    } catch (err: any) {
      alertError("Lỗi kết nối MCP", err.message);
    }
  };

  const handleDeleteServer = async (serverId: string) => {
    const confirmed = await confirmDialog({
      title: "Xác nhận xóa MCP Server",
      text: "Xóa cấu hình MCP server này khỏi hệ thống?",
      confirmText: "Xóa Server",
      cancelText: "Hủy",
      isDestructive: true,
    });
    if (!confirmed) return;

    try {
      await api.deleteMCPServer(serverId);
      setSelectedServer(null);
      await loadMcpServers();
      toastSuccess("Đã xóa MCP server");
    } catch (err: any) {
      alertError("Lỗi xóa MCP server", err.message);
    }
  };

  const handleExecuteTool = async (toolName: string) => {
    if (!selectedServer) return;
    setIsExecutingTool(true);
    setTestToolOutput(null);
    try {
      const res = await api.executeMCPTool(selectedServer.id, toolName, {
        target: "workspace_verification",
      });
      setTestToolOutput(res.execution);
      toastSuccess(`Tool '${toolName}' thực thi thành công`);
    } catch (err: any) {
      alertError("Lỗi chạy tool", err.message);
    } finally {
      setIsExecutingTool(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-700/80 rounded-xl shadow-2xl w-full max-w-5xl h-[88vh] flex flex-col overflow-hidden text-zinc-100">
        {/* Header */}
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/70">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-950/60 border border-indigo-500/30 rounded-lg text-indigo-400">
              <Sliders size={20} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                Customizations & Extensibility Hub
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800/60 font-mono">
                  ANTIGRAVITY CORE
                </span>
              </h2>
              <p className="text-xs text-zinc-400">
                Skills Protocol (SKILL.md) • Model Context Protocol (MCP) • Anti-Hallucination Grounding
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="bg-zinc-800/80 p-0.5 rounded-lg border border-zinc-700/60 flex text-xs">
              <button
                onClick={() => setActiveTab("skills")}
                className={`px-3 py-1 rounded-md transition flex items-center gap-1.5 ${
                  activeTab === "skills" ? "bg-indigo-600 text-white font-medium" : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Sparkles size={13} />
                <span>Skills ({skills.length})</span>
              </button>
              <button
                onClick={() => setActiveTab("mcp")}
                className={`px-3 py-1 rounded-md transition flex items-center gap-1.5 ${
                  activeTab === "mcp" ? "bg-indigo-600 text-white font-medium" : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Server size={13} />
                <span>MCP Servers ({mcpServers.length})</span>
              </button>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 ml-2"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-hidden flex">
          {activeTab === "skills" ? (
            /* ================= SKILLS TAB ================= */
            <>
              {/* Skills Sidebar */}
              <div className="w-72 border-r border-zinc-800 bg-zinc-950/40 p-3 flex flex-col justify-between">
                <div className="overflow-y-auto space-y-1.5 flex-1 pr-1">
                  <div className="flex items-center justify-between text-[11px] font-semibold text-zinc-500 uppercase px-1 pb-1">
                    <span>Active Skills ({skills.length})</span>
                    <button
                      onClick={() => {
                        setIsCreatingSkill(true);
                        setSelectedSkill(null);
                      }}
                      className="text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5 text-[10px]"
                    >
                      <Plus size={12} /> Thêm Mới
                    </button>
                  </div>

                  <div className="relative my-1">
                    <input
                      type="text"
                      value={skillFilter}
                      onChange={(e) => setSkillFilter(e.target.value)}
                      placeholder="Tìm kiếm skill..."
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-7 pr-2 py-1 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
                    />
                    <Search size={12} className="absolute left-2.5 top-2 text-zinc-500" />
                  </div>

                  {skills.filter(s => s.name.toLowerCase().includes(skillFilter.toLowerCase()) || s.description.toLowerCase().includes(skillFilter.toLowerCase())).map((s) => (
                    <div
                      key={s.id}
                      onClick={() => {
                        setSelectedSkill(s);
                        setIsCreatingSkill(false);
                      }}
                      className={`p-2.5 rounded-lg border transition cursor-pointer flex items-center justify-between text-xs ${
                        selectedSkill?.id === s.id && !isCreatingSkill
                          ? "bg-indigo-950/40 border-indigo-500/40 text-indigo-200"
                          : "bg-zinc-900/60 border-zinc-800/80 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                      }`}
                    >
                      <div className="truncate mr-2">
                        <div className="font-medium text-zinc-200 truncate flex items-center gap-1.5">
                          <span>{s.name}</span>
                          {s.is_builtin && (
                            <span className="text-[9px] px-1 py-0.2 rounded bg-zinc-800 text-zinc-400 font-mono">
                              Core
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-zinc-500 truncate mt-0.5">{s.description}</div>
                      </div>

                      {/* Enable/Disable toggle */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleSkill(s.id, s.enabled);
                        }}
                        className={`w-8 h-4 rounded-full p-0.5 transition shrink-0 ${
                          s.enabled ? "bg-emerald-600" : "bg-zinc-700"
                        }`}
                        title={s.enabled ? "Đang bật" : "Đang tắt"}
                      >
                        <div
                          className={`w-3 h-3 rounded-full bg-white transition transform ${
                            s.enabled ? "translate-x-4" : "translate-x-0"
                          }`}
                        />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Skill Details / Form */}
              <div className="flex-1 p-5 overflow-y-auto space-y-4">
                {isCreatingSkill ? (
                  /* Form tạo mới Skill */
                  <div className="space-y-4">
                    <div className="border-b border-zinc-800 pb-2 flex items-center justify-between">
                      <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                        <Sparkles size={16} className="text-indigo-400" /> Tạo Skill Mới
                      </h3>
                      <button
                        onClick={() => setIsCreatingSkill(false)}
                        className="text-xs text-zinc-400 hover:text-zinc-200"
                      >
                        Hủy
                      </button>
                    </div>

                    <div>
                      <label className="text-xs text-zinc-400 block mb-1">Tên Skill (slug)</label>
                      <input
                        type="text"
                        value={newSkillData.name}
                        onChange={(e) => setNewSkillData({ ...newSkillData, name: e.target.value })}
                        placeholder="e.g. database-migration-expert"
                        className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="text-xs text-zinc-400 block mb-1">Mô tả tóm tắt</label>
                      <input
                        type="text"
                        value={newSkillData.description}
                        onChange={(e) => setNewSkillData({ ...newSkillData, description: e.target.value })}
                        placeholder="Mô tả khi nào nên dùng skill này..."
                        className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="text-xs text-zinc-400 block mb-1">System Prompt bổ trợ</label>
                      <input
                        type="text"
                        value={newSkillData.system_prompt}
                        onChange={(e) => setNewSkillData({ ...newSkillData, system_prompt: e.target.value })}
                        placeholder="Vai trò của AI khi kích hoạt skill..."
                        className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="text-xs text-zinc-400 block mb-1">Hướng Dẫn & Quy Tắc (Markdown SKILL.md)</label>
                      <textarea
                        rows={10}
                        value={newSkillData.instructions}
                        onChange={(e) => setNewSkillData({ ...newSkillData, instructions: e.target.value })}
                        className="w-full font-mono bg-zinc-950 border border-zinc-800 rounded p-3 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <button
                      onClick={handleCreateSkill}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium flex items-center gap-2"
                    >
                      <Save size={14} /> Lưu Skill Mới
                    </button>
                  </div>
                ) : selectedSkill ? (
                  /* Xem & Chỉnh sửa Skill */
                  <div className="space-y-4">
                    <div className="border-b border-zinc-800 pb-3 flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-semibold text-zinc-100">{selectedSkill.name}</h3>
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                              selectedSkill.enabled
                                ? "bg-emerald-950 text-emerald-400 border border-emerald-800/60"
                                : "bg-zinc-800 text-zinc-500"
                            }`}
                          >
                            {selectedSkill.enabled ? "ACTIVE" : "DISABLED"}
                          </span>
                        </div>
                        <p className="text-xs text-zinc-400 mt-1">{selectedSkill.description}</p>
                      </div>

                      <div className="flex items-center gap-2">
                        {!selectedSkill.is_builtin && (
                          <button
                            onClick={() => handleDeleteSkill(selectedSkill.id)}
                            className="p-1.5 bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 rounded border border-rose-800/40 text-xs"
                            title="Xóa skill"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-semibold text-zinc-300 mb-1 flex items-center justify-between">
                        <span>Hướng dẫn thực thi (SKILL.md)</span>
                        <button
                          onClick={() => setIsEditingSkill(!isEditingSkill)}
                          className="text-[11px] text-indigo-400 hover:text-indigo-300"
                        >
                          {isEditingSkill ? "Hủy sửa" : "Chỉnh sửa"}
                        </button>
                      </div>

                      {isEditingSkill ? (
                        <div className="space-y-2">
                          <textarea
                            rows={14}
                            value={selectedSkill.instructions}
                            onChange={(e) => setSelectedSkill({ ...selectedSkill, instructions: e.target.value })}
                            className="w-full font-mono bg-zinc-950 border border-zinc-800 rounded p-3 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                          />
                          <button
                            onClick={handleSaveSkill}
                            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs flex items-center gap-1.5"
                          >
                            <Save size={13} /> Lưu Thay Đổi
                          </button>
                        </div>
                      ) : (
                        <pre className="bg-zinc-950/80 p-4 rounded-lg border border-zinc-800/80 text-xs font-mono text-zinc-300 overflow-x-auto whitespace-pre-wrap max-h-96">
                          {selectedSkill.instructions}
                        </pre>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-xs text-zinc-500 py-12">
                    Chọn một skill bên trái hoặc bấm "Thêm Mới"
                  </div>
                )}
              </div>
            </>
          ) : (
            /* ================= MCP SERVERS TAB ================= */
            <>
              {/* MCP Sidebar */}
              <div className="w-72 border-r border-zinc-800 bg-zinc-950/40 p-3 flex flex-col justify-between">
                <div className="overflow-y-auto space-y-1.5 flex-1 pr-1">
                  <div className="flex items-center justify-between text-[11px] font-semibold text-zinc-500 uppercase px-1 pb-1">
                    <span>Configured Servers ({mcpServers.length})</span>
                    <button
                      onClick={() => {
                        setIsAddingServer(true);
                        setSelectedServer(null);
                      }}
                      className="text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5 text-[10px]"
                    >
                      <Plus size={12} /> Thêm Server
                    </button>
                  </div>

                  <div className="relative my-1">
                    <input
                      type="text"
                      value={mcpFilter}
                      onChange={(e) => setMcpFilter(e.target.value)}
                      placeholder="Tìm kiếm server..."
                      className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-7 pr-2 py-1 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
                    />
                    <Search size={12} className="absolute left-2.5 top-2 text-zinc-500" />
                  </div>

                  {mcpServers.filter(srv => srv.name.toLowerCase().includes(mcpFilter.toLowerCase())).map((srv) => (
                    <div
                      key={srv.id}
                      onClick={() => {
                        setSelectedServer(srv);
                        setIsAddingServer(false);
                      }}
                      className={`p-2.5 rounded-lg border transition cursor-pointer flex items-center justify-between text-xs ${
                        selectedServer?.id === srv.id && !isAddingServer
                          ? "bg-indigo-950/40 border-indigo-500/40 text-indigo-200"
                          : "bg-zinc-900/60 border-zinc-800/80 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                      }`}
                    >
                      <div className="truncate mr-2">
                        <div className="font-medium text-zinc-200 truncate flex items-center gap-1.5">
                          <Terminal size={12} className="text-zinc-500" />
                          <span>{srv.name}</span>
                        </div>
                        <div className="text-[10px] text-zinc-500 font-mono mt-0.5">
                          {srv.command} {srv.args?.slice(0, 2).join(" ")}
                        </div>
                      </div>

                      <span
                        className={`text-[9px] px-1.5 py-0.5 rounded font-mono uppercase ${
                          srv.status === "connected"
                            ? "bg-emerald-950 text-emerald-400 border border-emerald-800/60"
                            : "bg-zinc-800 text-zinc-400"
                        }`}
                      >
                        {srv.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* MCP Details / Add Form */}
              <div className="flex-1 p-5 overflow-y-auto space-y-5">
                {isAddingServer ? (
                  /* Form Thêm Server */
                  <div className="space-y-4">
                    <div className="border-b border-zinc-800 pb-2 flex items-center justify-between">
                      <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                        <Server size={16} className="text-indigo-400" /> Thêm MCP Server Mới
                      </h3>
                      <button
                        onClick={() => setIsAddingServer(false)}
                        className="text-xs text-zinc-400 hover:text-zinc-200"
                      >
                        Hủy
                      </button>
                    </div>

                    <div>
                      <label className="text-xs text-zinc-400 block mb-1">Tên Server (e.g. filesystem)</label>
                      <input
                        type="text"
                        value={newServerData.name}
                        onChange={(e) => setNewServerData({ ...newServerData, name: e.target.value })}
                        placeholder="e.g. postgres-mcp"
                        className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="text-xs text-zinc-400 block mb-1">Command thực thi</label>
                      <input
                        type="text"
                        value={newServerData.command}
                        onChange={(e) => setNewServerData({ ...newServerData, command: e.target.value })}
                        placeholder="python, npx, node, uvx..."
                        className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500 font-mono"
                      />
                    </div>

                    <div>
                      <label className="text-xs text-zinc-400 block mb-1">Arguments (cách nhau bởi khoảng trắng)</label>
                      <input
                        type="text"
                        value={newServerData.args}
                        onChange={(e) => setNewServerData({ ...newServerData, args: e.target.value })}
                        placeholder="-y @modelcontextprotocol/server-postgres postgresql://..."
                        className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500 font-mono"
                      />
                    </div>

                    <button
                      onClick={handleAddMcpServer}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium flex items-center gap-2"
                    >
                      <Save size={14} /> Thêm Server
                    </button>
                  </div>
                ) : selectedServer ? (
                  /* Chi tiết MCP Server */
                  <div className="space-y-4">
                    <div className="border-b border-zinc-800 pb-3 flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-semibold text-zinc-100">{selectedServer.name}</h3>
                          <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono">
                            {selectedServer.transport}
                          </span>
                        </div>
                        <div className="text-xs font-mono text-zinc-400 mt-1">
                          $ {selectedServer.command} {selectedServer.args?.join(" ")}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handlePingServer(selectedServer.id)}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs flex items-center gap-1.5 transition shadow"
                        >
                          <RefreshCw size={13} /> Test Ping & Khám Phá Tools
                        </button>
                        <button
                          onClick={() => handleDeleteServer(selectedServer.id)}
                          className="p-1.5 bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 rounded border border-rose-800/40 text-xs"
                          title="Xóa server"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    {/* Danh sách Tools do Server cung cấp */}
                    <div>
                      <div className="text-xs font-semibold text-zinc-300 mb-2.5 flex items-center gap-2">
                        <Code size={14} className="text-indigo-400" />
                        <span>Danh Sách Công Cụ Đã Đăng Ký ({selectedServer.tools?.length || 0})</span>
                      </div>

                      <div className="space-y-2">
                        {selectedServer.tools && selectedServer.tools.length > 0 ? (
                          selectedServer.tools.map((t: any, idx: number) => (
                            <div
                              key={idx}
                              className="p-3 bg-zinc-950/60 border border-zinc-800 rounded-lg flex items-start justify-between text-xs"
                            >
                              <div>
                                <div className="font-semibold text-indigo-300 font-mono">{t.name}</div>
                                <div className="text-zinc-400 text-[11px] mt-0.5">{t.description}</div>
                                {t.inputSchema?.properties && (
                                  <div className="text-[10px] text-zinc-500 font-mono mt-1">
                                    Params: {Object.keys(t.inputSchema.properties).join(", ")}
                                  </div>
                                )}
                              </div>

                              <button
                                onClick={() => handleExecuteTool(t.name)}
                                disabled={isExecutingTool}
                                className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-[11px] flex items-center gap-1 shrink-0"
                              >
                                <Play size={11} className="text-emerald-400" />
                                <span>Thử Chạy</span>
                              </button>
                            </div>
                          ))
                        ) : (
                          <div className="text-center text-xs text-zinc-500 py-6 border border-zinc-800/60 rounded-lg bg-zinc-950/30">
                            Chưa có tools nào được lưu. Bấm "Test Ping & Khám Phá Tools" ở trên để quét.
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Test Tool Output */}
                    {testToolOutput && (
                      <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg space-y-2">
                        <div className="text-xs font-semibold text-zinc-300 flex items-center justify-between">
                          <span className="flex items-center gap-1.5 text-emerald-400">
                            <CheckCircle2 size={13} /> Kết Quả Thực Thi Tool:
                          </span>
                        </div>
                        <pre className="text-[11px] font-mono bg-zinc-900 p-2.5 rounded border border-zinc-800 text-zinc-300 overflow-x-auto">
                          {JSON.stringify(testToolOutput, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-xs text-zinc-500 py-12">
                    Chọn một MCP server bên trái hoặc bấm "Thêm Server"
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
