import React, { useState, useRef, useEffect } from "react";
import {
  Folder,
  Cpu,
  HardDrive,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Sliders,
  ChevronDown,
  FolderPlus,
  FolderOpen,
  Layers
} from "lucide-react";
import type { SystemInfo, HealthInfo } from "../services/api";

interface TopBarProps {
  workspacePath: string;
  systemInfo?: SystemInfo;
  healthInfo?: HealthInfo;
  recentWorkspaces?: Array<{ id: string; name: string; path: string }>;
  onSelectWorkspace?: (path: string) => void;
  onOpenOtherFolder?: () => void;
  onCreateProject?: () => void;
  onOpenRequirementGate?: () => void;
  onOpenOrchestratorCenter?: () => void;
  onOpenCustomizations?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  workspacePath,
  systemInfo,
  healthInfo,
  recentWorkspaces = [],
  onSelectWorkspace,
  onOpenOtherFolder,
  onCreateProject,
  onOpenRequirementGate,
  onOpenOrchestratorCenter,
  onOpenCustomizations,
}) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const isOllamaOnline = healthInfo?.ollama?.online;

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Extract folder name from path
  const currentFolderName = workspacePath.split(/[\\/]/).filter(Boolean).pop() || workspacePath;

  return (
    <header className="h-13 bg-zinc-950/95 backdrop-blur-md border-b border-zinc-800/80 flex items-center justify-between px-4 text-xs select-none relative z-40 transition-colors">
      {/* Left: Project Selector & Main Customization Actions */}
      <div className="flex items-center gap-2.5 min-w-0">
        {/* Project Switcher Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900/90 hover:bg-zinc-800/90 rounded-xl border border-zinc-700/70 hover:border-zinc-600 text-zinc-100 transition shadow-sm group"
          >
            <div className="w-5 h-5 rounded-md bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
              <Folder size={12} />
            </div>
            <div className="text-left flex items-baseline gap-1.5 min-w-0">
              <span className="font-semibold text-zinc-100 text-xs truncate max-w-[140px]">
                {currentFolderName}
              </span>
              <span className="text-[10px] text-zinc-500 hidden md:inline truncate max-w-[160px]">
                {workspacePath}
              </span>
            </div>
            <ChevronDown
              size={13}
              className={`text-zinc-400 transition-transform duration-200 ml-1 ${
                isDropdownOpen ? "rotate-180 text-indigo-400" : ""
              }`}
            />
          </button>

          {/* Project Switcher Dropdown Menu */}
          {isDropdownOpen && (
            <div className="absolute left-0 top-full mt-2 w-84 bg-zinc-900/95 backdrop-blur-lg border border-zinc-700/80 rounded-2xl shadow-2xl py-2 z-50 animate-in fade-in duration-150 ring-1 ring-white/5">
              <div className="px-3.5 py-1.5 text-[10px] font-bold text-zinc-400 uppercase tracking-wider border-b border-zinc-800 flex justify-between items-center">
                <span>Dự Án Đã Mở</span>
                <span className="text-indigo-400 font-mono text-[9px] bg-indigo-950/80 px-2 py-0.5 rounded-full border border-indigo-800/60">
                  Antigravity Workspaces
                </span>
              </div>

              <div className="max-h-56 overflow-y-auto py-1 px-1.5 space-y-0.5">
                {recentWorkspaces.map((ws) => {
                  const isActive = ws.path.toLowerCase() === workspacePath.toLowerCase();
                  return (
                    <button
                      key={ws.id}
                      onClick={() => {
                        setIsDropdownOpen(false);
                        onSelectWorkspace?.(ws.path);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-xl text-xs flex items-center justify-between transition-all ${
                        isActive
                          ? "bg-indigo-950/60 border border-indigo-500/40 text-indigo-200 font-medium"
                          : "text-zinc-300 hover:bg-zinc-800/70 hover:text-white"
                      }`}
                    >
                      <div className="truncate mr-2">
                        <div className="font-medium text-xs truncate flex items-center gap-1.5">
                          <Folder size={12} className={isActive ? "text-indigo-400" : "text-zinc-500"} />
                          {ws.name}
                        </div>
                        <div className="text-[10px] text-zinc-500 truncate pl-4.5 mt-0.5">
                          {ws.path}
                        </div>
                      </div>
                      {isActive && (
                        <CheckCircle2 size={13} className="text-indigo-400 shrink-0" />
                      )}
                    </button>
                  );
                })}
              </div>

              <div className="border-t border-zinc-800/80 mt-1 pt-1.5 px-1.5 space-y-1 bg-zinc-950/40 rounded-b-xl">
                <button
                  onClick={() => {
                    setIsDropdownOpen(false);
                    onOpenOtherFolder?.();
                  }}
                  className="w-full text-left px-3 py-2 text-xs font-medium text-indigo-300 hover:bg-indigo-950/40 hover:text-indigo-200 rounded-xl flex items-center gap-2 transition"
                >
                  <FolderOpen size={14} className="text-indigo-400" />
                  <span>Duyệt Thư Mục Khác Trên Ổ Đĩa...</span>
                </button>
                <button
                  onClick={() => {
                    setIsDropdownOpen(false);
                    onCreateProject?.();
                  }}
                  className="w-full text-left px-3 py-2 text-xs font-medium text-emerald-300 hover:bg-emerald-950/40 hover:text-emerald-200 rounded-xl flex items-center gap-2 transition"
                >
                  <FolderPlus size={14} className="text-emerald-400" />
                  <span>Tạo Thư Mục Dự Án Mới...</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Separator */}
        <div className="h-5 w-[1px] bg-zinc-800 hidden sm:block" />

        {/* Antigravity Customizations (Skills & MCP) Button */}
        {onOpenCustomizations && (
          <button
            onClick={onOpenCustomizations}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-200 hover:text-white border border-zinc-700/70 hover:border-zinc-600 rounded-xl transition text-xs font-medium shadow-sm whitespace-nowrap shrink-0"
            title="Quản lý Skills & Máy Chủ MCP"
          >
            <Sliders size={13} className="text-indigo-400 shrink-0" />
            <span className="hidden sm:inline whitespace-nowrap">Customizations</span>
            <span className="text-[10px] text-zinc-400 hidden lg:inline whitespace-nowrap">(Skills & MCP)</span>
          </button>
        )}

        {/* Requirement Gate */}
        {onOpenRequirementGate && (
          <button
            onClick={onOpenRequirementGate}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-indigo-950/40 text-zinc-200 hover:text-indigo-200 border border-zinc-700/70 hover:border-indigo-500/40 rounded-xl transition text-xs font-medium shadow-sm whitespace-nowrap shrink-0"
            title="Làm rõ và phân tích yêu cầu thông minh"
          >
            <Sparkles size={13} className="text-indigo-400 shrink-0" />
            <span className="whitespace-nowrap">Requirement Gate</span>
          </button>
        )}

        {/* Orchestrator & Domains */}
        {onOpenOrchestratorCenter && (
          <button
            onClick={onOpenOrchestratorCenter}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-emerald-950/40 text-zinc-200 hover:text-emerald-200 border border-zinc-700/70 hover:border-emerald-500/40 rounded-xl transition text-xs font-medium shadow-sm whitespace-nowrap shrink-0"
            title="Đồ thị DAG & Trung tâm mở rộng 8 domain"
          >
            <Layers size={13} className="text-emerald-400 shrink-0" />
            <span className="hidden sm:inline whitespace-nowrap">Orchestrator</span>
            <span className="text-[10px] text-zinc-400 hidden lg:inline whitespace-nowrap">& Domains</span>
          </button>
        )}
      </div>

      {/* Right: Model Status & Hardware Telemetry */}
      <div className="flex items-center gap-3 text-zinc-400">
        {/* Model Indicator Pill */}
        <div className="flex items-center gap-2 px-2.5 py-1 bg-zinc-900/80 rounded-xl border border-zinc-800 text-xs">
          <div className="flex items-center gap-1.5">
            <Sparkles size={13} className="text-indigo-400" />
            <span className="font-semibold text-zinc-200">Qwen3 4B</span>
          </div>

          <div className="h-3 w-[1px] bg-zinc-700/80" />

          {isOllamaOnline ? (
            <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-medium">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span>RTX 2070 Local</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-[11px] text-amber-400">
              <AlertCircle size={12} />
              <span>Offline</span>
            </div>
          )}
        </div>

        {/* CPU & RAM Telemetry */}
        {systemInfo && (
          <div className="hidden xl:flex items-center gap-3 border-l border-zinc-800/80 pl-3 text-[11px]">
            <div className="flex items-center gap-1.5 text-zinc-400" title="CPU Utilization">
              <Cpu size={13} className="text-zinc-500" />
              <span>{systemInfo.cpu_usage_percent}% CPU</span>
            </div>
            <div className="flex items-center gap-1.5 text-zinc-400" title="RAM Utilization">
              <HardDrive size={13} className="text-zinc-500" />
              <span>{systemInfo.ram_used_percent}% RAM ({systemInfo.ram_available_gb}GB free)</span>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};
