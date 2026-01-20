"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";
import type { PageType } from "@/lib/api/types";

interface PageCreateFormProps {
  onSubmit: (url: string, pageType: PageType, label?: string) => Promise<void>;
  defaultPageType?: PageType;
}

const PAGE_TYPE_OPTIONS: { value: PageType; label: string }[] = [
  { value: "official_homepage", label: "公式ホームページ" },
  { value: "competitor_page", label: "競合ページ" },
  { value: "third_party_profile_page", label: "サードパーティプロフィール" },
];

export function PageCreateForm({
  onSubmit,
  defaultPageType = "official_homepage",
}: PageCreateFormProps) {
  const [url, setUrl] = useState("");
  const [pageType, setPageType] = useState<PageType>(defaultPageType);
  const [label, setLabel] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // Validate URL
    if (!url.trim()) {
      setError("URLを入力してください");
      return;
    }

    try {
      new URL(url.trim());
    } catch {
      setError("有効なURLを入力してください");
      return;
    }

    setLoading(true);
    try {
      await onSubmit(url.trim(), pageType, label.trim() || undefined);
      setUrl("");
      setLabel("");
    } catch (err: any) {
      setError(err.message || "登録に失敗しました");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* URL Input */}
        <div className="md:col-span-5">
          <label className="block text-sm text-text-muted mb-2">URL</label>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="w-full px-4 py-2 bg-bg-surface border border-border-subtle rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-cyan"
          />
        </div>

        {/* Page Type Select */}
        <div className="md:col-span-3">
          <label className="block text-sm text-text-muted mb-2">種別</label>
          <select
            value={pageType}
            onChange={(e) => setPageType(e.target.value as PageType)}
            className="w-full px-4 py-2 bg-bg-surface border border-border-subtle rounded-lg text-text-primary focus:outline-none focus:border-accent-cyan"
          >
            {PAGE_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Label Input */}
        <div className="md:col-span-3">
          <label className="block text-sm text-text-muted mb-2">
            ラベル（任意）
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="例: メインLP"
            className="w-full px-4 py-2 bg-bg-surface border border-border-subtle rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-cyan"
          />
        </div>

        {/* Submit Button */}
        <div className="md:col-span-1 flex items-end">
          <button
            type="submit"
            disabled={loading}
            className="w-full h-[42px] btn-primary flex items-center justify-center gap-2"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm">
          <X className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
    </form>
  );
}
