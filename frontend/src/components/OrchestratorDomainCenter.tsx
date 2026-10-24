import { useState, useEffect } from "react";
import {
  ShieldCheck,
  Cpu,
  Layers,
  Play,
  CheckCircle2,
  Lock,
  Globe,
  FileCode,
  DollarSign,
  Briefcase,
  Share2,
  Video,
  Languages,
  Compass,
  X,
  Download,
  Eye,
  AlertCircle,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import { api } from "../services/api";
import { alertError, toastSuccess } from "../utils/alerts";

interface OrchestratorDomainCenterProps {
  workspaceId: string;
  workspacePath: string;
  onClose: () => void;
}

export function OrchestratorDomainCenter({ workspaceId, workspacePath, onClose }: OrchestratorDomainCenterProps) {
  const [activeTab, setActiveTab] = useState<"orchestrator" | "domains">("domains");
  
  // Domains State
  const [domains, setDomains] = useState<any[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<any | null>(null);
  const [domainLicenseAudit, setDomainLicenseAudit] = useState<any | null>(null);
  const [domainActionOutput, setDomainActionOutput] = useState<any | null>(null);
  const [isExecutingAction, setIsExecutingAction] = useState(false);

  // Multi-Agent Orchestrator State
  const [agents, setAgents] = useState<any[]>([]);
  const [dagPlan, setDagPlan] = useState<any | null>(null);
  const [isPlanning, setIsPlanning] = useState(false);
  const [isExecutingPlan, setIsExecutingPlan] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [domRes, agentRes] = await Promise.all([
        api.getDomains(),
        api.getOrchestratorAgents()
      ]);
      setDomains(domRes.domains || []);
      setAgents(agentRes.agents || []);
      if (domRes.domains?.length > 0) {
        selectDomain(domRes.domains[0]);
      }
    } catch (err) {
      console.error("Error loading orchestrator & domain data:", err);
    }
  };

  const selectDomain = async (domain: any) => {
    setSelectedDomain(domain);
    setDomainActionOutput(null);
    try {
      const audit = await api.auditDomainLicense(domain.domain_id);
      setDomainLicenseAudit(audit.audit);
    } catch (err) {
      console.error("License audit failed:", err);
    }
  };

  const [planPrompt, setPlanPrompt] = useState("Kiểm toán mã nguồn, bảo mật & cập nhật sơ đồ kiến trúc hệ thống");
  const [selectedSubtask, setSelectedSubtask] = useState<any | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string>("");

  const handleTestDomainAction = async () => {
    if (!selectedDomain || !workspaceId) {
      alertError("Chưa chọn Workspace", "Vui lòng mở một dự án trước khi thực thi domain action.");
      return;
    }
    setIsExecutingAction(true);
    setDomainActionOutput(null);
    try {
      const actionName = selectedDomain.tools[0] || "execute_default";
      const res = await api.executeDomainAction(
        workspaceId,
        selectedDomain.domain_id,
        actionName,
        { prompt: `Verify ${selectedDomain.name} local capability` },
        selectedDomain.required_permissions
      );
      setDomainActionOutput(res.execution);
      toastSuccess(`Đã thực thi thành công: ${actionName}`);
    } catch (err: any) {
      alertError("Lỗi thực thi Domain", err.message || "Không thể thực thi hành động domain");
    } finally {
      setIsExecutingAction(false);
    }
  };

  const handleGenerateDAGPlanOnly = async () => {
    if (!workspaceId) {
      alertError("Chưa chọn Workspace", "Vui lòng mở một dự án trước khi sinh DAG plan.");
      return;
    }
    setIsPlanning(true);
    setSelectedSubtask(null);
    try {
      const reqRes = await api.analyzeRequirement(
        workspaceId,
        workspacePath,
        planPrompt.trim() || "Kiểm toán mã nguồn, bảo mật & cập nhật sơ đồ kiến trúc hệ thống"
      );
      const taskId = reqRes.task_spec.task_id;
      setActiveTaskId(taskId);

      const planRes = await api.createOrchestratorPlan(taskId);
      setDagPlan(planRes.plan);
      toastSuccess(`Đã sinh thành công DAG Plan gồm ${planRes.plan.subtasks.length} bước`);
    } catch (err: any) {
      alertError("Lỗi sinh kế hoạch DAG", err.message || "Không thể tạo kế hoạch DAG cho yêu cầu này");
    } finally {
      setIsPlanning(false);
    }
  };

  const handleExecuteCurrentPlan = async () => {
    if (!activeTaskId || !dagPlan) {
      alertError("Chưa có Kế Hoạch", "Vui lòng nhấn 'Sinh Kế Hoạch DAG' trước khi thực thi.");
      return;
    }
    setIsExecutingPlan(true);
    try {
      const execRes = await api.executeOrchestratorPlan(activeTaskId, workspacePath);
      setDagPlan(execRes.plan);
      toastSuccess("Đã thực thi toàn bộ quy trình DAG thành công!");
    } catch (err: any) {
      alertError("Lỗi thực thi DAG Plan", err.message || "Quá trình thực thi kế hoạch gặp lỗi");
    } finally {
      setIsExecutingPlan(false);
    }
  };

  const handleCreateAndRunDAGPlan = async () => {
    if (!workspaceId) {
      alertError("Chưa chọn Workspace", "Vui lòng mở một dự án trước khi chạy DAG.");
      return;
    }
    setIsPlanning(true);
    setSelectedSubtask(null);
    try {
      // 1. Analyze prompt to create a task
      const reqRes = await api.analyzeRequirement(
        workspaceId,
        workspacePath,
        planPrompt.trim() || "Kiểm toán mã nguồn, bảo mật & cập nhật sơ đồ kiến trúc hệ thống"
      );
      const taskId = reqRes.task_spec.task_id;
      setActiveTaskId(taskId);

      // 2. Generate DAG Plan
      const planRes = await api.createOrchestratorPlan(taskId);
      setDagPlan(planRes.plan);

      // 3. Execute Plan
      setIsExecutingPlan(true);
      setIsPlanning(false);
      const execRes = await api.executeOrchestratorPlan(taskId, workspacePath);
      setDagPlan(execRes.plan);
      toastSuccess("Đã hoàn thành sinh và thực thi toàn bộ DAG Plan!");
    } catch (err: any) {
      alertError("Lỗi Orchestrator DAG", err.message || "Gặp sự cố khi sinh hoặc thực thi DAG");
    } finally {
      setIsPlanning(false);
      setIsExecutingPlan(false);
    }
  };

  const handleExportPlanJSON = () => {
    if (!dagPlan) return;
    try {
      const jsonStr = JSON.stringify(dagPlan, null, 2);
      navigator.clipboard.writeText(jsonStr);
      toastSuccess("Đã sao chép cấu trúc DAG Plan JSON vào Clipboard");
    } catch {
      // fallback
    }
  };

  const getDomainIcon = (id: string) => {
    switch (id) {
      case "research": return <Globe className="text-cyan-400" size={18} />;
      case "design": return <FileCode className="text-pink-400" size={18} />;
      case "finance": return <DollarSign className="text-emerald-400" size={18} />;
      case "ceo_strategy": return <Briefcase className="text-indigo-400" size={18} />;
      case "marketing": return <Share2 className="text-amber-400" size={18} />;
      case "media": return <Video className="text-rose-400" size={18} />;
      case "translation": return <Languages className="text-teal-400" size={18} />;
      case "browser_automation": return <Compass className="text-violet-400" size={18} />;
      default: return <Layers className="text-zinc-400" size={18} />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-700/80 rounded-xl shadow-2xl w-full max-w-5xl h-[88vh] flex flex-col overflow-hidden text-zinc-100">
        {/* Header */}
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/70">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-950/60 border border-indigo-500/30 rounded-lg text-indigo-400">
              <Cpu size={20} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                Multi-Agent Orchestrator & Domain Expansion Center
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/60 font-mono">
                  PHASE 6 & 7 ACTIVE
                </span>
              </h2>
              <p className="text-xs text-zinc-400">
                100% Local-First DAG Workflow • Permissive License Governance • Strict Permission Boundaries
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Tab switch */}
            <div className="bg-zinc-800/80 p-0.5 rounded-lg border border-zinc-700/60 flex text-xs">
              <button
                onClick={() => setActiveTab("domains")}
                className={`px-3 py-1 rounded-md transition ${
                  activeTab === "domains" ? "bg-indigo-600 text-white font-medium" : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                8 Core Domains
              </button>
              <button
                onClick={() => setActiveTab("orchestrator")}
                className={`px-3 py-1 rounded-md transition ${
                  activeTab === "orchestrator" ? "bg-indigo-600 text-white font-medium" : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Multi-Agent DAG Planner
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
          {activeTab === "domains" ? (
            <>
              {/* Domain List Sidebar */}
              <div className="w-72 border-r border-zinc-800 bg-zinc-950/40 p-3 overflow-y-auto space-y-1.5">
                <div className="text-[11px] font-semibold text-zinc-500 uppercase px-2 pb-1">
                  Available Domains (8)
                </div>
                {domains.map((dom) => (
                  <button
                    key={dom.domain_id}
                    onClick={() => selectDomain(dom)}
                    className={`w-full text-left p-2.5 rounded-lg border transition flex items-center justify-between text-xs ${
                      selectedDomain?.domain_id === dom.domain_id
                        ? "bg-indigo-950/40 border-indigo-500/40 text-indigo-200"
                        : "bg-zinc-900/60 border-zinc-800/80 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      {getDomainIcon(dom.domain_id)}
                      <div>
                        <div className="font-medium text-zinc-200">{dom.name}</div>
                        <div className="text-[10px] text-zinc-500 font-mono">{dom.license_type}</div>
                      </div>
                    </div>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 uppercase font-mono">
                      {dom.risk_assessment}
                    </span>
                  </button>
                ))}
              </div>

              {/* Domain Detail & Action Playground */}
              <div className="flex-1 p-5 overflow-y-auto space-y-5">
                {selectedDomain && (
                  <>
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2.5">
                          {getDomainIcon(selectedDomain.domain_id)}
                          <h3 className="text-lg font-semibold text-zinc-100">{selectedDomain.name}</h3>
                          <span className="text-xs px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-400 border border-indigo-800/60 font-mono">
                            v{selectedDomain.version}
                          </span>
                        </div>
                        <p className="text-xs text-zinc-400 mt-1">{selectedDomain.description}</p>
                      </div>

                      {/* License Shield */}
                      {domainLicenseAudit && (
                        <div className="bg-emerald-950/30 border border-emerald-500/30 p-2.5 rounded-lg flex items-center gap-2 text-xs text-emerald-400">
                          <ShieldCheck size={18} className="text-emerald-400 shrink-0" />
                          <div>
                            <div className="font-semibold text-emerald-300">
                              License: {domainLicenseAudit.license_type} (Permissive)
                            </div>
                            <div className="text-[10px] text-emerald-500">
                              Commercial Allowed • Zero Cloud Costs • Local Only
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Permissions & Tool Grid */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-zinc-950/60 border border-zinc-800/80 rounded-lg">
                        <div className="text-xs font-semibold text-zinc-300 mb-2 flex items-center gap-1.5">
                          <Lock size={13} className="text-amber-400" /> Required Permissions
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedDomain.required_permissions.map((p: string, idx: number) => (
                            <span
                              key={idx}
                              className="text-[11px] px-2 py-0.5 rounded bg-zinc-800/90 text-amber-300 border border-amber-900/40 font-mono"
                            >
                              {p}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="p-3 bg-zinc-950/60 border border-zinc-800/80 rounded-lg">
                        <div className="text-xs font-semibold text-zinc-300 mb-2 flex items-center gap-1.5">
                          <Layers size={13} className="text-indigo-400" /> Registered Tools
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedDomain.tools.map((t: string, idx: number) => (
                            <span
                              key={idx}
                              className="text-[11px] px-2 py-0.5 rounded bg-zinc-800/90 text-indigo-300 border border-indigo-900/40 font-mono"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Acceptance Criteria */}
                    <div className="p-3 bg-zinc-950/60 border border-zinc-800/80 rounded-lg">
                      <div className="text-xs font-semibold text-zinc-300 mb-2 flex items-center gap-1.5">
                        <CheckCircle2 size={13} className="text-emerald-400" /> Acceptance Criteria & Constraints
                      </div>
                      <ul className="text-xs text-zinc-400 space-y-1 list-disc list-inside">
                        {selectedDomain.acceptance_criteria.map((c: string, idx: number) => (
                          <li key={idx}>{c}</li>
                        ))}
                      </ul>
                    </div>

                    {/* Action Execution Button */}
                    <div className="pt-2">
                      <button
                        onClick={handleTestDomainAction}
                        disabled={isExecutingAction}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium flex items-center gap-2 shadow-lg transition"
                      >
                        <Play size={14} />
                        {isExecutingAction ? "Executing Domain Test..." : `Test ${selectedDomain.name} Capability`}
                      </button>
                    </div>

                    {/* Execution Output */}
                    {domainActionOutput && (
                      <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-lg space-y-2">
                        <div className="text-xs font-semibold text-zinc-300 flex items-center justify-between">
                          <span>Deterministic Verification Output:</span>
                          <span className="text-[10px] text-emerald-400 font-mono">STATUS: {domainActionOutput.status}</span>
                        </div>
                        <pre className="text-[11px] font-mono bg-zinc-900/80 p-3 rounded border border-zinc-800 text-zinc-300 overflow-x-auto max-h-56">
                          {JSON.stringify(domainActionOutput.result, null, 2)}
                        </pre>
                      </div>
                    )}
                  </>
                )}
              </div>
            </>
          ) : (
            /* Multi-Agent Orchestrator View */
            <div className="flex-1 p-5 overflow-y-auto space-y-6">
              {/* Header & Goal Configuration */}
              <div className="space-y-3 p-4 bg-zinc-950/80 border border-zinc-800 rounded-xl">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                      <Cpu size={18} className="text-indigo-400" />
                      Multi-Agent DAG Execution Engine
                    </h3>
                    <p className="text-xs text-zinc-400">
                      Phân rã yêu cầu thành các bước DAG đa tác tử, cô lập lỗi và quản lý khóa tệp song song.
                    </p>
                  </div>
                </div>

                {/* Custom Goal Input */}
                <div className="space-y-2 pt-1">
                  <label className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                    <Sparkles size={13} className="text-amber-400" />
                    Mục tiêu / Yêu cầu Kế hoạch DAG (Goal Specification):
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={planPrompt}
                      onChange={(e) => setPlanPrompt(e.target.value)}
                      placeholder="Nhập mục tiêu phân rã DAG..."
                      className="flex-1 px-3 py-2 bg-zinc-900 border border-zinc-700/80 rounded-lg text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  {/* Preset Pills */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <span className="text-[10px] text-zinc-500 self-center">Gợi ý:</span>
                    {[
                      "Kiểm toán mã nguồn, bảo mật & cập nhật sơ đồ kiến trúc",
                      "Thực thi tính năng mới với kiểm tra đơn vị và tích hợp",
                      "Tối ưu hóa hiệu năng & dọn dẹp nợ kỹ thuật",
                      "Sản xuất media đa kênh: AI Video, Whisper subtitles"
                    ].map((preset, idx) => (
                      <button
                        key={idx}
                        onClick={() => setPlanPrompt(preset)}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-indigo-300 border border-zinc-800 hover:border-zinc-700 transition"
                      >
                        {preset}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Action Buttons Toolbar */}
                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-zinc-800/60">
                  <button
                    onClick={handleGenerateDAGPlanOnly}
                    disabled={isPlanning || isExecutingPlan}
                    className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 shadow transition"
                  >
                    <Layers size={13} />
                    {isPlanning ? "Đang phân tích & sinh DAG..." : "Sinh Kế Hoạch DAG"}
                  </button>

                  <button
                    onClick={handleExecuteCurrentPlan}
                    disabled={!dagPlan || isPlanning || isExecutingPlan}
                    className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 shadow transition"
                  >
                    <Play size={13} />
                    {isExecutingPlan ? "Đang thực thi DAG..." : "Thực Thi Toàn Bộ DAG"}
                  </button>

                  <button
                    onClick={handleCreateAndRunDAGPlan}
                    disabled={isPlanning || isExecutingPlan}
                    className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-zinc-200 rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
                  >
                    <Sparkles size={13} className="text-amber-400" />
                    Sinh & Chạy Ngay
                  </button>

                  {dagPlan && (
                    <button
                      onClick={handleExportPlanJSON}
                      className="px-3 py-1.5 bg-zinc-850 hover:bg-zinc-800 text-zinc-300 border border-zinc-700/60 rounded-lg text-xs font-medium flex items-center gap-1.5 ml-auto transition"
                      title="Sao chép cấu trúc DAG Plan JSON"
                    >
                      <Download size={13} />
                      Xuất JSON Plan
                    </button>
                  )}
                </div>
              </div>

              {/* Registered Agents Grid */}
              <div>
                <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2.5">
                  Specialist Agent Registry ({agents.length})
                </div>
                <div className="grid grid-cols-5 gap-3">
                  {agents.map((ag) => (
                    <div
                      key={ag.role}
                      className="p-3 bg-zinc-950/70 border border-zinc-800 rounded-lg flex flex-col justify-between"
                    >
                      <div>
                        <div className="text-xs font-semibold text-zinc-200">{ag.name}</div>
                        <div className="text-[10px] text-zinc-500 font-mono mt-0.5">Role: {ag.role}</div>
                        <p className="text-[11px] text-zinc-400 mt-2 line-clamp-3">{ag.description}</p>
                      </div>
                      <div className="mt-3 pt-2 border-t border-zinc-800/80 text-[10px] text-indigo-400 font-mono">
                        Permissions: {ag.allowed_permissions.length}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Live DAG Subtasks & Inspector */}
              {dagPlan && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs font-semibold text-zinc-300">
                    <span className="flex items-center gap-2">
                      DAG Plan: <span className="font-mono text-indigo-400">{dagPlan.id}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-mono ${
                        dagPlan.status === "completed" ? "bg-emerald-950 text-emerald-400 border border-emerald-800/60" : "bg-zinc-800 text-zinc-300"
                      }`}>
                        {dagPlan.status}
                      </span>
                    </span>
                    <span className="text-zinc-500 text-[11px]">Subtasks: {dagPlan.subtasks.length} (Nhấp vào để xem chi tiết)</span>
                  </div>

                  <div className="space-y-2">
                    {dagPlan.subtasks.map((st: any, idx: number) => {
                      const isSelected = selectedSubtask?.id === st.id;
                      return (
                        <div
                          key={st.id}
                          onClick={() => setSelectedSubtask(isSelected ? null : st)}
                          className={`p-3 rounded-lg border flex items-center justify-between text-xs transition cursor-pointer ${
                            isSelected ? "ring-1 ring-indigo-500 shadow-md " : ""
                          }${
                            st.status === "completed"
                              ? "bg-emerald-950/20 border-emerald-800/40 text-emerald-200 hover:bg-emerald-950/30"
                              : st.status === "running"
                              ? "bg-amber-950/20 border-amber-800/40 text-amber-200 hover:bg-amber-950/30"
                              : st.status === "failed" || st.status === "blocked"
                              ? "bg-rose-950/20 border-rose-800/40 text-rose-200 hover:bg-rose-950/30"
                              : "bg-zinc-950/60 border-zinc-800 text-zinc-400 hover:bg-zinc-900"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <span className="font-mono text-[11px] text-zinc-500">#{idx + 1}</span>
                            <div>
                              <div className="font-medium text-zinc-100 flex items-center gap-1.5">
                                {st.title}
                                <Eye size={12} className="text-zinc-500 opacity-60" />
                              </div>
                              <div className="text-[10px] text-zinc-400 flex items-center gap-2 font-mono mt-0.5">
                                <span className="text-indigo-400">Agent: {st.assigned_agent}</span>
                                {st.depends_on.length > 0 && (
                                  <span>Depends: [{st.depends_on.join(", ")}]</span>
                                )}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded font-mono uppercase font-semibold ${
                                st.status === "completed"
                                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800/60"
                                  : st.status === "running"
                                  ? "bg-amber-950 text-amber-400 border border-amber-800/60"
                                  : st.status === "blocked"
                                  ? "bg-rose-950 text-rose-400 border border-rose-800/60"
                                  : "bg-zinc-800 text-zinc-400"
                              }`}
                            >
                              {st.status}
                            </span>
                            <ChevronRight size={13} className={`text-zinc-500 transition-transform ${isSelected ? "rotate-90" : ""}`} />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Subtask Inspector Drawer */}
                  {selectedSubtask && (
                    <div className="p-4 bg-zinc-950 border border-indigo-900/50 rounded-xl space-y-3 animate-in fade-in duration-150">
                      <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                        <div className="flex items-center gap-2">
                          <Eye size={15} className="text-indigo-400" />
                          <span className="font-semibold text-xs text-zinc-200">Chi Tiết Bước #{selectedSubtask.id}: {selectedSubtask.title}</span>
                        </div>
                        <button
                          onClick={() => setSelectedSubtask(null)}
                          className="text-zinc-400 hover:text-zinc-200 text-xs"
                        >
                          ✕
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <span className="text-zinc-500 font-medium">Assigned Agent:</span>
                          <span className="font-mono text-indigo-300 ml-1.5">{selectedSubtask.assigned_agent}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500 font-medium">Permissions:</span>
                          <span className="font-mono text-zinc-300 ml-1.5">{selectedSubtask.required_permissions?.join(", ") || "None"}</span>
                        </div>
                      </div>

                      {selectedSubtask.error_message && (
                        <div className="p-2.5 bg-rose-950/40 border border-rose-800/60 rounded-lg text-xs text-rose-300 flex items-center gap-2">
                          <AlertCircle size={14} className="shrink-0 text-rose-400" />
                          <span>{selectedSubtask.error_message}</span>
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Input Context:</span>
                          <pre className="text-[11px] font-mono bg-zinc-900/90 p-2.5 rounded border border-zinc-800 text-zinc-300 overflow-x-auto max-h-40">
                            {JSON.stringify(selectedSubtask.input_context, null, 2)}
                          </pre>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Result Output:</span>
                          <pre className="text-[11px] font-mono bg-zinc-900/90 p-2.5 rounded border border-zinc-800 text-emerald-300 overflow-x-auto max-h-40">
                            {JSON.stringify(selectedSubtask.result_output, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
