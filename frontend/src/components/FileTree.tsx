import React, { useState } from "react";
import {
  Folder,
  FolderOpen,
  FileText,
  ChevronRight,
  ChevronDown,
  Edit2,
  Trash2,
  Code2,
  FileJson,
  FileCode,
  FileSpreadsheet
} from "lucide-react";
import type { FileItem } from "../services/api";

interface FileTreeProps {
  items: FileItem[];
  onSelectFile: (path: string) => void;
  onRename?: (path: string) => void;
  onDelete?: (path: string) => void;
  selectedPath?: string;
}

const getFileIcon = (fileName: string) => {
  const ext = fileName.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "py":
      return <Code2 size={13} className="text-yellow-400 shrink-0" />;
    case "ts":
    case "tsx":
    case "js":
    case "jsx":
      return <FileCode size={13} className="text-sky-400 shrink-0" />;
    case "json":
    case "yaml":
    case "yml":
    case "toml":
      return <FileJson size={13} className="text-amber-400 shrink-0" />;
    case "md":
      return <FileText size={13} className="text-emerald-400 shrink-0" />;
    case "csv":
      return <FileSpreadsheet size={13} className="text-green-400 shrink-0" />;
    default:
      return <FileText size={13} className="text-zinc-400 shrink-0" />;
  }
};

const FileTreeNode: React.FC<{
  item: FileItem;
  onSelectFile: (path: string) => void;
  onRename?: (path: string) => void;
  onDelete?: (path: string) => void;
  selectedPath?: string;
}> = ({ item, onSelectFile, onRename, onDelete, selectedPath }) => {
  const [isOpen, setIsOpen] = useState(false);
  const isSelected = selectedPath === item.path;

  if (item.type === "directory") {
    return (
      <div className="select-none group">
        <div
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center justify-between py-1 px-2 hover:bg-zinc-800/60 rounded-lg cursor-pointer text-zinc-300 hover:text-white transition-all text-xs"
        >
          <div className="flex items-center gap-1.5 truncate">
            {isOpen ? (
              <ChevronDown size={12} className="text-zinc-500 shrink-0" />
            ) : (
              <ChevronRight size={12} className="text-zinc-500 shrink-0" />
            )}
            {isOpen ? (
              <FolderOpen size={14} className="text-amber-400 shrink-0" />
            ) : (
              <Folder size={14} className="text-amber-400 shrink-0" />
            )}
            <span className="truncate font-medium">{item.name}</span>
          </div>

          <div className="hidden group-hover:flex items-center gap-1">
            {onRename && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRename(item.path);
                }}
                className="p-1 hover:text-indigo-400 text-zinc-500 hover:bg-zinc-700/60 rounded"
                title="Đổi tên thư mục"
              >
                <Edit2 size={11} />
              </button>
            )}
            {onDelete && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(item.path);
                }}
                className="p-1 hover:text-rose-400 text-zinc-500 hover:bg-zinc-700/60 rounded"
                title="Xóa thư mục"
              >
                <Trash2 size={11} />
              </button>
            )}
          </div>
        </div>

        {isOpen && item.children && (
          <div className="pl-3 border-l border-zinc-800/80 ml-2.5 space-y-0.5 mt-0.5">
            {item.children.map((child) => (
              <FileTreeNode
                key={child.path}
                item={child}
                onSelectFile={onSelectFile}
                onRename={onRename}
                onDelete={onDelete}
                selectedPath={selectedPath}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      onClick={() => onSelectFile(item.path)}
      className={`group flex items-center justify-between py-1 px-2 rounded-lg cursor-pointer transition-all text-xs pl-4.5 ${
        isSelected
          ? "bg-indigo-950/60 text-indigo-200 font-semibold border-l-2 border-indigo-500 shadow-sm"
          : "hover:bg-zinc-800/50 text-zinc-400 hover:text-zinc-200"
      }`}
    >
      <div className="flex items-center gap-1.5 truncate">
        {getFileIcon(item.name)}
        <span className="truncate">{item.name}</span>
      </div>

      <div className="hidden group-hover:flex items-center gap-1 shrink-0">
        {onRename && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRename(item.path);
            }}
            className="p-1 hover:text-indigo-400 text-zinc-500 hover:bg-zinc-700/60 rounded"
            title="Đổi tên tệp"
          >
            <Edit2 size={11} />
          </button>
        )}
        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(item.path);
            }}
            className="p-1 hover:text-rose-400 text-zinc-500 hover:bg-zinc-700/60 rounded"
            title="Xóa tệp"
          >
            <Trash2 size={11} />
          </button>
        )}
      </div>
    </div>
  );
};

export const FileTree: React.FC<FileTreeProps> = ({
  items,
  onSelectFile,
  onRename,
  onDelete,
  selectedPath,
}) => {
  if (!items || items.length === 0) {
    return (
      <div className="p-4 text-xs text-zinc-500 text-center">
        Thư mục trống. Tạo file mới với nút + File bên trên.
      </div>
    );
  }

  return (
    <div className="py-1 space-y-0.5">
      {items.map((item) => (
        <FileTreeNode
          key={item.path}
          item={item}
          onSelectFile={onSelectFile}
          onRename={onRename}
          onDelete={onDelete}
          selectedPath={selectedPath}
        />
      ))}
    </div>
  );
};
