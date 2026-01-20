"use client";

import type { Todo } from "@/lib/api/types";
import { TodoCard } from "./TodoCard";

interface TodoBoardProps {
  todos: Todo[];
  onSelectTodo?: (todo: Todo) => void;
}

export function TodoBoard({ todos, onSelectTodo }: TodoBoardProps) {
  const p0Todos = todos.filter((t) => t.priority === "P0");
  const p1Todos = todos.filter((t) => t.priority === "P1");
  const p2Todos = todos.filter((t) => t.priority === "P2");

  const columns = [
    { priority: "P0", label: "今すぐ", todos: p0Todos, color: "text-red-400" },
    { priority: "P1", label: "1-2週間", todos: p1Todos, color: "text-amber-400" },
    { priority: "P2", label: "継続", todos: p2Todos, color: "text-slate-400" },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {columns.map((column) => (
        <div key={column.priority} className="space-y-3">
          <div className="flex items-center gap-2 px-2">
            <span className={`font-mono font-bold ${column.color}`}>
              {column.priority}
            </span>
            <span className="text-text-secondary text-sm">{column.label}</span>
            <span className="text-text-muted text-xs ml-auto">
              {column.todos.length}件
            </span>
          </div>
          <div className="space-y-2">
            {column.todos.length > 0 ? (
              column.todos.map((todo) => (
                <TodoCard
                  key={todo.todo_id}
                  todo={todo}
                  onClick={() => onSelectTodo?.(todo)}
                />
              ))
            ) : (
              <div className="rounded-lg p-4 text-center text-text-muted text-sm border border-dashed border-[rgba(148,163,184,0.15)]">
                なし
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
