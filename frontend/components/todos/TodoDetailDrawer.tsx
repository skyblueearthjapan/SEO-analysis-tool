"use client";

import { useEffect, useState } from "react";
import { X, ChevronDown, ChevronRight, Copy, Check, AlertTriangle, Info, AlertCircle } from "lucide-react";
import { cn, getPriorityClass } from "@/lib/utils";
import type { Todo, TodoDetail, EvidenceItem, Step, Template, Verification, RootCause } from "@/lib/api/types";

interface TodoDetailDrawerProps {
  todo: Todo | null;
  open: boolean;
  onClose: () => void;
  allTodos?: Todo[];
  onSelectTodo?: (todo: Todo) => void;
}

export function TodoDetailDrawer({ todo, open, onClose, allTodos = [], onSelectTodo }: TodoDetailDrawerProps) {
  const [checkedSteps, setCheckedSteps] = useState<Record<string, boolean>>({});
  const [expandedEvidence, setExpandedEvidence] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Load checked steps from localStorage
  useEffect(() => {
    if (todo?.todo_id) {
      const stored = localStorage.getItem(`todo_steps_${todo.todo_id}`);
      if (stored) {
        setCheckedSteps(JSON.parse(stored));
      } else {
        setCheckedSteps({});
      }
    }
  }, [todo?.todo_id]);

  // Save checked steps to localStorage
  const toggleStep = (index: number) => {
    if (!todo) return;
    const key = `step_${index}`;
    const newChecked = { ...checkedSteps, [key]: !checkedSteps[key] };
    setCheckedSteps(newChecked);
    localStorage.setItem(`todo_steps_${todo.todo_id}`, JSON.stringify(newChecked));
  };

  // Copy to clipboard
  const copyToClipboard = async (content: string, id: string) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open || !todo) return null;

  const detail = todo.detail;
  const relatedTodos = allTodos.filter(t => detail?.related_todo_ids?.includes(t.todo_id));

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={cn(
          "fixed top-0 right-0 h-full w-[600px] max-w-[90vw] z-50",
          "bg-bg-base border-l border-border-subtle",
          "transform transition-transform duration-300 ease-out",
          "overflow-hidden flex flex-col",
          open ? "translate-x-0" : "translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-border-subtle">
          <div className="flex-1 pr-4">
            <div className="flex items-center gap-2 mb-2">
              <span className={cn("priority-tag", getPriorityClass(todo.priority))}>
                {todo.priority}
              </span>
              <span className="text-xs text-text-muted bg-bg-surface px-2 py-0.5 rounded">
                {todo.category}
              </span>
              <ImpactBadge impact={todo.impact} />
              <EffortBadge effort={todo.effort} />
            </div>
            <h2 className="text-lg font-semibold text-text-primary">{todo.title}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-bg-elevated rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-text-muted" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Summary */}
          <Section title="概要">
            <p className="text-text-secondary">{todo.details}</p>
          </Section>

          {/* Why (if detail exists) */}
          {detail?.why && (
            <Section title="なぜ重要か">
              <p className="text-text-secondary">{detail.why}</p>
            </Section>
          )}

          {/* Root Causes */}
          {detail?.root_causes && detail.root_causes.length > 0 && (
            <Section title="考えられる原因">
              <div className="space-y-2">
                {detail.root_causes.map((cause, idx) => (
                  <RootCauseItem key={idx} cause={cause} />
                ))}
              </div>
            </Section>
          )}

          {/* Evidence */}
          {detail?.evidence && detail.evidence.length > 0 && (
            <Section title="根拠データ">
              <div className="space-y-2">
                {detail.evidence.map((ev) => (
                  <EvidenceAccordion
                    key={ev.id}
                    evidence={ev}
                    expanded={expandedEvidence === ev.id}
                    onToggle={() => setExpandedEvidence(
                      expandedEvidence === ev.id ? null : ev.id
                    )}
                  />
                ))}
              </div>
            </Section>
          )}

          {/* Steps */}
          {detail?.steps && detail.steps.length > 0 && (
            <Section title="対応手順">
              <div className="space-y-2">
                {detail.steps.map((step, idx) => (
                  <StepItem
                    key={idx}
                    step={step}
                    index={idx}
                    checked={checkedSteps[`step_${idx}`] || false}
                    onToggle={() => toggleStep(idx)}
                  />
                ))}
              </div>
            </Section>
          )}

          {/* Templates */}
          {detail?.templates && detail.templates.length > 0 && (
            <Section title="テンプレート・サンプル">
              <div className="space-y-3">
                {detail.templates.map((template, idx) => (
                  <CopyBlock
                    key={idx}
                    template={template}
                    copied={copiedId === `template_${idx}`}
                    onCopy={() => copyToClipboard(template.content, `template_${idx}`)}
                  />
                ))}
              </div>
            </Section>
          )}

          {/* Examples (legacy support) */}
          {todo.examples && Object.keys(todo.examples).length > 0 && !detail?.templates && (
            <Section title="提案例">
              <ExamplesBlock examples={todo.examples} copiedId={copiedId} onCopy={copyToClipboard} />
            </Section>
          )}

          {/* Verification */}
          {detail?.verification && detail.verification.length > 0 && (
            <Section title="検証方法">
              <div className="space-y-2">
                {detail.verification.map((v, idx) => (
                  <VerificationItem key={idx} verification={v} />
                ))}
              </div>
            </Section>
          )}

          {/* Related Todos */}
          {relatedTodos.length > 0 && (
            <Section title="関連ToDo">
              <div className="space-y-2">
                {relatedTodos.map((related) => (
                  <button
                    key={related.todo_id}
                    onClick={() => onSelectTodo?.(related)}
                    className="w-full text-left p-3 rounded-lg bg-bg-surface hover:bg-bg-elevated transition-colors border border-border-subtle"
                  >
                    <div className="flex items-center gap-2">
                      <span className={cn("priority-tag text-xs", getPriorityClass(related.priority))}>
                        {related.priority}
                      </span>
                      <span className="text-sm text-text-primary">{related.title}</span>
                    </div>
                  </button>
                ))}
              </div>
            </Section>
          )}
        </div>
      </div>
    </>
  );
}

// Sub-components

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-medium text-text-muted mb-3">{title}</h3>
      {children}
    </div>
  );
}

function ImpactBadge({ impact }: { impact: string }) {
  const colors = {
    high: "text-red-400 bg-red-400/10",
    medium: "text-amber-400 bg-amber-400/10",
    low: "text-slate-400 bg-slate-400/10",
  };
  return (
    <span className={cn("text-xs px-2 py-0.5 rounded", colors[impact as keyof typeof colors])}>
      Impact: {impact}
    </span>
  );
}

function EffortBadge({ effort }: { effort: string }) {
  const colors = {
    small: "text-green-400 bg-green-400/10",
    medium: "text-amber-400 bg-amber-400/10",
    large: "text-red-400 bg-red-400/10",
  };
  return (
    <span className={cn("text-xs px-2 py-0.5 rounded", colors[effort as keyof typeof colors])}>
      Effort: {effort}
    </span>
  );
}

function RootCauseItem({ cause }: { cause: RootCause }) {
  const likelihoodColors = {
    high: "text-red-400",
    medium: "text-amber-400",
    low: "text-slate-400",
  };
  return (
    <div className="p-3 rounded-lg bg-bg-surface border border-border-subtle">
      <div className="flex items-center gap-2 mb-1">
        <span className={cn("text-xs font-medium", likelihoodColors[cause.likelihood])}>
          {cause.likelihood === "high" ? "可能性: 高" : cause.likelihood === "medium" ? "可能性: 中" : "可能性: 低"}
        </span>
      </div>
      <p className="text-sm text-text-primary">{cause.label}</p>
      {cause.notes && (
        <p className="text-xs text-text-muted mt-1">{cause.notes}</p>
      )}
    </div>
  );
}

function EvidenceAccordion({
  evidence,
  expanded,
  onToggle,
}: {
  evidence: EvidenceItem;
  expanded: boolean;
  onToggle: () => void;
}) {
  const severityIcon = {
    critical: <AlertCircle className="h-4 w-4 text-red-400" />,
    warning: <AlertTriangle className="h-4 w-4 text-amber-400" />,
    info: <Info className="h-4 w-4 text-accent-cyan" />,
  };

  return (
    <div className="rounded-lg bg-bg-surface border border-border-subtle overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 p-3 hover:bg-bg-elevated transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-text-muted" />
        ) : (
          <ChevronRight className="h-4 w-4 text-text-muted" />
        )}
        {severityIcon[evidence.severity]}
        <span className="text-sm text-text-primary flex-1 text-left">{evidence.title}</span>
        <span className="text-xs text-text-muted">{evidence.kind}</span>
      </button>
      {expanded && (
        <div className="p-3 pt-0 border-t border-border-subtle">
          <pre className="text-xs text-text-secondary bg-bg-base p-2 rounded overflow-x-auto">
            {JSON.stringify(evidence.data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function StepItem({
  step,
  index,
  checked,
  onToggle,
}: {
  step: Step;
  index: number;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <label className="flex items-start gap-3 p-3 rounded-lg bg-bg-surface border border-border-subtle cursor-pointer hover:bg-bg-elevated transition-colors">
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        className="mt-0.5 rounded border-border-subtle bg-bg-base text-accent-cyan focus:ring-accent-cyan"
      />
      <span className={cn("text-sm", checked ? "text-text-muted line-through" : "text-text-primary")}>
        {index + 1}. {step.text}
      </span>
    </label>
  );
}

function CopyBlock({
  template,
  copied,
  onCopy,
}: {
  template: Template;
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <div className="rounded-lg bg-bg-surface border border-border-subtle overflow-hidden">
      <div className="flex items-center justify-between p-3 border-b border-border-subtle">
        <span className="text-sm font-medium text-text-primary">{template.title}</span>
        <button
          onClick={onCopy}
          className="flex items-center gap-1 text-xs text-text-muted hover:text-accent-cyan transition-colors"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3" />
              コピー済み
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              コピー
            </>
          )}
        </button>
      </div>
      <div className="p-3">
        {template.type === "code" ? (
          <pre className="text-xs text-text-secondary bg-bg-base p-2 rounded overflow-x-auto whitespace-pre-wrap">
            {template.content}
          </pre>
        ) : (
          <p className="text-sm text-text-secondary whitespace-pre-wrap">{template.content}</p>
        )}
      </div>
    </div>
  );
}

function VerificationItem({ verification }: { verification: Verification }) {
  return (
    <div className="p-3 rounded-lg bg-bg-surface border border-border-subtle">
      <div className="flex items-center gap-4 text-sm">
        <div>
          <span className="text-text-muted">指標: </span>
          <span className="text-text-primary font-medium">{verification.metric}</span>
        </div>
        <div>
          <span className="text-text-muted">目標: </span>
          <span className="text-accent-cyan font-medium">{verification.target}</span>
        </div>
      </div>
      <p className="text-xs text-text-muted mt-2">確認方法: {verification.how_to_check}</p>
    </div>
  );
}

function ExamplesBlock({
  examples,
  copiedId,
  onCopy,
}: {
  examples: Todo["examples"];
  copiedId: string | null;
  onCopy: (content: string, id: string) => void;
}) {
  if (!examples) return null;

  const items: { title: string; content: string; id: string }[] = [];

  if (examples.title_variants?.length) {
    items.push({
      title: "タイトル案",
      content: examples.title_variants.join("\n"),
      id: "title_variants",
    });
  }
  if (examples.meta_description_variants?.length) {
    items.push({
      title: "メタディスクリプション案",
      content: examples.meta_description_variants.join("\n"),
      id: "meta_variants",
    });
  }
  if (examples.h2_outline?.length) {
    items.push({
      title: "見出し構成案",
      content: examples.h2_outline.join("\n"),
      id: "h2_outline",
    });
  }
  if (examples.faq_questions?.length) {
    items.push({
      title: "FAQ質問案",
      content: examples.faq_questions.join("\n"),
      id: "faq_questions",
    });
  }
  if (examples.outreach_message_draft_jp) {
    items.push({
      title: "依頼文テンプレート",
      content: examples.outreach_message_draft_jp,
      id: "outreach_message",
    });
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.id} className="rounded-lg bg-bg-surface border border-border-subtle overflow-hidden">
          <div className="flex items-center justify-between p-3 border-b border-border-subtle">
            <span className="text-sm font-medium text-text-primary">{item.title}</span>
            <button
              onClick={() => onCopy(item.content, item.id)}
              className="flex items-center gap-1 text-xs text-text-muted hover:text-accent-cyan transition-colors"
            >
              {copiedId === item.id ? (
                <>
                  <Check className="h-3 w-3" />
                  コピー済み
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  コピー
                </>
              )}
            </button>
          </div>
          <div className="p-3">
            <p className="text-sm text-text-secondary whitespace-pre-wrap">{item.content}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
