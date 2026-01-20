"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { GlassCard } from "@/components/layout/GlassCard";
import { listPages, createPage, deletePage } from "@/lib/api/queries";
import type { Page, PageType } from "@/lib/api/types";
import { Plus, Trash2, ExternalLink, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export default function PagesPage({
  params,
}: {
  params: { siteId: string };
}) {
  const [pages, setPages] = useState<Page[]>([]);
  const [activeTab, setActiveTab] = useState<"official" | "competitor" | "third_party">("official");
  const [isAddingUrl, setIsAddingUrl] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [newPageType, setNewPageType] = useState<PageType>("official_homepage");
  const [loading, setLoading] = useState(true);

  // Selection state
  const [selectedOfficial, setSelectedOfficial] = useState<string | null>(null);
  const [selectedCompetitors, setSelectedCompetitors] = useState<Set<string>>(new Set());
  const [selectedThirdParty, setSelectedThirdParty] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadPages();
  }, [params.siteId]);

  async function loadPages() {
    try {
      const data = await listPages(params.siteId);
      setPages(data.items);
    } catch (error) {
      console.error("Failed to load pages:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleAddPage() {
    if (!newUrl.trim()) return;
    try {
      await createPage(params.siteId, {
        url: newUrl,
        page_type: newPageType,
        label: newLabel || undefined,
      });
      await loadPages();
      setNewUrl("");
      setNewLabel("");
      setIsAddingUrl(false);
    } catch (error) {
      console.error("Failed to add page:", error);
    }
  }

  async function handleDeletePage(pageId: string) {
    if (!confirm("このURLを削除しますか？")) return;
    try {
      await deletePage(params.siteId, pageId);
      await loadPages();
    } catch (error) {
      console.error("Failed to delete page:", error);
    }
  }

  const filteredPages = pages.filter((page) => {
    if (activeTab === "official") return page.page_type === "official_homepage";
    if (activeTab === "competitor") return page.page_type === "competitor_page";
    return page.page_type === "third_party_profile_page";
  });

  const officialPages = pages.filter((p) => p.page_type === "official_homepage");
  const competitorPages = pages.filter((p) => p.page_type === "competitor_page");
  const thirdPartyPages = pages.filter((p) => p.page_type === "third_party_profile_page");

  function toggleSelection(pageId: string, type: PageType) {
    if (type === "official_homepage") {
      setSelectedOfficial(selectedOfficial === pageId ? null : pageId);
    } else if (type === "competitor_page") {
      const newSet = new Set(selectedCompetitors);
      if (newSet.has(pageId)) {
        newSet.delete(pageId);
      } else if (newSet.size < 2) {
        newSet.add(pageId);
      }
      setSelectedCompetitors(newSet);
    } else {
      const newSet = new Set(selectedThirdParty);
      if (newSet.has(pageId)) {
        newSet.delete(pageId);
      } else {
        newSet.add(pageId);
      }
      setSelectedThirdParty(newSet);
    }
  }

  const canProceed = selectedOfficial !== null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-muted">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">URL BASE</h1>
          <p className="text-text-secondary text-sm">
            公式 / 競合 / 紹介記事を整理して解析ターゲットを選択
          </p>
        </div>
        <button
          onClick={() => setIsAddingUrl(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          <span>URL追加</span>
        </button>
      </div>

      {/* Add URL Modal */}
      {isAddingUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <GlassCard className="w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">URL追加</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  URL
                </label>
                <input
                  type="url"
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="input-base"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  ページタイプ
                </label>
                <select
                  value={newPageType}
                  onChange={(e) => setNewPageType(e.target.value as PageType)}
                  className="input-base"
                >
                  <option value="official_homepage">公式HP</option>
                  <option value="competitor_page">競合</option>
                  <option value="third_party_profile_page">紹介記事</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  ラベル（任意）
                </label>
                <input
                  type="text"
                  value={newLabel}
                  onChange={(e) => setNewLabel(e.target.value)}
                  placeholder="例: 公式トップ、競合A"
                  className="input-base"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setIsAddingUrl(false)}
                className="btn-secondary"
              >
                キャンセル
              </button>
              <button onClick={handleAddPage} className="btn-primary">
                追加
              </button>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-[rgba(148,163,184,0.15)]">
        {[
          { key: "official", label: "公式HP", count: officialPages.length },
          { key: "competitor", label: "競合", count: competitorPages.length },
          { key: "third_party", label: "紹介記事", count: thirdPartyPages.length },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as typeof activeTab)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px]",
              activeTab === tab.key
                ? "border-accent-cyan text-accent-cyan"
                : "border-transparent text-text-muted hover:text-text-primary"
            )}
          >
            {tab.label}
            <span className="ml-2 text-xs opacity-70">({tab.count})</span>
          </button>
        ))}
      </div>

      {/* Pages Table */}
      <GlassCard>
        {filteredPages.length > 0 ? (
          <div className="space-y-2">
            {filteredPages.map((page) => {
              const isSelected =
                page.page_type === "official_homepage"
                  ? selectedOfficial === page.page_id
                  : page.page_type === "competitor_page"
                  ? selectedCompetitors.has(page.page_id)
                  : selectedThirdParty.has(page.page_id);

              return (
                <div
                  key={page.page_id}
                  className={cn(
                    "flex items-center gap-4 p-4 rounded-lg transition-colors cursor-pointer",
                    isSelected
                      ? "bg-accent-cyan/10 border border-accent-cyan/30"
                      : "bg-bg-surface hover:bg-bg-elevated border border-transparent"
                  )}
                  onClick={() => toggleSelection(page.page_id, page.page_type)}
                >
                  <input
                    type={page.page_type === "official_homepage" ? "radio" : "checkbox"}
                    checked={isSelected}
                    onChange={() => {}}
                    className="h-4 w-4"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">
                        {page.label || page.url}
                      </span>
                      <a
                        href={page.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-text-muted hover:text-accent-cyan"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </div>
                    <p className="text-sm text-text-muted truncate">
                      {page.url}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeletePage(page.page_id);
                    }}
                    className="p-2 text-text-muted hover:text-accent-red transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-12 text-text-muted">
            このカテゴリにはまだURLがありません
          </div>
        )}
      </GlassCard>

      {/* Selection Summary */}
      <div className="fixed bottom-0 left-[72px] right-0 p-4 bg-bg-base/90 backdrop-blur-xl border-t border-[rgba(148,163,184,0.15)]">
        <div className="container flex items-center justify-between">
          <div className="flex items-center gap-6 text-sm">
            <span className={cn(selectedOfficial ? "text-accent-cyan" : "text-text-muted")}>
              公式: {selectedOfficial ? "1" : "0"}/1
            </span>
            <span className={cn(selectedCompetitors.size > 0 ? "text-accent-cyan" : "text-text-muted")}>
              競合: {selectedCompetitors.size}/2
            </span>
            <span className={cn(selectedThirdParty.size > 0 ? "text-accent-cyan" : "text-text-muted")}>
              紹介: {selectedThirdParty.size}
            </span>
          </div>
          <Link
            href={canProceed ? `/sites/${params.siteId}/run?official=${selectedOfficial}&competitors=${Array.from(selectedCompetitors).join(",")}&thirdParty=${Array.from(selectedThirdParty).join(",")}` : "#"}
            className={cn(
              "btn-primary flex items-center gap-2",
              !canProceed && "opacity-50 cursor-not-allowed"
            )}
            onClick={(e) => !canProceed && e.preventDefault()}
          >
            <span>解析設定へ</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
