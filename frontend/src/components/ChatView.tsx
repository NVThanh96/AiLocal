import React, { useState, useRef, useEffect } from "react";
import {
  Bot,
  User,
  FileCode,
  CheckCircle2,
  Loader2,
  Sparkles,
  ShieldCheck,
  CornerDownLeft,
  Terminal,
  Paperclip,
  Image as ImageIcon,
  Video as VideoIcon,
  FileText,
  Music,
  X,
  Eye,
  ChevronDown,
  ChevronUp,
  UploadCloud,
  Film,
  File,
  Copy,
  Check,
  Download
} from "lucide-react";
import { api } from "../services/api";
import type { ChatMessage, ChatAttachment } from "../services/api";
import { toastSuccess, toastError } from "../utils/alerts";
import { MarkdownMessage } from "./MarkdownMessage";

interface ChatViewProps {
  messages: ChatMessage[];
  onSendMessage: (content: string, attachments?: ChatAttachment[]) => Promise<void>;
  isLoading: boolean;
  onSelectEvidenceFile?: (path: string) => void;
  workspaceId?: string;
}

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  onSendMessage,
  isLoading,
  onSelectEvidenceFile,
  workspaceId,
}) => {
  const [input, setInput] = useState("");
  const [stagedAttachments, setStagedAttachments] = useState<ChatAttachment[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [expandedDocMap, setExpandedDocMap] = useState<Record<string, boolean>>({});
  const [previewModalImg, setPreviewModalImg] = useState<{ url: string; name: string } | null>(null);
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);

  const endRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, stagedAttachments]);

  const handleCopyMessage = async (msgId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMsgId(msgId);
      toastSuccess("Đã sao chép nội dung tin nhắn!");
      setTimeout(() => setCopiedMsgId(null), 2000);
    } catch (e) {
      toastError("Không thể sao chép văn bản");
    }
  };

  const handleExportChat = () => {
    if (messages.length === 0) return;
    let md = `# Lịch Sử Cuộc Trò Chuyện (Antigravity Local AI)\n`;
    md += `*Thời gian xuất: ${new Date().toLocaleString("vi-VN")}*\n\n---\n\n`;

    messages.forEach((m, idx) => {
      const sender = m.role === "user" ? "👤 NGƯỜI DÙNG" : "🤖 TRỢ LÝ ANTIGRAVITY";
      md += `### ${idx + 1}. ${sender} (${new Date(m.created_at).toLocaleTimeString()})\n\n`;
      md += `${m.content}\n\n`;

      if (m.attachments && m.attachments.length > 0) {
        md += `*Tệp đính kèm (${m.attachments.length}):*\n`;
        m.attachments.forEach((a) => {
          md += `- **${a.file_name}** (${a.file_type.toUpperCase()}, ${a.file_size_human})\n`;
        });
        md += `\n`;
      }

      if (m.sources && m.sources.length > 0) {
        md += `*Bằng chứng xác thực (Grounded Sources):*\n`;
        m.sources.forEach((s) => {
          md += `- \`${s.file_path}\`\n`;
        });
        md += `\n`;
      }

      md += `---\n\n`;
    });

    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chat-export-${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toastSuccess("Đã xuất toàn bộ lịch sử trò chuyện sang file .md!");
  };

  const handleUploadFiles = async (files: FileList | File[]) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    const newAttachments: ChatAttachment[] = [];

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        try {
          const res = await api.uploadChatAttachment(file, workspaceId);
          newAttachments.push(res.attachment);
          toastSuccess(`Đã nạp & phân tích: ${file.name}`);
        } catch (err: any) {
          toastError(`Lỗi xử lý ${file.name}: ${err.message}`);
        }
      }
      if (newAttachments.length > 0) {
        setStagedAttachments((prev) => [...prev, ...newAttachments]);
      }
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleUploadFiles(e.target.files);
    }
  };

  const handleRemoveStagedAttachment = (index: number) => {
    setStagedAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    if (e.clipboardData && e.clipboardData.files && e.clipboardData.files.length > 0) {
      e.preventDefault();
      handleUploadFiles(e.clipboardData.files);
    }
  };

  // Safe DragOver handler: ONLY trigger drag overlay when actual OS files are dragged
  const handleDragOver = (e: React.DragEvent) => {
    if (e.dataTransfer && e.dataTransfer.types && Array.from(e.dataTransfer.types).includes("Files")) {
      e.preventDefault();
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    if (e.dataTransfer && e.dataTransfer.types && Array.from(e.dataTransfer.types).includes("Files")) {
      e.preventDefault();
      setIsDragOver(false);
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleUploadFiles(e.dataTransfer.files);
      }
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = input.trim();
    if ((!trimmed && stagedAttachments.length === 0) || isLoading || isUploading) return;
    
    const contentToSend = trimmed;
    const attachmentsToSend = [...stagedAttachments];

    setInput("");
    setStagedAttachments([]);
    onSendMessage(contentToSend, attachmentsToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const toggleDocExpand = (docKey: string) => {
    setExpandedDocMap((prev) => ({ ...prev, [docKey]: !prev[docKey] }));
  };

  const renderFileIcon = (fileType: string) => {
    switch (fileType) {
      case "image":
        return <ImageIcon size={14} className="text-sky-400 shrink-0" />;
      case "video":
        return <VideoIcon size={14} className="text-amber-400 shrink-0" />;
      case "audio":
        return <Music size={14} className="text-emerald-400 shrink-0" />;
      case "document":
        return <FileText size={14} className="text-indigo-400 shrink-0" />;
      default:
        return <File size={14} className="text-zinc-400 shrink-0" />;
    }
  };

  const QUICK_PROMPTS = [
    { label: "🔍 Phân tích cấu trúc module", prompt: "Quét và phân tích toàn bộ cấu trúc module và thư mục dự án" },
    { label: "🛡️ Kiểm toán bảo mật", prompt: "Kiểm toán an toàn mã nguồn, ranh giới sandbox và các tệp cấu hình" },
    { label: "⚡ Tối ưu hiệu năng", prompt: "Đánh giá hiệu năng và đề xuất các điểm tối ưu trong dự án" },
    { label: "🧪 Viết test tự động", prompt: "Tạo các kịch bản kiểm thử tự động pytest để bảo vệ tính toàn vẹn hệ thống" }
  ];

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="flex-1 flex flex-col h-full bg-zinc-950 text-zinc-100 overflow-hidden relative"
    >
      {/* Hidden native file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        multiple
        className="hidden"
        accept="image/*,video/*,audio/*,.pdf,.txt,.md,.json,.csv,.tsv,.py,.ts,.js,.tsx,.jsx,.html,.css,.yaml,.yml,.sql,.log,.docx"
      />

      {/* Header Utilities Toolbar */}
      {messages.length > 0 && (
        <div className="px-4 py-2 border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur flex items-center justify-between text-xs shrink-0 select-none">
          <div className="flex items-center gap-2 text-zinc-400">
            <span className="flex items-center gap-1.5 font-medium text-zinc-300">
              <Bot size={13} className="text-indigo-400" />
              <span>Hội thoại ({messages.length} tin nhắn)</span>
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={handleExportChat}
              className="flex items-center gap-1 px-2.5 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded-lg border border-zinc-800 hover:border-zinc-700 transition text-[11px] shadow-sm font-medium"
              title="Xuất toàn bộ nội dung trò chuyện ra tệp Markdown (.md)"
            >
              <Download size={12} className="text-indigo-400" />
              <span>Xuất hội thoại (.md)</span>
            </button>
          </div>
        </div>
      )}

      {/* Drag & Drop Visual Overlay (Active only when actual files are dragged) */}
      {isDragOver && (
        <div className="absolute inset-0 z-50 bg-indigo-950/80 backdrop-blur-sm border-2 border-dashed border-indigo-400 flex flex-col items-center justify-center pointer-events-none animate-in fade-in duration-150">
          <UploadCloud size={48} className="text-indigo-300 animate-bounce mb-3" />
          <h3 className="text-base font-bold text-white">Thả tệp vào đây để tải lên</h3>
          <p className="text-xs text-indigo-200 mt-1">Hỗ trợ Hình ảnh, Video, Tài liệu PDF, Bảng tính CSV và Mã nguồn</p>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-zinc-500 max-w-lg mx-auto select-none">
            <div className="w-14 h-14 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center mb-4 text-indigo-400 shadow-inner">
              <Sparkles size={28} />
            </div>
            <h3 className="text-base font-bold text-zinc-200">
              Antigravity Local Coding & Multimodal Assistant
            </h3>
            <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
              Trợ lý lập trình AI cục bộ (Qwen3 4B) chạy 100% trên GPU NVIDIA RTX 2070.
              Hỗ trợ phân tích toàn diện <strong>Hình ảnh, Video, Tài liệu PDF/Code</strong> bằng chứng thực tế, không suy đoán mù quáng.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-6 w-full text-left">
              {QUICK_PROMPTS.slice(0, 2).map((qp, i) => (
                <button
                  key={i}
                  onClick={() => onSendMessage(qp.prompt)}
                  className="p-3 bg-zinc-900/80 hover:bg-zinc-800/80 border border-zinc-800 hover:border-zinc-700 rounded-xl text-xs text-zinc-300 transition"
                >
                  <div className="font-semibold text-indigo-300">{qp.label}</div>
                  <div className="text-[11px] text-zinc-500 mt-0.5 truncate">{qp.prompt}</div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages
            .filter((m): m is ChatMessage => Boolean(m && typeof m === "object" && typeof m.role === "string"))
            .map((m, idx) => {
              const isUser = m.role === "user";
              const hasAttachments = m.attachments && m.attachments.length > 0;
              const isCopied = copiedMsgId === m.id;

              return (
                <div
                  key={m.id || `msg-${idx}`}
                  className={`flex gap-3 max-w-3xl ${
                    isUser ? "ml-auto flex-row-reverse" : "mr-auto"
                  }`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-xs shadow-sm select-none ${
                      isUser
                        ? "bg-indigo-600 text-white"
                        : "bg-zinc-900 border border-zinc-800 text-indigo-400"
                    }`}
                  >
                    {isUser ? <User size={15} /> : <Bot size={16} />}
                  </div>

                  {/* Message Body */}
                  <div className={`space-y-1.5 flex-1 min-w-0 ${isUser ? "text-right" : "text-left"}`}>
                    {/* Header Row: Sender Label & One-Click Copy Button */}
                    <div className={`flex items-center gap-2 text-[11px] text-zinc-500 px-1 select-none ${isUser ? "justify-end" : "justify-between"}`}>
                      {!isUser ? (
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-zinc-300">Antigravity Agent</span>
                          <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400">
                            Local RTX 2070
                          </span>
                        </div>
                      ) : (
                        <span className="font-medium text-zinc-400">Bạn</span>
                      )}

                      <button
                        onClick={() => handleCopyMessage(m.id, m.content)}
                        className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/80 px-2 py-0.5 rounded transition active:scale-95"
                        title="Sao chép toàn bộ tin nhắn này để dán nơi khác"
                      >
                        {isCopied ? (
                          <>
                            <Check size={11} className="text-emerald-400" />
                            <span className="text-emerald-400 font-medium">Đã chép</span>
                          </>
                        ) : (
                          <>
                            <Copy size={11} />
                            <span>Sao chép</span>
                          </>
                        )}
                      </button>
                    </div>

                    {/* Message Bubble with Full Markdown & Syntax Support */}
                    <div
                      className={`rounded-2xl px-4 py-3.5 text-xs md:text-sm leading-relaxed text-left select-text cursor-text selection:bg-indigo-500/40 selection:text-white ${
                        isUser
                          ? "bg-indigo-950/70 border border-indigo-500/40 text-indigo-100 rounded-tr-sm shadow-md"
                          : "bg-zinc-900/90 border border-zinc-800/90 text-zinc-200 rounded-tl-sm shadow-sm"
                      }`}
                    >
                      <MarkdownMessage content={m.content} isUser={isUser} />
                    </div>

                    {/* Attached Media Cards (Images, Videos, Documents) */}
                    {hasAttachments && (
                      <div className={`flex flex-col gap-2 pt-1 ${isUser ? "items-end" : "items-start"}`}>
                        <div className="text-[10px] text-zinc-500 font-medium flex items-center gap-1 select-none">
                          <Paperclip size={11} className="text-indigo-400" /> Tệp đã đính kèm ({m.attachments!.length}):
                        </div>

                        <div className="flex flex-wrap gap-2 max-w-full">
                          {m.attachments!.map((att, attIdx) => {
                            const docKey = `${m.id}-att-${attIdx}`;
                            const isExpanded = !!expandedDocMap[docKey];

                            return (
                              <div
                                key={attIdx}
                                className="bg-zinc-900 border border-zinc-800 rounded-xl p-2.5 max-w-sm text-left shadow-sm flex flex-col gap-2 transition hover:border-zinc-700"
                              >
                                {/* Header: Icon + Name + Size */}
                                <div className="flex items-center gap-2 min-w-0">
                                  <div className="p-1 rounded-lg bg-zinc-800/80 border border-zinc-700/60 select-none">
                                    {renderFileIcon(att.file_type)}
                                  </div>
                                  <div className="truncate flex-1">
                                    <div className="font-semibold text-xs text-zinc-200 truncate select-text" title={att.file_name}>
                                      {att.file_name}
                                    </div>
                                    <div className="text-[10px] text-zinc-500 flex items-center gap-1.5 select-none">
                                      <span className="uppercase font-mono">{att.extension.replace(".", "") || att.file_type}</span>
                                      <span>•</span>
                                      <span>{att.file_size_human}</span>
                                    </div>
                                  </div>
                                </div>

                                {/* Image Preview Thumbnail */}
                                {att.file_type === "image" && att.preview_url && (
                                  <div
                                    onClick={() => setPreviewModalImg({ url: att.preview_url!, name: att.file_name })}
                                    className="relative group rounded-lg overflow-hidden border border-zinc-800 cursor-pointer max-h-48 bg-zinc-950 flex items-center justify-center select-none"
                                  >
                                    <img
                                      src={att.preview_url}
                                      alt={att.file_name}
                                      className="w-full h-auto object-cover max-h-48 transition group-hover:scale-105 duration-200"
                                    />
                                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white text-xs gap-1">
                                      <Eye size={14} /> Phóng to
                                    </div>
                                  </div>
                                )}

                                {/* Video Metadata & Keyframe Preview */}
                                {att.file_type === "video" && (
                                  <div className="space-y-1.5">
                                    {att.preview_url && (
                                      <div className="relative rounded-lg overflow-hidden border border-zinc-800 max-h-40 bg-zinc-950 select-none">
                                        <img
                                          src={att.preview_url}
                                          alt="Video keyframe"
                                          className="w-full h-auto object-cover max-h-40"
                                        />
                                        <div className="absolute bottom-1.5 right-1.5 bg-black/80 px-1.5 py-0.5 rounded text-[10px] text-zinc-200 font-mono flex items-center gap-1">
                                          <Film size={10} className="text-amber-400" />
                                          {att.metadata?.duration_formatted || "Video"}
                                        </div>
                                      </div>
                                    )}
                                    <div className="text-[10px] text-zinc-400 bg-zinc-950/60 p-2 rounded-lg border border-zinc-800/80 space-y-0.5 font-mono select-text">
                                      <div>Độ phân giải: <span className="text-zinc-200">{att.metadata?.width}x{att.metadata?.height}</span> ({att.metadata?.fps})</div>
                                      <div>Codec: <span className="text-zinc-200">{att.metadata?.video_codec}</span> / Audio: {att.metadata?.audio_codec}</div>
                                      {att.metadata?.platform_compliance && (
                                        <div className="text-indigo-300 font-sans mt-1 text-[10px]">{att.metadata?.platform_compliance}</div>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {/* Document Extracted Content Toggle */}
                                {att.file_type === "document" && att.extracted_text && (
                                  <div className="space-y-1">
                                    <button
                                      onClick={() => toggleDocExpand(docKey)}
                                      className="w-full py-1 px-2 bg-zinc-800/60 hover:bg-zinc-800 text-[11px] text-indigo-300 rounded-lg flex items-center justify-between transition select-none"
                                    >
                                      <span>{isExpanded ? "Thu gọn trích xuất" : "Xem nội dung trích xuất"}</span>
                                      {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                    </button>

                                    {isExpanded && (
                                      <div className="p-2 bg-zinc-950 rounded-lg border border-zinc-800 text-[11px] font-mono text-zinc-300 max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed select-text cursor-text">
                                        {att.extracted_text}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Grounded Evidence Citations */}
                    {m.sources && m.sources.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1 select-none">
                        <div className="w-full text-[10px] text-zinc-500 font-medium flex items-center gap-1">
                          <ShieldCheck size={11} className="text-emerald-400" /> Bằng chứng xác thực (Grounded Sources):
                        </div>
                        {m.sources.map((src, i) => (
                          <button
                            key={i}
                            onClick={() => onSelectEvidenceFile?.(src.file_path)}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-zinc-300 hover:text-indigo-300 text-xs transition shadow-sm"
                            title={src.snippet.replace(/<[^>]+>/g, "")}
                          >
                            <FileCode size={13} className="text-indigo-400 shrink-0" />
                            <span className="truncate max-w-[160px] font-mono text-[11px]">{src.file_name}</span>
                            <CheckCircle2 size={11} className="text-emerald-400 ml-0.5 shrink-0" />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex gap-3 max-w-2xl mr-auto animate-in fade-in duration-200 select-none">
            <div className="w-8 h-8 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-indigo-400 shrink-0 shadow-sm">
              <Bot size={16} />
            </div>
            <div className="bg-zinc-900/90 border border-zinc-800/90 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2.5 text-xs text-zinc-400 shadow-sm">
              <Loader2 size={14} className="animate-spin text-indigo-400" />
              <span>Đang suy luận & đối chiếu bằng chứng bằng Qwen3 4B (RTX 2070)...</span>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Floating Modern Input Box & Quick Prompt Action Chips */}
      <div className="p-4 bg-zinc-950/90 border-t border-zinc-800/80">
        <div className="max-w-4xl mx-auto space-y-2">
          
          {/* Quick Prompt Chips (Suggest common prompts) */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none select-none">
            {QUICK_PROMPTS.map((qp, i) => (
              <button
                key={i}
                onClick={() => setInput(qp.prompt)}
                className="whitespace-nowrap shrink-0 px-2.5 py-1 rounded-full bg-zinc-900/90 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-zinc-400 hover:text-zinc-200 text-[11px] transition shadow-sm font-medium"
              >
                {qp.label}
              </button>
            ))}
          </div>

          <div className="bg-zinc-900/90 border border-zinc-800 hover:border-zinc-700 focus-within:border-indigo-500/80 focus-within:ring-1 focus-within:ring-indigo-500/40 rounded-2xl shadow-xl transition p-2.5">
            {/* Staged Attachments Preview Strip */}
            {stagedAttachments.length > 0 && (
              <div className="flex flex-wrap gap-2 pb-2.5 mb-2 border-b border-zinc-800/80 select-none">
                {stagedAttachments.map((att, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 px-2.5 py-1.5 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-zinc-200 animate-in fade-in duration-100 group shadow-sm"
                  >
                    {att.preview_url && att.file_type === "image" ? (
                      <img
                        src={att.preview_url}
                        alt="Thumb"
                        className="w-5 h-5 rounded object-cover border border-zinc-700"
                      />
                    ) : (
                      renderFileIcon(att.file_type)
                    )}

                    <span className="truncate max-w-[150px] font-medium" title={att.file_name}>
                      {att.file_name}
                    </span>
                    <span className="text-[10px] text-zinc-500">{att.file_size_human}</span>

                    <button
                      onClick={() => handleRemoveStagedAttachment(idx)}
                      className="p-0.5 hover:bg-zinc-800 text-zinc-500 hover:text-rose-400 rounded transition ml-1"
                      title="Xóa tệp đính kèm"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Uploading Status Banner */}
            {isUploading && (
              <div className="flex items-center gap-2 px-3 py-1.5 mb-2 bg-indigo-950/50 border border-indigo-500/30 rounded-xl text-xs text-indigo-300 animate-pulse select-none">
                <Loader2 size={13} className="animate-spin text-indigo-400" />
                <span>Đang tải lên và trích xuất dữ liệu đa phương tiện...</span>
              </div>
            )}

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder="Gửi yêu cầu, hỏi về tệp hoặc kéo thả ảnh/video/tài liệu vào đây (Enter để gửi, Shift+Enter xuống dòng)..."
              disabled={isLoading || isUploading}
              rows={2}
              className="w-full bg-transparent border-0 text-xs md:text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none resize-none px-2 py-1 leading-relaxed select-text"
            />

            <div className="flex items-center justify-between pt-1.5 border-t border-zinc-800/60 px-1 text-[11px] select-none">
              {/* Attachment Actions */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading || isUploading}
                  className="flex items-center gap-1.5 px-2.5 py-1 bg-zinc-800/80 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded-lg border border-zinc-700/60 transition shadow-sm cursor-pointer disabled:opacity-50"
                  title="Đính kèm ảnh, video, tài liệu PDF hoặc code (hoặc kéo thả/Ctrl+V)"
                >
                  <Paperclip size={13} className="text-indigo-400" />
                  <span className="font-medium">Đính kèm tệp</span>
                </button>

                <div className="hidden sm:flex items-center gap-2 text-zinc-500 text-[10px]">
                  <span className="flex items-center gap-1">
                    <Terminal size={11} className="text-zinc-400" />
                    <span>Qwen3 4B • Multimodal Ready</span>
                  </span>
                </div>
              </div>

              {/* Send Button */}
              <button
                onClick={() => handleSubmit()}
                disabled={(!input.trim() && stagedAttachments.length === 0) || isLoading || isUploading}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition shadow-sm cursor-pointer disabled:cursor-not-allowed active:scale-[0.98]"
              >
                <span>Gửi</span>
                <CornerDownLeft size={12} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Image Zoom Modal */}
      {previewModalImg && (
        <div
          onClick={() => setPreviewModalImg(null)}
          className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex flex-col items-center justify-center p-4 cursor-pointer animate-in fade-in duration-150 select-none"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="relative max-w-4xl max-h-[85vh] bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col"
          >
            <div className="p-3 border-b border-zinc-800 flex items-center justify-between bg-zinc-950">
              <span className="text-xs font-semibold text-zinc-200 truncate select-text">{previewModalImg.name}</span>
              <button
                onClick={() => setPreviewModalImg(null)}
                className="p-1 hover:bg-zinc-800 text-zinc-400 hover:text-white rounded-lg transition"
              >
                <X size={15} />
              </button>
            </div>
            <div className="p-2 overflow-auto flex items-center justify-center bg-zinc-950">
              <img
                src={previewModalImg.url}
                alt={previewModalImg.name}
                className="max-w-full max-h-[75vh] object-contain rounded-lg"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
