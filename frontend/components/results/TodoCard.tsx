"use client";

import { cn, getPriorityClass } from "@/lib/utils";
import type { Todo } from "@/lib/api/types";
import { ChevronRight, Zap, Clock } from "lucide-react";

interface TodoCardProps {
  todo: Todo;
  onClick?: () => void;
}

export function TodoCard({ todo, onClick }: TodoCardProps) {
  const impactIcon = {
    high: <Zap className="h-3 w-3 text-red-400" />,
    medium: <Zap className="h-3 w-3 text-amber-400" />,
    low: <Zap className="h-3 w-3 text-slate-400" />,
  };

  const effortIcon = {
    small: <Clock className="h-3 w-3 text-green-400" />,
    medium: <Clock className="h-3 w-3 text-amber-400" />,
    large: <Clock className="h-3 w-3 text-red-400" />,
  };

  return (
    <div
      className={cn(
        "rounded-lg p-4 cursor-pointer transition-all",
        "bg-bg-surface border border-[rgba(148,163,184,0.15)]",
        "hover:border-accent-cyan/30 hover:bg-bg-elevated"
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={cn("priority-tag", getPriorityClass(todo.priority))}>
              {todo.priority}
            </span>
            <span className="text-xs text-text-muted">{todo.category}</span>
          </div>
          <h4 className="font-medium text-text-primary mb-1">{todo.title}</h4>
          <p className="text-sm text-text-secondary line-clamp-2">
            {todo.details}
          </p>
        </div>
        <ChevronRight className="h-5 w-5 text-text-muted flex-shrink-0" />
      </div>
      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-[rgba(148,163,184,0.1)]">
        <div className="flex items-center gap-1 text-xs text-text-muted">
          {impactIcon[todo.impact]}
          <span>Impact: {todo.impact}</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-text-muted">
          {effortIcon[todo.effort]}
          <span>Effort: {todo.effort}</span>
        </div>
      </div>
    </div>
  );
}
