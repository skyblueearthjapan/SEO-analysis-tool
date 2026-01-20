"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { PageItem, PageType } from "@/lib/api/types";
import { ExternalLink, Trash2, Edit2, Check, X } from "lucide-react";

interface PageListItemProps {
  page: PageItem;
  isSelected: boolean;
  onToggleSelect: () => void;
  onDelete: (pageId: string) => Promise<void>;
  onUpdate?: (pageId: string, label: string) => Promise<void>;
}

const PAGE_TYPE_LABELS: Record<PageType, string> = {
  official_homepage: "公式",
  competitor_page: "競合",
  third_party_profile_page: "3rd Party",
};

const PAGE_TYPE_COLORS: Record<PageType, string> = {
  official_homepage: "bg-accent-cyan/20 text-accent-cyan",
  competitor_page: "bg-accent-magenta/20 text-accent-magenta",
  third_party_profile_page: "bg-accent-purple/20 text-accent-purple",
};

export function PageListItem({
  page,
  isSelected,
  onToggleSelect,
  onDelete,
  onUpdate,
}: PageListItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editLabel, setEditLabel] = useState(page.label || "");
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (!confirm("このURLを削除しますか？")) return;
    setDeleting(true);
    try {
      await onDelete(page.page_id);
    } catch (error) {
      console.error("Failed to delete page:", error);
    } finally {
      setDeleting(false);
    }
  }

  async function handleSaveLabel() {
    if (onUpdate) {
      try {
        await onUpdate(page.page_id, editLabel);
      } catch (error) {
        console.error("Failed to update label:", error);
      }
    }
    setIsEditing(false);
  }

  return (
    <div
      className={cn(
        "flex items-center gap-4 p-4 rounded-lg bg-bg-surface hover:bg-bg-elevated transition-colors",
        isSelected && "ring-1 ring-accent-cyan"
      )}
    >
      {/* Checkbox */}
      <input
        type="checkbox"
        checked={isSelected}
        onChange={onToggleSelect}
        className="h-4 w-4 rounded border-border-subtle bg-bg-surface text-accent-cyan focus:ring-accent-cyan focus:ring-offset-0"
      />

      {/* Page Type Badge */}
      <span
        className={cn(
          "px-2 py-1 rounded text-xs font-medium",
          PAGE_TYPE_COLORS[page.page_type]
        )}
      >
        {PAGE_TYPE_LABELS[page.page_type]}
      </span>

      {/* URL and Label */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <a
            href={page.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-text-primary hover:text-accent-cyan truncate flex items-center gap-1"
          >
            {page.url}
            <ExternalLink className="h-3 w-3 flex-shrink-0" />
          </a>
        </div>
        {isEditing ? (
          <div className="flex items-center gap-2 mt-1">
            <input
              type="text"
              value={editLabel}
              onChange={(e) => setEditLabel(e.target.value)}
              placeholder="ラベルを入力"
              className="px-2 py-1 text-xs bg-bg-base border border-border-subtle rounded text-text-primary focus:outline-none focus:border-accent-cyan"
              autoFocus
            />
            <button
              onClick={handleSaveLabel}
              className="p-1 text-green-400 hover:text-green-300"
            >
              <Check className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                setIsEditing(false);
                setEditLabel(page.label || "");
              }}
              className="p-1 text-text-muted hover:text-text-primary"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          page.label && (
            <div className="text-xs text-text-muted mt-1">{page.label}</div>
          )
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setIsEditing(true)}
          className="p-2 text-text-muted hover:text-text-primary transition-colors"
          title="ラベル編集"
        >
          <Edit2 className="h-4 w-4" />
        </button>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="p-2 text-text-muted hover:text-red-400 transition-colors disabled:opacity-50"
          title="削除"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
