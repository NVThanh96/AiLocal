import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check } from "lucide-react";

interface MarkdownMessageProps {
  content: string;
  isUser?: boolean;
}

export const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content, isUser }) => {
  const [copiedCodeIdx, setCopiedCodeIdx] = useState<number | null>(null);

  const handleCopyCode = async (codeText: string, idx: number) => {
    try {
      await navigator.clipboard.writeText(codeText);
      setCopiedCodeIdx(idx);
      setTimeout(() => setCopiedCodeIdx(null), 2000);
    } catch (e) {
      console.error("Failed to copy code:", e);
    }
  };

  if (isUser) {
    return (
      <div className="whitespace-pre-wrap break-words leading-relaxed select-text cursor-text selection:bg-indigo-500/40 selection:text-white">
        {content}
      </div>
    );
  }

  let codeBlockCounter = 0;

  return (
    <div className="markdown-body select-text cursor-text text-zinc-200 text-xs md:text-sm leading-relaxed selection:bg-indigo-500/40 selection:text-white space-y-2">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            const isInline = !match && !String(children).includes("\n");
            const codeString = String(children).replace(/\n$/, "");

            if (isInline) {
              return (
                <code
                  className="px-1.5 py-0.5 rounded-md bg-zinc-800/90 text-indigo-300 font-mono text-[11px] border border-zinc-700/60 select-text"
                  {...props}
                >
                  {children}
                </code>
              );
            }

            const currentIdx = codeBlockCounter++;
            const isCopied = copiedCodeIdx === currentIdx;
            const lang = match ? match[1] : "code";

            return (
              <div className="my-2.5 rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden shadow-md group">
                <div className="flex items-center justify-between px-3.5 py-1.5 bg-zinc-900/90 border-b border-zinc-800/80 text-[11px] select-none">
                  <span className="font-mono text-zinc-400 uppercase tracking-wider text-[10px] font-semibold">
                    {lang}
                  </span>
                  <button
                    onClick={() => handleCopyCode(codeString, currentIdx)}
                    className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] text-zinc-400 hover:text-white hover:bg-zinc-800 transition active:scale-95"
                    title="Sao chép đoạn mã này"
                  >
                    {isCopied ? (
                      <>
                        <Check size={12} className="text-emerald-400" />
                        <span className="text-emerald-400 font-medium">Đã chép</span>
                      </>
                    ) : (
                      <>
                        <Copy size={12} />
                        <span>Sao chép</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="p-3 overflow-x-auto font-mono text-[11px] md:text-xs leading-relaxed text-zinc-200 select-text">
                  <pre className="m-0 p-0 font-mono">
                    <code>{codeString}</code>
                  </pre>
                </div>
              </div>
            );
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-3 rounded-xl border border-zinc-800 shadow-sm">
                <table className="w-full text-left border-collapse text-xs select-text">{children}</table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-zinc-900/90 text-zinc-300 border-b border-zinc-800 font-semibold">{children}</thead>;
          },
          th({ children }) {
            return <th className="px-3 py-2 text-[11px] font-bold text-zinc-300">{children}</th>;
          },
          td({ children }) {
            return <td className="px-3 py-2 border-t border-zinc-850/80 text-zinc-300 text-[11px]">{children}</td>;
          },
          ul({ children }) {
            return <ul className="list-disc list-inside space-y-1 my-2 pl-1.5 text-zinc-300">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="list-decimal list-inside space-y-1 my-2 pl-1.5 text-zinc-300">{children}</ol>;
          },
          li({ children }) {
            return <li className="leading-relaxed text-zinc-300 select-text">{children}</li>;
          },
          p({ children }) {
            return <p className="my-1.5 leading-relaxed select-text">{children}</p>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-2 border-indigo-500/70 pl-3 my-2 text-zinc-400 italic bg-zinc-900/30 py-1 rounded-r-lg select-text">
                {children}
              </blockquote>
            );
          },
          h1({ children }) {
            return <h1 className="text-base font-bold text-white mt-3 mb-1.5 pb-1 border-b border-zinc-800 select-text">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="text-sm font-bold text-white mt-2.5 mb-1 select-text">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="text-xs font-bold text-indigo-300 mt-2 mb-1 select-text">{children}</h3>;
          },
          hr() {
            return <hr className="my-3 border-zinc-800" />;
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
              >
                {children}
              </a>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
