import React, { useState, useEffect } from "react";
import {
  Folder,
  FolderOpen,
  FolderPlus,
  HardDrive,
  ChevronRight,
  ArrowUp,
  RefreshCw,
  Search,
  CheckCircle2,
  X,
  Code2
} from "lucide-react";
import { api } from "../services/api";
import type { SystemDrive, BrowseDirectoryItem } from "../services/api";
import { toastSuccess, alertError } from "../utils/alerts";

interface FolderPickerModalProps {
  initialPath?: string;
  defaultMode?: "open" | "create";
  onClose: () => void;
  onSelectFolder: (path: string) => Promise<void>;
}

export const FolderPickerModal: React.FC<FolderPickerModalProps> = ({
  initialPath = "H:\\",
  defaultMode = "open",
  onClose,
  onSelectFolder,
}) => {
  const [mode, setMode] = useState<"open" | "create">(defaultMode);
  const [drives, setDrives] = useState<SystemDrive[]>([]);
  const [currentPath, setCurrentPath] = useState<string>(initialPath);
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [breadcrumbs, setBreadcrumbs] = useState<Array<{ name: string; path: string }>>([]);
  const [directories, setDirectories] = useState<BrowseDirectoryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [newFolderName, setNewFolderName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load drives once on mount
  useEffect(() => {
    loadDrives();
  }, []);

  // Browse directory whenever currentPath changes
  useEffect(() => {
    loadDirectory(currentPath);
  }, [currentPath]);

  const loadDrives = async () => {
    try {
      const res = await api.getSystemDrives();
      setDrives(res.drives || []);
    } catch (err) {
      console.error("Failed to load drives:", err);
    }
  };

  const loadDirectory = async (targetPath: string) => {
    setIsLoading(true);
    setSelectedFolder(null);
    try {
      const res = await api.browseDirectory(targetPath);
      setCurrentPath(res.current_path);
      setParentPath(res.parent_path);
      setBreadcrumbs(res.breadcrumbs || []);
      setDirectories(res.directories || []);
    } catch (err: any) {
      alertError("Không thể đọc thư mục", err.message || "Vui lòng kiểm tra quyền truy cập");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectFolder = (folderPath: string) => {
    setSelectedFolder(folderPath);
  };

  const handleDrillDown = (folderPath: string) => {
    setCurrentPath(folderPath);
    setSearchQuery("");
  };

  const handleGoUp = () => {
    if (parentPath) {
      setCurrentPath(parentPath);
      setSearchQuery("");
    }
  };

  const handleConfirmOpen = async () => {
    const target = selectedFolder || currentPath;
    if (!target) return;
    setIsSubmitting(true);
    try {
      await onSelectFolder(target);
      toastSuccess(`Đã mở dự án: ${target.split(/[\\/]/).filter(Boolean).pop()}`);
      onClose();
    } catch (err: any) {
      alertError("Lỗi mở dự án", err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmCreate = async () => {
    if (!newFolderName.trim()) {
      alertError("Thiếu tên thư mục", "Vui lòng nhập tên thư mục dự án mới");
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await api.createDirectoryOnDisk(currentPath, newFolderName.trim());
      await onSelectFolder(res.path);
      toastSuccess(`Đã tạo và mở dự án: ${res.name}`);
      onClose();
    } catch (err: any) {
      alertError("Lỗi tạo dự án mới", err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Filter directories by search query
  const filteredDirectories = directories.filter((d) =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-zinc-900 border border-zinc-700/80 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden text-zinc-100 font-sans">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <FolderOpen size={20} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                Bộ Chọn Thư Mục Dự Án (Project Explorer)
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-950/80 border border-indigo-800 text-indigo-300">
                  Antigravity Core
                </span>
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Chọn một thư mục bất kỳ trên máy tính để tập trung phát triển phần mềm độc lập
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Mode Switcher */}
            <div className="flex bg-zinc-950 p-1 rounded-xl border border-zinc-800 text-xs">
              <button
                onClick={() => setMode("open")}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  mode === "open"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <FolderOpen size={13} /> Mở Dự Án Có Sẵn
              </button>
              <button
                onClick={() => setMode("create")}
                className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                  mode === "create"
                    ? "bg-emerald-600 text-white shadow"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <FolderPlus size={13} /> Tạo Dự Án Mới
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Drives Navigation Bar */}
        <div className="px-6 py-2.5 bg-zinc-950/40 border-b border-zinc-800/80 flex items-center gap-2 overflow-x-auto text-xs">
          <span className="text-zinc-500 font-medium shrink-0 flex items-center gap-1">
            <HardDrive size={13} /> Ổ Đĩa:
          </span>
          {drives.map((d) => {
            const isCurrentDrive = currentPath.toLowerCase().startsWith(d.drive.toLowerCase());
            return (
              <button
                key={d.drive}
                onClick={() => setCurrentPath(d.drive)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition shrink-0 ${
                  isCurrentDrive
                    ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/50"
                    : "bg-zinc-800/60 hover:bg-zinc-800 text-zinc-300 border border-zinc-700/60"
                }`}
              >
                <span>{d.drive}</span>
                {d.free_gb > 0 && (
                  <span className="text-[10px] text-zinc-400">({d.free_gb}GB free)</span>
                )}
              </button>
            );
          })}
        </div>

        {/* Breadcrumb & Navigation Controls */}
        <div className="px-6 py-2.5 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between gap-3 text-xs">
          {/* Breadcrumb Trail */}
          <div className="flex items-center gap-1 overflow-x-auto min-w-0 py-0.5">
            <button
              onClick={handleGoUp}
              disabled={!parentPath}
              className="p-1.5 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 disabled:hover:bg-zinc-800 text-zinc-300 shrink-0 mr-1"
              title="Lên thư mục cha"
            >
              <ArrowUp size={13} />
            </button>

            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={crumb.path}>
                {idx > 0 && <ChevronRight size={12} className="text-zinc-600 shrink-0" />}
                <button
                  onClick={() => setCurrentPath(crumb.path)}
                  className={`px-2 py-1 rounded hover:bg-zinc-800 font-medium truncate max-w-[140px] transition ${
                    idx === breadcrumbs.length - 1
                      ? "text-indigo-300 font-semibold bg-zinc-800/60"
                      : "text-zinc-400"
                  }`}
                >
                  {crumb.name}
                </button>
              </React.Fragment>
            ))}
          </div>

          {/* Search Filter */}
          <div className="relative shrink-0 w-56">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Lọc thư mục..."
              className="w-full bg-zinc-950 border border-zinc-700/80 rounded-lg pl-7 pr-3 py-1 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
            />
            <Search size={12} className="absolute left-2.5 top-2 text-zinc-500" />
          </div>
        </div>

        {/* Directory Explorer Grid */}
        <div className="flex-1 overflow-y-auto p-6 min-h-[300px]">
          {isLoading ? (
            <div className="h-full flex flex-col items-center justify-center text-zinc-500 gap-2 py-16">
              <RefreshCw size={24} className="animate-spin text-indigo-400" />
              <p className="text-xs">Đang quét danh sách thư mục...</p>
            </div>
          ) : filteredDirectories.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-zinc-500 py-16 text-center">
              <Folder size={36} className="text-zinc-600 mb-2 stroke-1" />
              <p className="text-sm font-medium text-zinc-400">Không tìm thấy thư mục con nào</p>
              <p className="text-xs text-zinc-500 mt-1">
                {searchQuery ? "Thử tìm kiếm với từ khóa khác" : "Thư mục này hiện tại đang trống"}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
              {filteredDirectories.map((dir) => {
                const isSelected = selectedFolder === dir.path;
                return (
                  <div
                    key={dir.path}
                    onClick={() => handleSelectFolder(dir.path)}
                    onDoubleClick={() => handleDrillDown(dir.path)}
                    className={`group p-3 rounded-xl border text-left cursor-pointer transition-all flex items-start gap-3 select-none ${
                      isSelected
                        ? "bg-indigo-950/50 border-indigo-500/80 shadow-md ring-1 ring-indigo-500/50"
                        : "bg-zinc-950/40 hover:bg-zinc-800/60 border-zinc-800/80 hover:border-zinc-700"
                    }`}
                  >
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 transition ${
                        isSelected
                          ? "bg-indigo-600 text-white"
                          : dir.is_project
                          ? "bg-emerald-950/80 border border-emerald-700/60 text-emerald-400"
                          : "bg-zinc-800 border border-zinc-700/60 text-amber-400 group-hover:scale-105"
                      }`}
                    >
                      {dir.is_project ? <Code2 size={16} /> : <Folder size={16} />}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-xs text-zinc-200 truncate group-hover:text-white">
                          {dir.name}
                        </span>
                        {dir.is_project && (
                          <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 shrink-0">
                            PROJ
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] text-zinc-500 mt-0.5 truncate">
                        Nhấp đúp để vào trong
                      </p>
                    </div>

                    {isSelected && (
                      <CheckCircle2 size={14} className="text-indigo-400 shrink-0 mt-0.5" />
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-zinc-800 bg-zinc-950/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          {/* Target Preview */}
          <div className="min-w-0 flex-1">
            <div className="text-[11px] text-zinc-500 font-medium">Thư mục đã chọn:</div>
            <div className="text-xs font-mono text-zinc-200 truncate mt-0.5 bg-zinc-900 border border-zinc-800 px-2.5 py-1 rounded-lg">
              {mode === "create"
                ? `${currentPath}${currentPath.endsWith("\\") ? "" : "\\"}${newFolderName || "[Tên dự án mới]"}`
                : selectedFolder || currentPath}
            </div>
          </div>

          {/* Action Buttons based on mode */}
          <div className="flex items-center gap-2.5 shrink-0">
            {mode === "create" ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  placeholder="Nhập tên dự án (e.g. MyShopeeTool)..."
                  className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500 w-52"
                  onKeyDown={(e) => e.key === "Enter" && handleConfirmCreate()}
                />
                <button
                  onClick={handleConfirmCreate}
                  disabled={isSubmitting || !newFolderName.trim()}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg font-semibold flex items-center gap-1.5 shadow transition"
                >
                  <FolderPlus size={14} /> Tạo & Mở Dự Án
                </button>
              </div>
            ) : (
              <button
                onClick={handleConfirmOpen}
                disabled={isSubmitting}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg font-semibold flex items-center gap-1.5 shadow transition"
              >
                <FolderOpen size={14} /> Mở Thư Mục Này
              </button>
            )}

            <button
              onClick={onClose}
              className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 rounded-lg font-medium transition"
            >
              Hủy
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
