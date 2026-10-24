import { useState, useEffect } from "react";
import {
  Search,
  MessageSquare,
  Plus,
  RefreshCw,
  FilePlus,
  FolderPlus,
  Files,
  MessagesSquare,
  Trash2,
  Edit3,
  Filter,
  Database,
  CheckSquare
} from "lucide-react";
import { api } from "./services/api";
import type {
  FileItem,
  ChatMessage,
  ChatAttachment,
  SystemInfo,
  HealthInfo,
  TaskSpecification
} from "./services/api";
import { TopBar } from "./components/TopBar";
import { FileTree } from "./components/FileTree";
import { ChatView } from "./components/ChatView";
import { FileViewer } from "./components/FileViewer";
import { TaskIntelligenceModal } from "./components/TaskIntelligenceModal";
import { OrchestratorDomainCenter } from "./components/OrchestratorDomainCenter";
import { CustomizationsModal } from "./components/CustomizationsModal";
import { FolderPickerModal } from "./components/FolderPickerModal";
import {
  alertError,
  confirmDialog,
  promptDialog,
  toastSuccess,
  toastError
} from "./utils/alerts";

export function App() {
  const [workspacePath, setWorkspacePath] = useState("H:\\AiLocal");
  const [workspaceId, setWorkspaceId] = useState<string>("");
  const [recentWorkspaces, setRecentWorkspaces] = useState<any[]>([]);
  const [fileTree, setFileTree] = useState<FileItem[]>([]);
  const [conversations, setConversations] = useState<any[]>([]);
  const [activeConvId, setActiveConvId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedFile, setSelectedFile] = useState<{ path: string; content: string; size: number } | null>(null);
  const [activeTaskSpec, setActiveTaskSpec] = useState<TaskSpecification | null>(null);

  // Modals state
  const [isOrchestratorCenterOpen, setIsOrchestratorCenterOpen] = useState(false);
  const [isCustomizationsOpen, setIsCustomizationsOpen] = useState(false);
  const [isFolderPickerOpen, setIsFolderPickerOpen] = useState(false);
  const [folderPickerMode, setFolderPickerMode] = useState<"open" | "create">("open");

  // Sidebar Tab: "files" | "chats"
  const [sidebarTab, setSidebarTab] = useState<"files" | "chats">("files");

  const [systemInfo, setSystemInfo] = useState<SystemInfo>();
  const [healthInfo, setHealthInfo] = useState<HealthInfo>();
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);

  // 1. Initial Load
  useEffect(() => {
    initApp();
  }, []);

  const initApp = async () => {
    try {
      const [h, s] = await Promise.all([api.getHealth(), api.getSystemInfo()]);
      setHealthInfo(h);
      setSystemInfo(s);

      await loadRecentWorkspaces();
      await loadWorkspace(workspacePath);
    } catch (err) {
      console.error("Initialization error:", err);
    }
  };

  const loadRecentWorkspaces = async () => {
    try {
      const res = await api.listWorkspaces();
      setRecentWorkspaces(res.workspaces || []);
    } catch (err) {
      console.error("Failed to load recent workspaces:", err);
    }
  };

  const loadWorkspace = async (path: string) => {
    try {
      const ws = await api.openWorkspace(path);
      setWorkspaceId(ws.workspace.id);
      setWorkspacePath(ws.workspace.path);

      // Load file tree
      const treeRes = await api.getTree(ws.workspace.path);
      setFileTree(treeRes.tree);

      // Load conversations
      const convRes = await api.getConversations(ws.workspace.id);
      setConversations(convRes.conversations);

      if (convRes.conversations.length > 0) {
        selectConversation(convRes.conversations[0].id);
      } else {
        await startNewChat(ws.workspace.id);
      }
      await loadRecentWorkspaces();
    } catch (err: any) {
      alertError("Không thể mở workspace", err.message || "Đường dẫn không hợp lệ hoặc bị từ chối truy cập");
    }
  };

  const handleSelectWorkspace = async (path: string) => {
    setSelectedFile(null);
    await loadWorkspace(path);
  };

  const handleOpenOtherFolder = () => {
    setFolderPickerMode("open");
    setIsFolderPickerOpen(true);
  };

  const handleCreateProject = () => {
    setFolderPickerMode("create");
    setIsFolderPickerOpen(true);
  };

  // --- File CRUD Handlers with SweetAlert2 ---
  const handleCreateFile = async () => {
    const relPath = await promptDialog({
      title: "Tạo Tệp Mới (New File)",
      text: "Nhập đường dẫn tệp tương đối trong workspace (ví dụ: src/utils.py):",
      inputPlaceholder: "src/new_module.py",
      required: true,
    });
    if (!relPath) return;

    try {
      await api.createFile(workspacePath, relPath);
      const treeRes = await api.getTree(workspacePath);
      setFileTree(treeRes.tree);
      await handleSelectFile(relPath);
      toastSuccess(`Đã tạo tệp: ${relPath}`);
    } catch (err: any) {
      alertError("Lỗi tạo tệp", err.message);
    }
  };

  const handleCreateFolder = async () => {
    const relPath = await promptDialog({
      title: "Tạo Thư Mục Mới (New Folder)",
      text: "Nhập đường dẫn thư mục tương đối trong workspace (ví dụ: src/components):",
      inputPlaceholder: "src/components",
      required: true,
    });
    if (!relPath) return;

    try {
      await api.createDirectory(workspacePath, relPath);
      const treeRes = await api.getTree(workspacePath);
      setFileTree(treeRes.tree);
      toastSuccess(`Đã tạo thư mục: ${relPath}`);
    } catch (err: any) {
      alertError("Lỗi tạo thư mục", err.message);
    }
  };

  const handleRenameItem = async (oldPath: string) => {
    const newPath = await promptDialog({
      title: "Đổi Tên (Rename)",
      text: `Nhập tên mới cho '${oldPath}':`,
      inputValue: oldPath,
      required: true,
    });
    if (!newPath || newPath === oldPath) return;

    try {
      await api.renameItem(workspacePath, oldPath, newPath);
      const treeRes = await api.getTree(workspacePath);
      setFileTree(treeRes.tree);
      if (selectedFile?.path === oldPath) {
        await handleSelectFile(newPath);
      }
      toastSuccess(`Đã đổi tên thành: ${newPath}`);
    } catch (err: any) {
      alertError("Lỗi đổi tên", err.message);
    }
  };

  const handleDeleteItem = async (relPath: string) => {
    const confirmed = await confirmDialog({
      title: "Xác nhận xóa tệp / thư mục",
      text: `Bạn có chắc chắn muốn xóa '${relPath}' không? Hệ thống sẽ tự động tạo Checkpoint trước khi xóa để bạn có thể rollback phục hồi bất kỳ lúc nào.`,
      confirmText: "Xóa Ngay",
      cancelText: "Hủy bỏ",
      isDestructive: true,
    });
    if (!confirmed) return;

    try {
      await api.deleteFile(workspaceId, workspacePath, relPath);
      const treeRes = await api.getTree(workspacePath);
      setFileTree(treeRes.tree);
      if (selectedFile?.path === relPath) {
        setSelectedFile(null);
      }
      toastSuccess(`Đã xóa: ${relPath}`);
    } catch (err: any) {
      alertError("Lỗi xóa tệp", err.message);
    }
  };

  const handleSaveFile = async (filePath: string, newContent: string) => {
    if (!workspaceId) return;
    try {
      await api.updateFile(workspaceId, workspacePath, filePath, newContent);
      setSelectedFile({
        path: filePath,
        content: newContent,
        size: newContent.length,
      });
      const treeRes = await api.getTree(workspacePath);
      setFileTree(treeRes.tree);
      toastSuccess("Đã lưu thay đổi & tạo Checkpoint an toàn");
    } catch (err: any) {
      alertError("Lỗi lưu tệp", err.message);
    }
  };

  const [convSearch, setConvSearch] = useState("");
  const [isBatchSelectMode, setIsBatchSelectMode] = useState(false);
  const [selectedConvIds, setSelectedConvIds] = useState<Set<string>>(new Set());

  const startNewChat = async (wsId?: string) => {
    const targetWsId = wsId || workspaceId;
    if (!targetWsId) return;
    try {
      const res = await api.createConversation(targetWsId, `Chat #${conversations.length + 1}`);
      const newConv = res.conversation;
      setConversations([newConv, ...conversations]);
      setActiveConvId(newConv.id);
      setMessages([]);
      toastSuccess(`Đã tạo phiên chat mới: ${newConv.title}`);
    } catch (err: any) {
      alertError("Lỗi tạo cuộc trò chuyện", err.message);
    }
  };

  const handleRenameConversation = async (convId: string, currentTitle: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    const newTitle = await promptDialog({
      title: "Đổi Tên Phiên Trò Chuyện",
      text: "Nhập tiêu đề mới cho phiên chat:",
      inputValue: currentTitle,
      inputPlaceholder: "Ví dụ: Tối ưu kiến trúc backend...",
      required: true,
    });
    if (!newTitle || newTitle.trim() === currentTitle) return;

    try {
      await api.updateConversation(convId, newTitle.trim());
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, title: newTitle.trim() } : c))
      );
      toastSuccess(`Đã đổi tên thành: ${newTitle.trim()}`);
    } catch (err: any) {
      alertError("Lỗi đổi tên chat", err.message);
    }
  };

  const handleDeleteConversation = async (convId: string, title: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    const confirmed = await confirmDialog({
      title: "Xóa Phiên Trò Chuyện",
      text: `Bạn có chắc chắn muốn xóa phiên chat '${title}' không? Toàn bộ tin nhắn sẽ bị xóa vĩnh viễn.`,
      confirmText: "Xóa Ngay",
      cancelText: "Hủy bỏ",
      isDestructive: true,
    });
    if (!confirmed) return;

    try {
      await api.deleteConversation(convId);
      const remaining = conversations.filter((c) => c.id !== convId);
      setConversations(remaining);
      if (activeConvId === convId) {
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          await startNewChat();
        }
      }
      toastSuccess("Đã xóa phiên chat thành công");
    } catch (err: any) {
      alertError("Lỗi xóa chat", err.message);
    }
  };

  const handleClearAllConversations = async () => {
    if (!workspaceId || conversations.length === 0) return;
    const confirmed = await confirmDialog({
      title: "Xóa Toàn Bộ Lịch Sử Chat",
      text: "Bạn có chắc chắn muốn xóa TOÀN BỘ các phiên trò chuyện trong workspace này không? Hành động này không thể hoàn tác.",
      confirmText: "Xóa Tất Cả",
      cancelText: "Hủy bỏ",
      isDestructive: true,
    });
    if (!confirmed) return;

    try {
      await api.clearWorkspaceConversations(workspaceId);
      setConversations([]);
      setMessages([]);
      await startNewChat();
      toastSuccess("Đã xóa toàn bộ lịch sử chat");
    } catch (err: any) {
      alertError("Lỗi xóa toàn bộ chat", err.message);
    }
  };

  const toggleSelectConversation = (convId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setSelectedConvIds((prev) => {
      const next = new Set(prev);
      if (next.has(convId)) {
        next.delete(convId);
      } else {
        next.add(convId);
      }
      return next;
    });
  };

  const handleSelectAllConversations = () => {
    if (selectedConvIds.size === conversations.length) {
      setSelectedConvIds(new Set());
    } else {
      setSelectedConvIds(new Set(conversations.map((c) => c.id)));
    }
  };

  const handleBatchDeleteConversations = async () => {
    if (selectedConvIds.size === 0) return;
    const count = selectedConvIds.size;
    const confirmed = await confirmDialog({
      title: "Xác nhận xóa hàng loạt",
      text: `Bạn có chắc chắn muốn xóa ${count} cuộc trò chuyện đã chọn không? Toàn bộ tin nhắn liên quan sẽ bị xóa vĩnh viễn.`,
      confirmText: `Xóa ${count} Phiên Chat`,
      cancelText: "Hủy bỏ",
      isDestructive: true,
    });
    if (!confirmed) return;

    try {
      const idsToDelete = Array.from(selectedConvIds);
      await api.batchDeleteConversations(idsToDelete);
      const remaining = conversations.filter((c) => !selectedConvIds.has(c.id));
      setConversations(remaining);
      setSelectedConvIds(new Set());
      setIsBatchSelectMode(false);
      if (selectedConvIds.has(activeConvId)) {
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          await startNewChat();
        }
      }
      toastSuccess(`Đã xóa thành công ${count} cuộc trò chuyện`);
    } catch (err: any) {
      alertError("Lỗi xóa hàng loạt", err.message);
    }
  };

  const handleReindexWorkspace = async () => {
    if (!workspaceId) return;
    try {
      await api.reindexWorkspace(workspaceId, workspacePath);
      toastSuccess("Đã đồng bộ chỉ mục SQLite FTS5 thành công!");
    } catch (err: any) {
      alertError("Lỗi đồng bộ chỉ mục", err.message);
    }
  };

  const selectConversation = async (convId: string) => {
    setActiveConvId(convId);
    try {
      const res = await api.getMessages(convId);
      setMessages(res.messages);
    } catch (err: any) {
      toastError("Không thể tải tin nhắn");
    }
  };

  const handleSendMessage = async (content: string, attachments?: ChatAttachment[]) => {
    if (!activeConvId || (!content.trim() && (!attachments || attachments.length === 0))) return;
    setIsChatLoading(true);

    const tempUserMsg: ChatMessage = {
      id: "temp-user-" + Date.now(),
      role: "user",
      content: content.trim() || (attachments?.length ? `[Đã gửi ${attachments.length} tệp đính kèm để phân tích]` : ""),
      attachments: attachments || [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      await api.sendMessage(activeConvId, content, undefined, attachments);
      const res = await api.getMessages(activeConvId);
      setMessages(res.messages);
    } catch (err: any) {
      alertError("Lỗi sinh phản hồi AI", err.message || "Mô hình Ollama Qwen3 4B đang bận hoặc ngoại tuyến");
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleSelectFile = async (relPath: string) => {
    try {
      const normalizedPath = relPath.replace(/\\/g, "/");
      const res = await api.readFile(workspacePath, normalizedPath);
      const fileData = res.file || res;
      setSelectedFile({
        path: normalizedPath,
        content: typeof fileData.content === "string" ? fileData.content : "",
        size: typeof fileData.size === "number" ? fileData.size : (fileData.content?.length || 0),
      });
    } catch (err: any) {
      toastError(`Không thể đọc tệp: ${relPath}`);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || !workspaceId) return;
    try {
      const res = await api.searchWorkspace(workspaceId, searchQuery);
      setSearchResults(res.matches || []);
    } catch (err) {
      console.error("Search failed:", err);
    }
  };

  const handleOpenRequirementGate = async () => {
    const prompt = await promptDialog({
      title: "Requirement Intelligence Gate",
      text: "Nhập mục tiêu / yêu cầu nhiệm vụ cần phân tích 5 bước & xác minh bằng chứng:",
      inputPlaceholder: "Ví dụ: Tạo module xác thực bảo mật với JWT và bcrypt...",
      required: true,
    });
    if (!prompt || !workspaceId) return;

    try {
      const res = await api.analyzeRequirement(workspaceId, workspacePath, prompt);
      setActiveTaskSpec(res.task_spec);
      toastSuccess("Đã phân tích yêu cầu thành công");
    } catch (err: any) {
      alertError("Lỗi phân tích yêu cầu", err.message);
    }
  };

  const handleClarify = async (taskId: string, questionId: string, option: string) => {
    try {
      const res = await api.clarifyRequirement(taskId, questionId, option);
      setActiveTaskSpec(res.task_spec);
      toastSuccess("Đã gửi câu trả lời làm rõ");
    } catch (err: any) {
      alertError("Lỗi gửi câu trả lời", err.message);
    }
  };

  const handleApprove = async (taskId: string, approved: boolean) => {
    try {
      const res = await api.approveRequirement(taskId, approved);
      setActiveTaskSpec(res.task_spec);
      toastSuccess(approved ? "Đã phê duyệt tác vụ" : "Đã từ chối tác vụ");
    } catch (err: any) {
      alertError("Lỗi cập nhật phê duyệt", err.message);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-zinc-950 font-sans select-none overflow-hidden text-zinc-100">
      {/* Top Header */}
      <TopBar
        workspacePath={workspacePath}
        systemInfo={systemInfo}
        healthInfo={healthInfo}
        recentWorkspaces={recentWorkspaces}
        onSelectWorkspace={handleSelectWorkspace}
        onOpenOtherFolder={handleOpenOtherFolder}
        onCreateProject={handleCreateProject}
        onOpenRequirementGate={handleOpenRequirementGate}
        onOpenOrchestratorCenter={() => setIsOrchestratorCenterOpen(true)}
        onOpenCustomizations={() => setIsCustomizationsOpen(true)}
      />

      {/* Main Content Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Activity Sidebar */}
        <aside className="w-80 bg-zinc-950/80 border-r border-zinc-800/80 flex flex-col h-full shrink-0">
          {/* Sidebar Tab Header */}
          <div className="p-2 border-b border-zinc-800/80 flex items-center gap-1.5 bg-zinc-900/40 select-none">
            <button
              onClick={() => setSidebarTab("files")}
              className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition whitespace-nowrap ${
                sidebarTab === "files"
                  ? "bg-zinc-800 text-white shadow-sm border border-zinc-700/60"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850"
              }`}
            >
              <Files size={13} className={sidebarTab === "files" ? "text-indigo-400" : ""} />
              <span>Explorer</span>
            </button>
            <button
              onClick={() => setSidebarTab("chats")}
              className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition whitespace-nowrap ${
                sidebarTab === "chats"
                  ? "bg-zinc-800 text-white shadow-sm border border-zinc-700/60"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850"
              }`}
            >
              <MessagesSquare size={13} className={sidebarTab === "chats" ? "text-emerald-400" : ""} />
              <span>Chats</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-zinc-900 text-zinc-400 border border-zinc-800 font-mono">
                {conversations.length}
              </span>
            </button>
          </div>

          {/* Tab 1: Files Explorer */}
          {sidebarTab === "files" && (
            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
              {/* FTS5 Search Input */}
              <div className="p-2.5 border-b border-zinc-800/80 bg-zinc-900/20">
                <form onSubmit={handleSearch} className="relative">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Tìm kiếm FTS5 trong dự án..."
                    className="w-full bg-zinc-900/90 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 pl-8 transition"
                  />
                  <Search size={13} className="absolute left-2.5 top-2.5 text-zinc-500" />
                </form>
              </div>

              {/* Search Results list if active */}
              {searchResults.length > 0 && (
                <div className="p-2 border-b border-zinc-800 bg-zinc-900/95 max-h-48 overflow-y-auto space-y-1">
                  <div className="flex justify-between items-center text-[10px] text-zinc-400 px-1 font-semibold">
                    <span>KẾT QUẢ FTS5 ({searchResults.length})</span>
                    <button onClick={() => setSearchResults([])} className="hover:text-zinc-200 text-zinc-500">
                      Đóng
                    </button>
                  </div>
                  {searchResults.map((m, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleSelectFile(m.file_path)}
                      className="p-1.5 rounded-lg hover:bg-zinc-800 cursor-pointer text-xs transition"
                    >
                      <div className="text-indigo-400 font-semibold truncate">{m.file_name}</div>
                      <div
                        className="text-[11px] text-zinc-400 line-clamp-2 mt-0.5"
                        dangerouslySetInnerHTML={{ __html: m.snippet }}
                      />
                    </div>
                  ))}
                </div>
              )}

              {/* Workspace Tree Header with CRUD Buttons */}
              <div className="px-3 py-2 flex items-center justify-between text-[11px] font-bold text-zinc-400 uppercase tracking-wider border-b border-zinc-800/40 bg-zinc-950/40">
                <span>FILES</span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleCreateFile}
                    className="p-1 hover:bg-zinc-800 rounded-md text-zinc-400 hover:text-indigo-300 transition"
                    title="Tạo tệp mới"
                  >
                    <FilePlus size={13} />
                  </button>
                  <button
                    onClick={handleCreateFolder}
                    className="p-1 hover:bg-zinc-800 rounded-md text-zinc-400 hover:text-amber-300 transition"
                    title="Tạo thư mục mới"
                  >
                    <FolderPlus size={13} />
                  </button>
                  <button
                    onClick={handleReindexWorkspace}
                    className="p-1 hover:bg-zinc-800 rounded-md text-zinc-500 hover:text-emerald-400 transition"
                    title="Tái lập & Đồng bộ chỉ mục FTS5"
                  >
                    <Database size={12} />
                  </button>
                  <button
                    onClick={() => loadWorkspace(workspacePath)}
                    className="p-1 hover:bg-zinc-800 rounded-md text-zinc-500 hover:text-zinc-300 transition"
                    title="Làm mới cây thư mục"
                  >
                    <RefreshCw size={12} />
                  </button>
                </div>
              </div>

              {/* Tree View Scrollable */}
              <div className="flex-1 overflow-y-auto px-1.5 py-1">
                <FileTree
                  items={fileTree}
                  onSelectFile={handleSelectFile}
                  onRename={handleRenameItem}
                  onDelete={handleDeleteItem}
                  selectedPath={selectedFile?.path}
                />
              </div>
            </div>
          )}

          {/* Tab 2: Conversations */}
          {sidebarTab === "chats" && (
            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
              {/* Header Row 1: Section Title & Batch Mode / Clear All */}
              <div className="px-3 py-2.5 border-b border-zinc-800/80 bg-zinc-900/30 flex items-center justify-between gap-2 shrink-0">
                <span className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5 whitespace-nowrap">
                  <MessagesSquare size={13} className="text-indigo-400 shrink-0" />
                  <span>Cuộc trò chuyện</span>
                  <span className="text-[10px] text-zinc-400 bg-zinc-800/90 px-1.5 py-0.5 rounded-full border border-zinc-700/60 font-mono">
                    {conversations.length}
                  </span>
                </span>
                
                <div className="flex items-center gap-1 shrink-0">
                  {conversations.length > 0 && (
                    <>
                      <button
                        onClick={() => {
                          setIsBatchSelectMode(!isBatchSelectMode);
                          setSelectedConvIds(new Set());
                        }}
                        className={`p-1.5 rounded-lg border text-xs flex items-center gap-1 transition ${
                          isBatchSelectMode
                            ? "bg-indigo-600/30 text-indigo-300 border-indigo-500/50"
                            : "hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border-transparent"
                        }`}
                        title={isBatchSelectMode ? "Hủy chế độ chọn hàng loạt" : "Chọn nhiều để xóa hàng loạt"}
                      >
                        <CheckSquare size={13} />
                      </button>
                      <button
                        onClick={handleClearAllConversations}
                        className="p-1.5 hover:bg-rose-950/40 text-zinc-500 hover:text-rose-400 rounded-lg border border-transparent hover:border-rose-900/40 transition"
                        title="Xóa toàn bộ các phiên trò chuyện"
                      >
                        <Trash2 size={13} />
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Header Row 2: Full-width New Chat Button */}
              <div className="px-3 pt-2.5 pb-1 shrink-0">
                <button
                  onClick={() => startNewChat()}
                  className="w-full py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 shadow-sm transition whitespace-nowrap shrink-0 group active:scale-[0.99]"
                  title="Bắt đầu phiên chat mới"
                >
                  <Plus size={14} className="group-hover:rotate-90 transition-transform duration-200 shrink-0" />
                  <span className="whitespace-nowrap">Tạo Cuộc Trò Chuyện Mới</span>
                </button>
              </div>

              {/* Batch Action Toolbar */}
              {isBatchSelectMode && (
                <div className="mx-3 my-2 p-2 bg-indigo-950/40 border border-indigo-500/30 rounded-xl flex items-center justify-between text-xs animate-in fade-in duration-150 shrink-0">
                  <div className="flex items-center gap-2 min-w-0">
                    <button
                      onClick={handleSelectAllConversations}
                      className="text-[11px] font-medium text-indigo-300 hover:text-indigo-200 hover:underline whitespace-nowrap"
                    >
                      {selectedConvIds.size === conversations.length ? "Bỏ chọn" : "Chọn tất cả"}
                    </button>
                    <span className="text-[10px] text-zinc-400 whitespace-nowrap">
                      ({selectedConvIds.size}/{conversations.length})
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      disabled={selectedConvIds.size === 0}
                      onClick={handleBatchDeleteConversations}
                      className="px-2 py-1 bg-rose-600 hover:bg-rose-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white rounded-lg text-[11px] font-medium transition flex items-center gap-1 whitespace-nowrap shadow-sm disabled:cursor-not-allowed"
                      title="Xóa các phiên chat đã chọn"
                    >
                      <Trash2 size={11} />
                      <span>Xóa ({selectedConvIds.size})</span>
                    </button>
                    <button
                      onClick={() => {
                        setIsBatchSelectMode(false);
                        setSelectedConvIds(new Set());
                      }}
                      className="p-1 text-zinc-400 hover:text-zinc-200 rounded"
                      title="Thoát chế độ chọn"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              )}

              {/* Real-time search filter */}
              {conversations.length > 2 && (
                <div className="px-3 pt-1 pb-1 shrink-0">
                  <div className="flex items-center gap-2 px-2.5 py-1.5 bg-zinc-900/80 border border-zinc-800 rounded-xl text-xs">
                    <Filter size={12} className="text-zinc-500 shrink-0" />
                    <input
                      type="text"
                      value={convSearch}
                      onChange={(e) => setConvSearch(e.target.value)}
                      placeholder="Tìm kiếm phiên chat..."
                      className="bg-transparent border-none focus:outline-none text-zinc-200 text-xs w-full placeholder:text-zinc-600"
                    />
                    {convSearch && (
                      <button
                        onClick={() => setConvSearch("")}
                        className="text-[10px] text-zinc-500 hover:text-zinc-300"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Conversation items list */}
              <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {conversations
                  .filter((c) =>
                    c.title.toLowerCase().includes(convSearch.toLowerCase())
                  )
                  .map((c) => {
                    const isActive = activeConvId === c.id;
                    const isSelected = selectedConvIds.has(c.id);

                    return (
                      <div
                        key={c.id}
                        onClick={(e) => {
                          if (isBatchSelectMode) {
                            toggleSelectConversation(c.id, e);
                          } else {
                            selectConversation(c.id);
                          }
                        }}
                        className={`group relative w-full text-left px-3 py-2.5 rounded-xl text-xs flex items-center justify-between gap-2 transition-all cursor-pointer select-none ${
                          isSelected
                            ? "bg-indigo-950/50 border border-indigo-500/50 text-indigo-200 font-medium shadow-sm"
                            : isActive
                            ? "bg-zinc-850 text-indigo-300 font-semibold border border-zinc-700/80 shadow-sm"
                            : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 border border-transparent"
                        }`}
                      >
                        {/* Checkbox (Batch mode) or Chat Icon */}
                        <div className="flex items-center gap-2.5 min-w-0 flex-1">
                          {isBatchSelectMode ? (
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => toggleSelectConversation(c.id, e as any)}
                              onClick={(e) => e.stopPropagation()}
                              className="rounded border-zinc-700 text-indigo-600 focus:ring-0 focus:ring-offset-0 bg-zinc-900 h-3.5 w-3.5 shrink-0 cursor-pointer accent-indigo-600"
                            />
                          ) : (
                            <MessageSquare
                              size={14}
                              className={isActive ? "text-indigo-400 shrink-0" : "text-zinc-500 shrink-0"}
                            />
                          )}
                          <span className="truncate flex-1" title={c.title}>
                            {c.title}
                          </span>
                        </div>

                        {/* Inline Actions: Rename & Delete (Single mode only) */}
                        {!isBatchSelectMode && (
                          <div className="hidden group-hover:flex items-center gap-1 shrink-0 animate-in fade-in duration-100">
                            <button
                              onClick={(e) => handleRenameConversation(c.id, c.title, e)}
                              className="p-1 hover:bg-zinc-800 text-zinc-400 hover:text-amber-300 rounded transition"
                              title="Đổi tên cuộc trò chuyện"
                            >
                              <Edit3 size={11} />
                            </button>
                            <button
                              onClick={(e) => handleDeleteConversation(c.id, c.title, e)}
                              className="p-1 hover:bg-rose-950/60 text-zinc-400 hover:text-rose-400 rounded transition"
                              title="Xóa cuộc trò chuyện này"
                            >
                              <Trash2 size={11} />
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                {conversations.filter((c) =>
                  c.title.toLowerCase().includes(convSearch.toLowerCase())
                ).length === 0 && (
                  <div className="text-center py-6 text-xs text-zinc-600">
                    Không tìm thấy cuộc trò chuyện phù hợp
                  </div>
                )}
              </div>
            </div>
          )}
        </aside>

        {/* Center Panel (Chat View) */}
        <main className="flex-1 flex overflow-hidden">
          <ChatView
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isChatLoading}
            onSelectEvidenceFile={handleSelectFile}
            workspaceId={workspaceId}
          />

          {/* Right Panel: File Viewer & In-Place Code Editor */}
          {selectedFile && (
            <FileViewer
              filePath={selectedFile.path}
              content={selectedFile.content}
              size={selectedFile.size}
              onClose={() => setSelectedFile(null)}
              onSave={handleSaveFile}
            />
          )}
        </main>
      </div>

      {/* Visual Folder Picker / Project Explorer Modal */}
      {isFolderPickerOpen && (
        <FolderPickerModal
          initialPath={workspacePath}
          defaultMode={folderPickerMode}
          onClose={() => setIsFolderPickerOpen(false)}
          onSelectFolder={handleSelectWorkspace}
        />
      )}

      {/* Task Intelligence Modal */}
      {activeTaskSpec && (
        <TaskIntelligenceModal
          taskSpec={activeTaskSpec}
          onClose={() => setActiveTaskSpec(null)}
          onClarify={handleClarify}
          onApprove={handleApprove}
        />
      )}

      {/* Orchestrator & Domain Center Modal */}
      {isOrchestratorCenterOpen && (
        <OrchestratorDomainCenter
          workspaceId={workspaceId}
          workspacePath={workspacePath}
          onClose={() => setIsOrchestratorCenterOpen(false)}
        />
      )}

      {/* Antigravity Customizations (Skills & MCP) Modal */}
      {isCustomizationsOpen && (
        <CustomizationsModal
          workspaceId={workspaceId}
          onClose={() => setIsCustomizationsOpen(false)}
        />
      )}
    </div>
  );
}

export default App;
