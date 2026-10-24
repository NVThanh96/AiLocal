import React, { useState } from "react";
import {
  X, CheckCircle2, AlertTriangle, ShieldAlert, HelpCircle,
  FileText, ArrowRight, Check, ShieldCheck
} from "lucide-react";
import type { TaskSpecification } from "../services/api";

interface TaskIntelligenceModalProps {
  taskSpec: TaskSpecification;
  onClose: () => void;
  onClarify: (taskId: string, questionId: string, option: string) => Promise<void>;
  onApprove: (taskId: string, approved: boolean) => Promise<void>;
}

export const TaskIntelligenceModal: React.FC<TaskIntelligenceModalProps> = ({
  taskSpec,
  onClose,
  onClarify,
  onApprove,
}) => {
  const [submitting, setSubmitting] = useState(false);

  const handleSelectOption = async (qId: string, opt: string) => {
    setSubmitting(true);
    try {
      await onClarify(taskSpec.task_id, qId, opt);
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproval = async (approved: boolean) => {
    setSubmitting(true);
    try {
      await onApprove(taskSpec.task_id, approved);
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = () => {
    switch (taskSpec.status) {
      case "READY":
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 bg-emerald-950/80 text-emerald-400 border border-emerald-800 rounded-md text-xs font-medium">
            <CheckCircle2 size={13} /> READY
          </span>
        );
      case "NEEDS_CLARIFICATION":
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 bg-amber-950/80 text-amber-400 border border-amber-800 rounded-md text-xs font-medium">
            <HelpCircle size={13} /> NEEDS CLARIFICATION
          </span>
        );
      case "NEEDS_APPROVAL":
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 bg-orange-950/80 text-orange-400 border border-orange-800 rounded-md text-xs font-medium">
            <ShieldAlert size={13} /> NEEDS APPROVAL
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 bg-rose-950/80 text-rose-400 border border-rose-800 rounded-md text-xs font-medium">
            <AlertTriangle size={13} /> {taskSpec.status}
          </span>
        );
    }
  };

  const getRiskBadge = () => {
    switch (taskSpec.risk_level) {
      case "LOW":
        return <span className="text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded text-[11px]">Rủi ro: Thấp (Low)</span>;
      case "MEDIUM":
        return <span className="text-amber-400 bg-amber-950 px-2 py-0.5 rounded text-[11px] border border-amber-800/40">Rủi ro: Trung bình</span>;
      default:
        return <span className="text-rose-400 bg-rose-950 px-2 py-0.5 rounded text-[11px] border border-rose-800/60 font-semibold">Rủi ro: Cao (High)</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden text-zinc-100 select-none animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="h-14 border-b border-zinc-800 px-5 flex items-center justify-between bg-zinc-900/90">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-semibold text-zinc-200">Requirement Intelligence Gate</h2>
            <span className="text-xs text-zinc-500 font-mono">v{taskSpec.request_version}</span>
            {getStatusBadge()}
            {getRiskBadge()}
          </div>
          <button onClick={onClose} className="p-1 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white">
            <X size={18} />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
          {/* Goal & Prompt */}
          <div className="bg-zinc-950/70 border border-zinc-800 rounded-xl p-3.5 space-y-1.5">
            <div className="text-[11px] font-semibold text-zinc-400">MỤC TIÊU NHIỆM VỤ</div>
            <div className="text-sm font-medium text-zinc-200">{taskSpec.goal}</div>
            <div className="text-zinc-500 text-[11px] font-mono">Prompt gốc: "{taskSpec.original_prompt}"</div>
          </div>

          {/* APPROVAL GATE (if NEEDS_APPROVAL) */}
          {taskSpec.status === "NEEDS_APPROVAL" && (
            <div className="bg-orange-950/40 border border-orange-700/60 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2 text-orange-300 font-semibold text-sm">
                <ShieldAlert size={18} />
                <span>Cổng Phê Duyệt An Toàn (Safety Approval Gate)</span>
              </div>
              <p className="text-zinc-300 text-xs leading-relaxed">
                Nhiệm vụ này bao gồm các hành động có mức độ rủi ro cao hoặc tác động thay đổi hệ thống. Quyền yêu cầu:
                <code className="mx-1 px-1.5 py-0.5 bg-orange-900/60 rounded text-orange-200 font-mono text-[11px]">
                  {taskSpec.required_permissions.join(", ")}
                </code>.
                Hệ thống yêu cầu xác nhận trước khi tiếp tục.
              </p>
              <div className="flex gap-2 pt-1">
                <button
                  disabled={submitting}
                  onClick={() => handleApproval(true)}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg font-medium flex items-center gap-1.5 transition-colors"
                >
                  <ShieldCheck size={15} />
                  <span>Phê duyệt thực thi (Approve)</span>
                </button>
                <button
                  disabled={submitting}
                  onClick={() => handleApproval(false)}
                  className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-zinc-300 rounded-lg font-medium transition-colors"
                >
                  <span>Từ chối (Reject)</span>
                </button>
              </div>
            </div>
          )}

          {/* CLARIFICATION QUESTIONS (if NEEDS_CLARIFICATION) */}
          {taskSpec.unresolved_questions && taskSpec.unresolved_questions.length > 0 && (
            <div className="space-y-3">
              <div className="text-[11px] font-semibold text-amber-400 flex items-center gap-1.5">
                <HelpCircle size={14} />
                <span>ĐIỂM CẦN LÀM RÕ (CLARIFICATION REQUIRED)</span>
              </div>
              {taskSpec.unresolved_questions.map((q) => (
                <div key={q.id} className="bg-zinc-950 border border-amber-900/40 rounded-xl p-3.5 space-y-2">
                  <div className="text-zinc-200 font-medium text-xs">{q.question}</div>
                  <div className="text-[11px] text-zinc-500 italic">Lý do: {q.reason}</div>
                  {!q.answered ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1">
                      {q.suggested_options.map((opt, i) => (
                        <button
                          key={i}
                          disabled={submitting}
                          onClick={() => handleSelectOption(q.id, opt)}
                          className="text-left px-3 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-zinc-300 hover:text-white transition-all text-xs flex items-center justify-between group"
                        >
                          <span>{opt}</span>
                          <ArrowRight size={13} className="text-zinc-600 group-hover:text-zinc-300 shrink-0 ml-1" />
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="text-emerald-400 bg-emerald-950/40 border border-emerald-900/50 px-2.5 py-1.5 rounded-lg text-[11px] flex items-center gap-1.5">
                      <Check size={13} />
                      <span>Đã chọn: <strong>{q.chosen_option}</strong></span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Verified Facts Collected */}
          {taskSpec.verified_facts && taskSpec.verified_facts.length > 0 && (
            <div className="space-y-2">
              <div className="text-[11px] font-semibold text-zinc-400 flex items-center gap-1.5">
                <CheckCircle2 size={13} className="text-emerald-500" />
                <span>DỮ KIỆN ĐÃ TỰ XÁC MINH TRONG WORKSPACE ({taskSpec.verified_facts.length})</span>
              </div>
              <div className="space-y-1.5">
                {taskSpec.verified_facts.map((fact, idx) => (
                  <div key={idx} className="bg-zinc-950 border border-zinc-800/80 rounded-lg p-2.5 text-xs">
                    <div className="text-zinc-300 font-medium flex items-center gap-1.5">
                      <FileText size={13} className="text-blue-400 shrink-0" />
                      <span>{fact.fact}</span>
                    </div>
                    {fact.snippet && (
                      <div className="text-[11px] text-zinc-500 mt-1 font-mono truncate">
                        {fact.snippet.replace(/<[^>]+>/g, "")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Acceptance Criteria */}
          {taskSpec.acceptance_criteria && taskSpec.acceptance_criteria.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-[11px] font-semibold text-zinc-400">TIÊU CHÍ NGHIỆM THU (ACCEPTANCE CRITERIA)</div>
              <ul className="list-disc pl-4 space-y-1 text-zinc-400 text-[11px]">
                {taskSpec.acceptance_criteria.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="h-12 border-t border-zinc-800 px-5 flex items-center justify-between bg-zinc-900/60 text-xs text-zinc-500">
          <span>Task ID: {taskSpec.task_id}</span>
          <button onClick={onClose} className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-zinc-300">
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
};
