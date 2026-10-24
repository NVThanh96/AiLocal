import React, { useState, useEffect } from "react";
import { X, FileText, Save, Check, ShieldAlert, Copy } from "lucide-react";
import { alertError, toastSuccess } from "../utils/alerts";

interface FileViewerProps {
  filePath: string;
  content: string;
  size: number;
  onClose: () => void;
  onSave?: (filePath: string, newContent: string) => Promise<void>;
}

export const FileViewer: React.FC<FileViewerProps> = ({ filePath, content, size, onClose, onSave }) => {
  const [editorContent, setEditorContent] = useState(content || "");
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setEditorContent(content || "");
    setSaveSuccess(false);
  }, [filePath, content]);

  const safeSize = typeof size === "number" && !isNaN(size) ? size : (editorContent?.length || 0);
  const isDirty = editorContent !== (content || "");
  const lineCount = (editorContent || "").split("\n").length;

  const handleSave = async () => {
    if (!onSave || !isDirty) return;
    setIsSaving(true);
    try {
      await onSave(filePath, editorContent);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err: any) {
      alertError("Lỗi lưu tệp", err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(editorContent);
      setCopied(true);
      toastSuccess("Đã sao chép nội dung tệp vào clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <div className="w-1/2 border-l border-zinc-800 bg-zinc-950 flex flex-col h-full shadow-2xl z-10">
      {/* File Header */}
      <div className="h-11 border-b border-zinc-800 bg-zinc-900/70 px-3 flex items-center justify-between text-xs select-none">
        <div className="flex items-center gap-2 truncate">
          <FileText size={15} className="text-indigo-400 shrink-0" />
          <span className="font-semibold text-zinc-200 truncate">{filePath}</span>
          <span className="text-[11px] text-zinc-500 font-mono">({(safeSize / 1024).toFixed(1)} KB)</span>
          {isDirty ? (
            <span className="text-[10px] px-1.5 py-0.5 bg-amber-950/80 text-amber-300 border border-amber-800/40 rounded flex items-center gap-1 font-mono">
              <ShieldAlert size={10} /> Chưa lưu
            </span>
          ) : (
            <span className="text-[10px] px-1.5 py-0.5 bg-zinc-800 text-zinc-400 rounded font-mono">
              Đã đồng bộ
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleCopy}
            className="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 transition"
            title="Sao chép nội dung"
          >
            {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
          </button>
          {onSave && isDirty && (
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-[11px] font-medium flex items-center gap-1 transition shadow"
            >
              {saveSuccess ? (
                <>
                  <Check size={12} /> Đã lưu
                </>
              ) : (
                <>
                  <Save size={12} /> {isSaving ? "Đang lưu..." : "Lưu (Checkpoint)"}
                </>
              )}
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      {/* Editable Code Editor */}
      <textarea
        value={editorContent}
        onChange={(e) => setEditorContent(e.target.value)}
        className="flex-1 p-3.5 font-mono text-xs text-zinc-200 bg-zinc-950 resize-none focus:outline-none leading-relaxed selection:bg-indigo-600/30"
        spellCheck={false}
        placeholder="Tệp rỗng..."
      />

      {/* Status Bar */}
      <div className="h-6 border-t border-zinc-850 bg-zinc-900/50 px-3 flex items-center justify-between text-[10px] text-zinc-500 font-mono select-none">
        <div className="flex items-center gap-3">
          <span>{lineCount} dòng</span>
          <span>{editorContent.length} ký tự</span>
        </div>
        <div className="flex items-center gap-2">
          <span>UTF-8</span>
          <span className="text-indigo-400">Local Antigravity Code Editor</span>
        </div>
      </div>
    </div>
  );
};
